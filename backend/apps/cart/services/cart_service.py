from uuid import UUID
from decimal import Decimal

from django.db import transaction

from apps.businesses.models import Business
from apps.businesses.choices import BusinessCategory, BusinessStatus
from apps.cart.models import Cart, CartItem
from apps.orders.models import CheckoutGroup, Order, OrderItem, OrderStatus
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
            raise CartError(
                f"Only {available} unit(s) available for SmartMall orders. "
                f"You already have {item.quantity} in your cart."
            )

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
            f"Only {item.product.available_stock} unit(s) available for SmartMall orders."
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

@transaction.atomic
def checkout_cart(*, customer) -> CheckoutGroup:
    """
    Convert the customer's cart into orders — ONE ORDER PER SHOP — grouped in a
    CheckoutGroup that the customer pays for with a single payment.

    Stock deduction logic:
    - If product uses channel allocation → deduct from smartmall_allocation
    - If product uses main stock → deduct from stock
    This ensures physical store stock is never accidentally reduced by SmartMall orders.

    The stock is held for 30 minutes. If the orders are not paid in that time they
    are cancelled and the stock goes back to the same bucket.
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
                f"Insufficient stock for '{product.name}'. "
                f"Requested {item.quantity}, available {product.available_stock}."
            )

    # --- Group cart lines by shop (keeps the order shops were added in) ---
    items_by_shop = {}
    for item in items:
        items_by_shop.setdefault(item.product.business_id, []).append(item)

    group = CheckoutGroup.objects.create(customer=customer, total=Decimal("0.00"))
    group_total = Decimal("0.00")

    for business_id, shop_items in items_by_shop.items():
        order = Order.objects.create(
            customer=customer,
            business_id=business_id,
            checkout_group=group,
            status=OrderStatus.PENDING_PAYMENT,
            total=Decimal("0.00"),
        )
        total = Decimal("0.00")

        # --- Hold stock (30-minute payment window) and create order lines ---
        for item in shop_items:
            product = Product.objects.select_for_update().get(pk=item.product_id)
            if item.quantity > product.available_stock:
                raise CartError(
                    f"Insufficient stock for '{product.name}'. "
                    f"Requested {item.quantity}, available {product.available_stock}."
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

        order.total = total
        order.save(update_fields=["total", "updated_at"])
        group_total += total

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
