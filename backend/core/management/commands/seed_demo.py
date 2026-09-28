"""
Fill the database with believable Asaba shops and goods, so the app has
something real-looking to show while it's being built.

    python manage.py seed_demo                # add or refresh the demo data
    python manage.py seed_demo --with-orders  # ...and some orders to look at
    python manage.py seed_demo --wipe         # remove it all again

Safe to run more than once: shops are matched by slug and updated rather than
duplicated. It only ever touches rows it created (slugs prefixed "demo-").

The prices are rough Asaba market prices and the coordinates are approximate
points around the city — good enough to see distances and sorting work, not a
survey. Change them freely.
"""

from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.businesses.choices import BusinessCategory, BusinessStatus
from apps.businesses.models import Business, BusinessLocation
from apps.products.models import Product
from apps.users.models import User, UserRole

PASSWORD = "checko12345"

# Roughly the centre of Asaba; the shops sit within a few kilometres of it.
SHOPS = [
    {
        "slug": "demo-mama-nkechi",
        "name": "Mama Nkechi Stores",
        "owner": "nkechi@demo.check-o.ng",
        "category": BusinessCategory.SUPERMARKET,
        "address": "42 Nnebisi Road, opposite the old bank",
        "lat": "6.2010", "lng": "6.7340",
        "delivers": True, "fee": "1500.00",
        "tagline": "Foodstuff and provisions since 1998",
        "products": [
            # name, price, stock, allocation, description
            ("Rice 50kg bag", "78000.00", 40, 12, "Long grain parboiled rice, sealed 50kg bag."),
            ("Golden Penny Semovita 2kg", "4200.00", 30, None, "2kg pack."),
            ("Groundnut Oil 5 litres", "12500.00", 3, None, "Pure groundnut oil in a 5 litre keg."),
            ("Garri (white) 4 litres", "3500.00", 25, None, "Measured in the four-litre rubber."),
            ("Peak Milk Refill 400g", "6200.00", 0, None, "Out of stock until Friday."),
            ("Titus Sardine (tin)", "2800.00", 60, None, "Single tin."),
        ],
    },
    {
        "slug": "demo-grace-chemist",
        "name": "Grace Chemist",
        "owner": "grace@demo.check-o.ng",
        "category": BusinessCategory.PHARMACY,
        "address": "5 Okpanam Road, beside the filling station",
        "lat": "6.2062", "lng": "6.7285",
        "delivers": True, "fee": "1000.00",
        "tagline": "Registered pharmacy, open till 9pm",
        "products": [
            ("Paracetamol 500mg (pack of 20)", "900.00", 100, None, "For pain and fever."),
            ("Vitamin C 1000mg (30 tablets)", "3200.00", 25, None, "One tablet daily."),
            ("Malaria test kit", "2500.00", 8, None, "Single-use rapid test."),
            ("Cough syrup 100ml", "2100.00", 4, None, "Adult formula."),
            ("Blood pressure monitor", "38000.00", 2, 2, "Digital, upper arm cuff."),
        ],
    },
    {
        "slug": "demo-chidis-kitchen",
        "name": "Chidi's Kitchen",
        "owner": "chidi@demo.check-o.ng",
        "category": BusinessCategory.RESTAURANT,
        "address": "18 DLA Road, upstairs",
        "lat": "6.1955", "lng": "6.7318",
        "delivers": True, "fee": "800.00",
        "tagline": "Hot food from 7am",
        "products": [
            ("Jollof rice and chicken", "4500.00", 40, None, "Served with a piece of chicken."),
            ("Egusi soup and pounded yam", "5500.00", 25, None, "With assorted meat."),
            ("Pepper soup (goat meat)", "4000.00", 15, None, "Hot and peppery."),
            ("Fried rice (takeaway pack)", "4200.00", 30, None, "Large pack."),
            ("Moi moi (wrap)", "1200.00", 5, None, "Wrapped in leaves."),
        ],
    },
    {
        "slug": "demo-bright-electronics",
        "name": "Bright Electronics",
        "owner": "bright@demo.check-o.ng",
        "category": BusinessCategory.ELECTRONICS,
        "address": "7 Ibusa Road, Ogbeogonogo market side",
        "lat": "6.2115", "lng": "6.7226",
        "delivers": False, "fee": "0.00",
        "tagline": "Phones, chargers and accessories",
        "products": [
            ("Type-C fast charger", "7500.00", 45, None, "25W, with cable."),
            ("Power bank 20000mAh", "22000.00", 12, 6, "Charges a phone about four times."),
            ("Phone pouch (universal)", "2500.00", 60, None, "Fits most 6-inch phones."),
            ("Bluetooth earbuds", "18000.00", 3, None, "With charging case."),
            ("Extension box (4 sockets)", "9500.00", 20, None, "Surge protected, 3 metre cable."),
        ],
    },
    {
        "slug": "demo-adaeze-fashion",
        "name": "Adaeze Fashion House",
        "owner": "adaeze@demo.check-o.ng",
        "category": BusinessCategory.FASHION,
        "address": "22 Summit Road, near the junction",
        "lat": "6.1902", "lng": "6.7402",
        "delivers": True, "fee": "2000.00",
        "tagline": "Ready-to-wear and Ankara",
        "products": [
            ("Ankara two-piece (ladies)", "28000.00", 6, None, "Made to standard sizes."),
            ("Men's kaftan (plain)", "35000.00", 4, 2, "Cotton, with cap."),
            ("Ankara fabric, 6 yards", "16000.00", 18, None, "Hollandais print."),
            ("Ladies' handbag", "21000.00", 2, None, "Faux leather."),
        ],
    },
    {
        "slug": "demo-favour-beauty",
        "name": "Favour Beauty Shop",
        "owner": "favour@demo.check-o.ng",
        "category": BusinessCategory.BEAUTY,
        "address": "3 Cable Point Road",
        "lat": "6.1830", "lng": "6.7255",
        "delivers": False, "fee": "0.00",
        "tagline": "Hair, skincare and cosmetics",
        "products": [
            ("Shea butter 500g", "4500.00", 30, None, "Unrefined, from Kano."),
            ("Braiding attachment (pack)", "3800.00", 40, None, "Colour 1B."),
            ("Body lotion 400ml", "6500.00", 15, None, "For dry skin."),
            ("Hair dryer", "26000.00", 2, None, "Two heat settings."),
        ],
    },
]


class Command(BaseCommand):
    help = "Fill the database with demo Asaba shops, products and a test customer."

    def add_arguments(self, parser):
        parser.add_argument(
            "--wipe",
            action="store_true",
            help="Delete the demo data instead of creating it.",
        )
        parser.add_argument(
            "--with-orders",
            action="store_true",
            help="Also place sample orders, at every stage a shop will see.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["wipe"]:
            return self.wipe()

        customer = self.make_user("shopper@demo.check-o.ng", UserRole.CUSTOMER, "Ada", "Shopper")

        for spec in SHOPS:
            owner = self.make_user(
                spec["owner"], UserRole.VENDOR, spec["name"].split()[0], "Owner"
            )
            shop = self.make_shop(spec, owner)
            for product in spec["products"]:
                self.make_product(shop, *product)
            self.stdout.write(
                f"  {shop.name}: {len(spec['products'])} products, "
                + ("delivers" if shop.delivers else "collection only")
            )

        if options["with_orders"]:
            self.stdout.write("")
            self.make_orders(customer)

        self.stdout.write(self.style.SUCCESS(f"\nDone. {len(SHOPS)} shops added around Asaba."))
        self.stdout.write(
            "\nSign in on your phone as:\n"
            f"  {customer.email} / {PASSWORD}\n"
            "\nEach shop owner can sign in too, e.g. nkechi@demo.check-o.ng with the same password.\n"
            "Run 'python manage.py seed_demo --wipe' to remove all of this again."
        )

    # ─── Sample orders ────────────────────────────────────────────────────────

    def make_orders(self, customer):
        """
        Place a few orders and leave them at different stages, so the seller
        screens have the whole spread to show rather than one lonely order.
        """
        from apps.cart.services.cart_service import add_to_cart, checkout_cart, clear_cart
        from apps.orders.models import Order, OrderStatus
        from apps.orders.services.order_service import cancel_order, transition_order_status

        delivery = {
            "recipient_name": "Ada Shopper",
            "phone": "08031112222",
            "address": "14 Okpanam Road, opposite the filling station, Asaba",
        }

        # (shop slug, [(product name, quantity)], where it should end up)
        plan = [
            ("demo-mama-nkechi", [("Rice 50kg bag", 2), ("Golden Penny Semovita 2kg", 1)], "paid"),
            ("demo-mama-nkechi", [("Garri (white) 4 litres", 3)], "processing"),
            ("demo-grace-chemist", [("Paracetamol 500mg (pack of 20)", 2)], "shipped"),
            ("demo-chidis-kitchen", [("Jollof rice and chicken", 2)], "delivered"),
            ("demo-bright-electronics", [("Type-C fast charger", 1)], "ready_for_pickup"),
            ("demo-favour-beauty", [("Shea butter 500g", 2)], "paid"),
            ("demo-adaeze-fashion", [("Ankara fabric, 6 yards", 1)], "cancelled"),
        ]

        made = 0
        for slug, lines, target in plan:
            shop = Business.objects.filter(slug=slug).first()
            if not shop:
                continue
            clear_cart(customer=customer)
            ok = True
            for name, quantity in lines:
                product = Product.objects.filter(business=shop, name=name).first()
                if not product or product.available_stock < quantity:
                    ok = False
                    break
                add_to_cart(customer=customer, product_id=product.id, quantity=quantity)
            if not ok:
                clear_cart(customer=customer)
                continue

            choice = "delivery" if shop.delivers else "pickup"
            group = checkout_cart(
                customer=customer,
                fulfilment={str(shop.id): choice},
                delivery=delivery if choice == "delivery" else None,
            )
            order = group.orders.get()
            self.walk_to(order, target, customer)
            made += 1
            self.stdout.write(f"  {shop.name}: order left at '{target}'")

        clear_cart(customer=customer)
        self.stdout.write(self.style.SUCCESS(f"  {made} sample orders placed."))

    def walk_to(self, order, target, customer):
        """Move an order along the same path a real one takes, one step at a time."""
        from apps.orders.models import Order, OrderStatus
        from apps.orders.services.order_service import cancel_order, transition_order_status

        if target == "pending_payment":
            return

        # Everything else starts by being paid for.
        from apps.orders.services.order_service import mark_order_paid

        mark_order_paid(order_id=order.id)
        order.refresh_from_db()

        if target == "cancelled":
            cancel_order(
                order_id=order.id,
                user=order.business.owner,
                reason="out_of_stock",
                note="",
            )
            return

        path = {
            "paid": [],
            "processing": ["processing"],
            "packaging": ["processing", "packaging"],
            "shipped": ["processing", "packaging", "shipped"],
            "delivered": ["processing", "packaging", "shipped", "delivered"],
            "ready_for_pickup": ["processing", "ready_for_pickup"],
            "collected": ["processing", "ready_for_pickup", "collected"],
        }.get(target, [])

        for step in path:
            transition_order_status(order_id=order.id, to_status=step)

    # ─── Pieces ───────────────────────────────────────────────────────────────

    def make_user(self, email, role, first, last):
        user = User.objects.filter(email=email).first()
        if user:
            return user
        return User.objects.create_user(
            email=email, password=PASSWORD, role=role, first_name=first, last_name=last
        )

    def make_shop(self, spec, owner):
        shop, _ = Business.objects.update_or_create(
            slug=spec["slug"],
            defaults={
                "owner": owner,
                "name": spec["name"],
                "legal_name": spec["name"] + " Ltd",
                "registration_number": "RC" + str(abs(hash(spec["slug"])) % 9000000 + 1000000),
                "category": spec["category"],
                "status": BusinessStatus.APPROVED,
                "tagline": spec["tagline"],
                "address": spec["address"],
                "business_phone": "0803" + str(abs(hash(spec["name"])) % 9000000 + 1000000),
                "delivers": spec["delivers"],
                "delivery_fee": Decimal(spec["fee"]),
                "is_active": True,
            },
        )
        # Without coordinates a shop never appears in "Shops near you".
        BusinessLocation.objects.update_or_create(
            business=shop,
            defaults={
                "address": spec["address"],
                "city": "Asaba",
                "state": "Delta",
                "country": "Nigeria",
                "latitude": Decimal(spec["lat"]),
                "longitude": Decimal(spec["lng"]),
            },
        )
        return shop

    def make_product(self, shop, name, price, stock, allocation, description):
        Product.objects.update_or_create(
            business=shop,
            name=name,
            defaults={
                "price": Decimal(price),
                "stock": stock,
                "smartmall_allocation": allocation,
                "description": description,
                "is_active": True,
            },
        )

    # ─── Undo ─────────────────────────────────────────────────────────────────

    def wipe(self):
        from apps.orders.models import CheckoutGroup, Order
        from apps.payments.models import Payment

        shops = Business.objects.filter(slug__startswith="demo-")
        emails = [s["owner"] for s in SHOPS] + ["shopper@demo.check-o.ng"]
        count = shops.count()
        products = Product.objects.filter(business__in=shops).count()

        # Orders and payments hold the shop and its products with PROTECT, so any
        # test order made against this data has to go first. Everything here was
        # created by this command, so nothing real is at risk.
        orders = Order.objects.filter(business__in=shops)
        groups = CheckoutGroup.objects.filter(orders__in=orders).distinct()
        order_count = orders.count()
        Payment.objects.filter(order__in=orders).delete()
        Payment.objects.filter(checkout_group__in=groups).delete()
        orders.delete()
        CheckoutGroup.objects.filter(orders__isnull=True, customer__email__in=emails).delete()

        shops.delete()  # products and locations go with the shop
        User.objects.filter(email__in=emails).delete()
        self.stdout.write(
            self.style.SUCCESS(
                f"Removed {count} demo shops, {products} products and {order_count} test orders."
            )
        )
