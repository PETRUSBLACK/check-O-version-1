from django.conf import settings
from django.db import models

from apps.products.models import Product
from core.models import UUIDTimeStampedModel


class Cart(UUIDTimeStampedModel):
    """
    One active cart per customer at a time.
    A cart is a staging area before checkout converts it into an Order.
    """
    customer = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="cart",
    )

    class Meta:
        db_table = "cart_cart"

    def __str__(self) -> str:
        return f"Cart({self.customer_id})"

    @property
    def total(self):
        return sum(item.line_total for item in self.items.select_related("product").all())

    @property
    def item_count(self):
        return self.items.count()


class CartItem(UUIDTimeStampedModel):
    """
    A single product line in a cart.
    Quantity is always at least 1.
    """
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name="items",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="cart_items",
    )
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = "cart_cartitem"
        unique_together = ("cart", "product")

    def __str__(self) -> str:
        return f"{self.quantity}x {self.product_id} in Cart({self.cart_id})"

    @property
    def line_total(self):
        return self.product.price * self.quantity
