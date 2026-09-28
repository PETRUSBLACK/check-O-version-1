from uuid import UUID
from decimal import Decimal

from django.db import transaction

from apps.businesses.models import Business
from apps.businesses.choices import BusinessCategory, BusinessStatus
from apps.cart.models import Cart, CartItem
from apps.orders.models import CheckoutGroup, FulfilmentType, Order, OrderItem, OrderStatus
from apps.orders.services.stock_service import release_expired_holds, reserve_stock
from apps.products.models import Product


class CartError(Exception):
    pass


# ─── Cart Management ──────────────────────────────────────────────────────────

def get_or_create_cart(*, customer) -> Cart:
    """Get the customer's active cart, or create one if it doesn't exist."""
    cart, _ = Cart.objects.get_or_create(customer=customer)
    return cart


def add_to_cart(*, customer, product_id: UUID, quantity: int = 1) -> CartItem:
    """
    Add a product to the customer's cart.
    - Uses available_stock (respects channel allocation if set).
    - If the item already exists, quantity is incremented.
    - Validates the product is active and from an approved business.
    """
    if quantity < 1:
        raise CartError("Quantity must be at least 1.")

    # Free up stock held by unpaid orders whose payment window has passed
    release_expired_holds(product_ids=[product_id])

    product = Product.objects.select_related("business").filter(pk=product_id).first()
    if not product:
        raise CartError("Product not found.")
    if not product.is_active:
        raise CartError("Product is not available.")
    if product.business.status != BusinessStatus.APPROVED:
        raise CartError("Product is from an unapproved vendor.")
    if product.business.owner_id == customer.id:
        raise CartError("You can't buy from your own shop.")

    # Use available_stock — respects channel allocation if set
    available = product.available_stock

    cart = get_or_create_cart(customer=customer)

    with transaction.atomic():
        item, created = CartItem.objects.select_for_update().get_or_create(
            cart=cart,
            product=product,
            defaults={"quantity": 0},
        )
        new_quantity = item.quantity + quantity

        if new_quantity > available:
            if item.quantity:
                raise CartError(
                    f"{product.business.name} has {available} of this on Check-O, "
                    f"and you already have {item.quantity} in your cart."
                )
            raise CartError(f"{product.business.name} only has {available} of this on Check-O.")

        item.quantity = new_quantity
        item.save(update_fields=["quantity", "updated_at"])

    return item


def update_cart_item(*, customer, product_id: UUID, quantity: int) -> CartItem:
    """
    Set the exact quantity of a cart item.
    - Uses available_stock (respects channel allocation if set).
    - If quantity is 0, the item is removed.
    """
    if quantity < 0:
        raise CartError("Quantity cannot be negative.")

    if quantity == 0:
        remove_from_cart(customer=customer, product_id=product_id)
        return None

    cart = get_or_create_cart(customer=customer)
    item = CartItem.objects.select_related("product").filter(
        cart=cart, product_id=product_id
    ).first()

    if not item:
        raise CartError("Item not found in cart.")

    # Use available_stock — respects channel allocation
    if quantity > item.product.available_stock:
        raise CartError(
            f"{item.product.business.name} only has "
            f"{item.product.available_stock} of this on Check-O."
        )

    with transaction.atomic():
        item.quantity = quantity
        item.save(update_fields=["quantity", "updated_at"])

    return item


def remove_from_cart(*, customer, product_id: UUID) -> None:
    """Remove a product from the customer's cart entirely."""
    cart = get_or_create_cart(customer=customer)
    CartItem.objects.filter(cart=cart, product_id=product_id).delete()


def clear_cart(*, customer) -> None:
    """Remove all items from the customer's cart."""
    cart = get_or_create_cart(customer=customer)
    cart.items.all().delete()


# ─── Checkout ─────────────────────────────────────────────────────────────────

def _resolve_fulfilment(*, shops, requested):
    """
    Work out delivery or pickup for each shop. Anything the customer didn't say
    falls back to what the shop can actually do.
    """
    requested = {str(k): v for k, v in (requested or {}).items()}
    choices = {}
    for business_id, shop in shops.items():
        asked = requested.get(str(business_id))
        if asked is None:
            choices[business_id] = (
                FulfilmentType.DELIVERY if shop.delivers else FulfilmentType.PICKUP
            )
            continue
        if asked not in (FulfilmentType.DELIVERY, FulfilmentType.PICKUP):
            raise CartError(f"'{asked}' is not a delivery choice for {shop.name}.")
        if asked == FulfilmentType.DELIVERY and not shop.delivers:
            raise CartError(f"{shop.name} does not deliver — please choose pickup.")
        choices[business_id] = asked
    return choices


def _check_delivery_details(*, choices, delivery):
    """Delivery details are only needed when something is actually being delivered."""
    if FulfilmentType.DELIVERY not in choices.values():
        return {"recipient_name": "", "phone": "", "address": ""}

    delivery = delivery or {}
    cleaned = {
        "recipient_name": (delivery.get("recipient_name") or "").strip(),
        "phone": (delivery.get("phone") or "").strip(),
        "address": (delivery.get("address") or "").strip(),
    }
    missing = [
        label
        for key, label in (
            ("recipient_name", "a name"),
            ("phone", "a phone number"),
            ("address", "a delivery address"),
        )
        if not cleaned[key]
    ]
    if missing:
        raise CartError("Please add " + " and ".join(missing) + " for the delivery.")
    return cleaned


@transaction.atomic
def checkout_cart(*, customer, fulfilment=None, delivery=None) -> CheckoutGroup:
    """
    Convert the customer's cart into orders — ONE ORDER PER SHOP — grouped in a
    CheckoutGroup that the customer pays for with a single payment.

    Stock deduction logic:
    - If product uses channel allocation → deduct from smartmall_allocation
    - If product uses main stock → deduct from stock
    This ensures physical store stock is never accidentally reduced by SmartMall orders.

    The stock is held for 30 minutes. If the orders are not paid in that time they
    are cancelled and the stock goes back to the same bucket.

    `fulfilment` maps a shop id to "delivery" or "pickup". A shop left out (or the
    whole argument left out) defaults to delivery if that shop delivers, otherwise
    pickup. `delivery` carries where the goods are going:
    {"recipient_name": ..., "phone": ..., "address": ...}. It is required as soon as
    one shop is being delivered. Check-O runs no riders: each shop delivers itself
    and its own fee is copied onto the order, so a later price change by the shop
    never moves the amount the customer already agreed to.
    """
    cart = Cart.objects.prefetch_related(
        "items__product__business"
    ).select_for_update().filter(customer=customer).first()

    if not cart or not cart.items.exists():
        raise CartError("Your cart is empty.")

    # Free up stock held by unpaid orders whose payment window has passed
    release_expired_holds(product_ids=list(cart.items.values_list("product_id", flat=True)))

    items = list(cart.items.select_related("product__business").order_by("created_at"))

    # --- Validation pass ---
    for item in items:
        product = item.product
        if not product.is_active:
            raise CartError(f"'{product.name}' is no longer available.")
        if product.business.status != BusinessStatus.APPROVED:
            raise CartError(f"'{product.name}' is from an unapproved vendor.")
        if item.quantity > product.available_stock:
            raise CartError(
                f"{product.business.name} now has only {product.available_stock} "
                f"of '{product.name}'. Please reduce it in your cart."
            )

    # --- Group cart lines by shop (keeps the order shops were added in) ---
    items_by_shop = {}
    shops = {}
    for item in items:
        items_by_shop.setdefault(item.product.business_id, []).append(item)
        shops[item.product.business_id] = item.product.business

    choices = _resolve_fulfilment(shops=shops, requested=fulfilment)
    delivery = _check_delivery_details(choices=choices, delivery=delivery)

    group = CheckoutGroup.objects.create(customer=customer, total=Decimal("0.00"))
    group_total = Decimal("0.00")

    for business_id, shop_items in items_by_shop.items():
        shop = shops[business_id]
        choice = choices[business_id]
        delivering = choice == FulfilmentType.DELIVERY
        fee = shop.delivery_fee if delivering else Decimal("0.00")

        order = Order.objects.create(
            customer=customer,
            business_id=business_id,
            checkout_group=group,
            status=OrderStatus.PENDING_PAYMENT,
            total=Decimal("0.00"),
            fulfilment_type=choice,
            delivery_fee=fee,
            delivery_address=delivery["address"] if delivering else "",
            recipient_name=delivery["recipient_name"] if delivering else "",
            delivery_phone=delivery["phone"] if delivering else "",
        )
        if not delivering:
            order.generate_pickup_code()
            order.set_pickup_deadline()
            order.save(update_fields=["pickup_code", "pickup_deadline", "updated_at"])

        total = Decimal("0.00")

        # --- Hold stock (30-minute payment window) and create order lines ---
        for item in shop_items:
            product = Product.objects.select_for_update().get(pk=item.product_id)
            if item.quantity > product.available_stock:
                raise CartError(
                    f"{product.business.name} now has only {product.available_stock} "
                    f"of '{product.name}'. Please reduce it in your cart."
                )
            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=item.quantity,
                unit_price=product.price,
            )
            total += product.price * item.quantity

            # Hold the units from the correct bucket (SmartMall allocation or
            # main stock). Released automatically if unpaid after 30 minutes.
            reserve_stock(order=order, product=product, quantity=item.quantity)

        # `total` is the whole amount charged for this shop, delivery included, so
        # payments and refunds need no separate fee handling.
        order.total = total + fee
        order.save(update_fields=["total", "updated_at"])
        group_total += order.total

    group.total = group_total
    group.save(update_fields=["total", "updated_at"])

    # --- Clear cart ---
    cart.items.all().delete()

    return group


def checkout(*, customer) -> Order:
    """
    Single-shop convenience wrapper around checkout_cart(): returns the one Order.
    Raises CartError if the cart has items from more than one shop — use
    checkout_cart() for that.
    """
    cart = Cart.objects.filter(customer=customer).first()
    if cart and cart.items.values("product__business_id").distinct().count() > 1:
        raise CartError("Your cart has items from several shops. Use checkout_cart().")
    group = checkout_cart(customer=customer)
    return group.orders.get()
