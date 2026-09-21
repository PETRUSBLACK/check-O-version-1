"""
Products application views.
"""

from .product import ProductViewSet
from .category import ProductCategoryViewSet
from .image import ProductImageViewSet
from .variant import ProductVariantViewSet
from .inventory import InventoryMovementViewSet
from .alert import InventoryAlertViewSet
from .embedding import ProductEmbeddingViewSet

__all__ = [
    "ProductViewSet",
    "ProductCategoryViewSet",
    "ProductImageViewSet",
    "ProductVariantViewSet",
    "InventoryMovementViewSet",
    "InventoryAlertViewSet",
    "ProductEmbeddingViewSet",
]