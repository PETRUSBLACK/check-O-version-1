"""
Product catalog service.

Contains business logic for creating and managing products.
"""

from apps.products.models import Product


def create_product(
    *,
    business,
    category=None,
    name,
    description="",
    price,
    stock=0,
    sku="",
    barcode="",
    is_active=True,
):
    """
    Create a new product.

    The Product model will automatically generate its slug.
    """

    product = Product.objects.create(
        business=business,
        category=category,
        name=name,
        description=description,
        price=price,
        stock=stock,
        sku=sku,
        barcode=barcode,
        is_active=is_active,
    )

    return product