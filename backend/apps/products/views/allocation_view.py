"""
Channel Allocation View.

Allows vendors to set a dedicated SmartMall stock allocation
for products they sell across multiple channels.
"""

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from apps.products.models import Product
from apps.products.serializers import ProductSerializer
from core.permissions import IsVendorOrAdmin


class SetChannelAllocationView(APIView):
    """
    Workflow: Vendor sets or updates the SmartMall stock allocation
    for a product they sell across multiple channels.

    Use this if you sell the same product:
    - In your physical store
    - Through your own app
    - Through other platforms

    Setting an allocation means SmartMall will only sell up to
    that number — independent of your total store stock.

    Set allocation to null to remove it and use main stock again.
    """
    permission_classes = [IsAuthenticated, IsVendorOrAdmin]

    @extend_schema(
        tags=["products"],
        summary="Set SmartMall channel allocation for a product",
        description=(
            "Set how many units of this product SmartMall can sell independently "
            "of your physical store or other channels. "
            "Pass `allocation: null` to remove the allocation and use main stock."
        ),
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "allocation": {
                        "type": "integer",
                        "nullable": True,
                        "description": (
                            "Number of units reserved for SmartMall. "
                            "Pass null to remove allocation and use main stock."
                        ),
                        "example": 20,
                    }
                },
                "required": ["allocation"],
            }
        },
        responses={200: ProductSerializer},
    )
    def post(self, request, pk=None):
        product = Product.objects.select_related("business").filter(pk=pk).first()
        if not product:
            return Response({"detail": "Product not found."}, status=404)

        # Verify ownership
        user = request.user
        if not user.is_staff and getattr(user, "role", None) != "admin":
            if product.business.owner_id != user.id:
                return Response(
                    {"detail": "You can only manage allocation for your own products."},
                    status=status.HTTP_403_FORBIDDEN,
                )

        allocation = request.data.get("allocation")

        # Validate allocation value
        if allocation is not None:
            try:
                allocation = int(allocation)
            except (TypeError, ValueError):
                return Response(
                    {"detail": "allocation must be a positive integer or null."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if allocation < 0:
                return Response(
                    {"detail": "allocation cannot be negative."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if allocation > product.stock:
                return Response(
                    {
                        "detail": (
                            f"Allocation ({allocation}) cannot exceed total stock ({product.stock}). "
                            f"Update your total stock first if needed."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        product.smartmall_allocation = allocation
        product.save(update_fields=["smartmall_allocation", "updated_at"])

        # Build a clear message for the vendor
        if allocation is not None:
            message = (
                f"SmartMall allocation set to {allocation} units. "
                f"SmartMall will only sell up to {allocation} units of this product, "
                f"independent of your physical store stock."
            )
        else:
            message = (
                "Channel allocation removed. "
                "SmartMall will now use your main stock field."
            )

        return Response({
            "message": message,
            "product": ProductSerializer(product).data,
        })


class AllocationStatusView(APIView):
    """
    Get the current channel allocation status for all of a vendor's products.
    Shows which products have allocations set and their available stock.
    """
    permission_classes = [IsAuthenticated, IsVendorOrAdmin]

    @extend_schema(
        tags=["products"],
        summary="Get channel allocation status for all vendor products",
        description="Shows which products have SmartMall allocations and their current available stock.",
    )
    def get(self, request, business_id=None):
        from apps.businesses.models import Business

        business = Business.objects.filter(pk=business_id).first()
        if not business:
            return Response({"detail": "Business not found."}, status=404)

        user = request.user
        if not user.is_staff and getattr(user, "role", None) != "admin":
            if business.owner_id != user.id:
                return Response({"detail": "Not your business."}, status=403)

        products = Product.objects.filter(
            business=business, is_active=True
        ).order_by("name")

        result = []
        for product in products:
            result.append({
                "product_id": str(product.pk),
                "name": product.name,
                "total_stock": product.stock,
                "smartmall_allocation": product.smartmall_allocation,
                "available_for_smartmall": product.available_stock,
                "uses_channel_allocation": product.uses_channel_allocation,
                "channel_mode": (
                    "allocated" if product.uses_channel_allocation
                    else "shared"
                ),
                "explanation": (
                    f"SmartMall sells from a reserved {product.smartmall_allocation} units "
                    f"(out of {product.stock} total)"
                    if product.uses_channel_allocation
                    else f"SmartMall uses your main stock ({product.stock} units)"
                ),
            })

        allocated_count = sum(1 for p in result if p["uses_channel_allocation"])
        shared_count = len(result) - allocated_count

        return Response({
            "business": business.name,
            "total_products": len(result),
            "using_channel_allocation": allocated_count,
            "using_shared_stock": shared_count,
            "products": result,
        })
