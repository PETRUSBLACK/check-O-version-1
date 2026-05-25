from django.db import transaction

from apps.businesses.models import Business
from apps.products.models import Product


def create_product(*, business: Business, **fields) -> Product:
    with transaction.atomic():
        return Product.objects.create(business=business, **fields)


def adjust_stock(*, product_id, delta: int) -> Product:
    product = Product.objects.select_for_update().get(pk=product_id)
    new_stock = int(product.stock) + delta
    if new_stock < 0:
        raise ValueError("Insufficient stock")
    product.stock = new_stock
    product.save(update_fields=["stock", "updated_at"])
    return product
