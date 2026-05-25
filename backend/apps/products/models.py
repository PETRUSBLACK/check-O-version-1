from django.db import models

from apps.businesses.models import Business
from core.models import UUIDTimeStampedModel


class Product(UUIDTimeStampedModel):
    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name="products",
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    # ─── Channel Allocation ───────────────────────────────────────────────────
    # Vendors with multiple sales channels (physical store, their own app, etc.)
    # can reserve a specific portion of stock exclusively for SmartMall orders.
    #
    # How it works:
    #   - If smartmall_allocation is NULL → SmartMall uses the main `stock` field
    #     (default behaviour, works for all small traders)
    #   - If smartmall_allocation is SET → SmartMall only sells up to this number,
    #     regardless of what `stock` shows. Physical store sales don't affect it.
    #
    # Example: Ebeano has 100 bags of rice (stock=100).
    #   They set smartmall_allocation=20.
    #   SmartMall shows 20 available. Physical store has its own 80.
    #   No conflict between channels.
    smartmall_allocation = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=(
            "Optional. Reserve a specific stock quantity for SmartMall orders only. "
            "Leave blank to use the main stock field (recommended for small vendors). "
            "Use this if you sell on multiple channels (physical store, other apps)."
        ),
    )

    class Meta:
        db_table = "products_product"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    @property
    def available_stock(self) -> int:
        """
        The stock available for SmartMall orders.
        - If smartmall_allocation is set → use that
        - Otherwise → use main stock field
        """
        if self.smartmall_allocation is not None:
            return self.smartmall_allocation
        return self.stock

    @property
    def uses_channel_allocation(self) -> bool:
        """True if this product has a dedicated SmartMall allocation."""
        return self.smartmall_allocation is not None
