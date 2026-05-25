"""
SmartMall AI Tools.
Functions the AI can call to query real data from the SmartMall database.
"""

import logging
from decimal import Decimal
from math import asin, cos, radians, sin, sqrt

logger = logging.getLogger(__name__)


def _haversine_km(lat1, lon1, lat2, lon2) -> float:
    R = 6371
    lat1, lon1, lat2, lon2 = map(radians, [float(lat1), float(lon1), float(lat2), float(lon2)])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return R * 2 * asin(sqrt(a))


# ─── Customer Tools ────────────────────────────────────────────────────────────

def search_products(query: str, max_price: float = None, lat: float = None, lng: float = None, radius_km: float = 10, limit: int = 10) -> dict:
    """Search products with optional price and location filter."""
    import django
    import os
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
    django.setup()

    from apps.products.models import Product
    from apps.businesses.models import BusinessStatus

    qs = Product.objects.filter(
        is_active=True,
        business__status=BusinessStatus.APPROVED,
    ).select_related("business__location", "business__ratings")

    if query:
        from django.db.models import Q
        qs = qs.filter(Q(name__icontains=query) | Q(description__icontains=query))

    if max_price:
        qs = qs.filter(price__lte=Decimal(str(max_price)))

    results = []
    for product in qs[:50]:
        distance = None
        if lat and lng and hasattr(product.business, "location") and product.business.location:
            loc = product.business.location
            distance = round(_haversine_km(lat, lng, loc.latitude, loc.longitude), 2)
            if distance > radius_km:
                continue

        ratings = product.business.ratings.all()
        avg_rating = round(sum(r.score for r in ratings) / len(ratings), 1) if ratings else None

        results.append({
            "product_id": str(product.pk),
            "name": product.name,
            "description": product.description[:100] if product.description else "",
            "price": float(product.price),
            "stock": product.stock,
            "shop_name": product.business.name,
            "shop_id": str(product.business.pk),
            "distance_km": distance,
            "avg_rating": avg_rating,
        })

    if lat and lng:
        results.sort(key=lambda x: x["distance_km"] or 9999)

    return {"products": results[:limit], "total_found": len(results)}


def get_product_details(product_id: str) -> dict:
    """Get full details of a product."""
    from apps.products.models import Product
    from apps.ads.models import ProductPromotion
    from django.utils import timezone

    product = Product.objects.filter(pk=product_id).select_related("business__location").first()
    if not product:
        return {"error": "Product not found"}

    ratings = product.business.ratings.all()
    avg_rating = round(sum(r.score for r in ratings) / len(ratings), 1) if ratings else None

    active_promo = ProductPromotion.objects.filter(
        product=product, is_active=True,
        starts_at__lte=timezone.now(), ends_at__gte=timezone.now(),
    ).first()

    return {
        "product_id": str(product.pk),
        "name": product.name,
        "description": product.description,
        "price": float(product.price),
        "discounted_price": float(active_promo.discounted_price) if active_promo else None,
        "discount_percent": float(active_promo.discount_percent) if active_promo else None,
        "stock": product.stock,
        "in_stock": product.stock > 0,
        "shop": {
            "id": str(product.business.pk),
            "name": product.business.name,
            "rating": avg_rating,
            "city": product.business.location.city if hasattr(product.business, "location") and product.business.location else "",
            "address": product.business.location.full_address if hasattr(product.business, "location") and product.business.location else "",
        },
    }


def compare_products(product_ids: list) -> dict:
    """Compare multiple products side by side."""
    from apps.products.models import Product

    products = Product.objects.filter(pk__in=product_ids).select_related("business")
    return {
        "comparison": [
            {
                "product_id": str(p.pk),
                "name": p.name,
                "price": float(p.price),
                "stock": p.stock,
                "shop": p.business.name,
                "description": p.description[:150] if p.description else "",
            }
            for p in products
        ]
    }


def find_nearby_shops(lat: float, lng: float, product_query: str = "", radius_km: float = 10) -> dict:
    """Find shops near a location."""
    from apps.businesses.models import BusinessLocation, BusinessStatus

    locations = BusinessLocation.objects.filter(
        business__status=BusinessStatus.APPROVED
    ).select_related("business__ratings")

    results = []
    for loc in locations:
        distance = _haversine_km(lat, lng, loc.latitude, loc.longitude)
        if distance > radius_km:
            continue
        if product_query:
            has_product = loc.business.products.filter(
                name__icontains=product_query, is_active=True, stock__gt=0
            ).exists()
            if not has_product:
                continue
        ratings = loc.business.ratings.all()
        avg_rating = round(sum(r.score for r in ratings) / len(ratings), 1) if ratings else None
        results.append({
            "shop_id": str(loc.business.pk),
            "name": loc.business.name,
            "address": loc.full_address,
            "city": loc.city,
            "distance_km": round(distance, 2),
            "avg_rating": avg_rating,
        })

    results.sort(key=lambda x: x["distance_km"])
    return {"shops": results[:10]}


def get_recommendations(customer_id: str, lat: float = None, lng: float = None, limit: int = 8) -> dict:
    """Get personalised recommendations for a customer."""
    from apps.orders.models import Order
    from apps.products.models import Product
    from apps.businesses.models import BusinessStatus

    past_orders = Order.objects.filter(
        customer_id=customer_id
    ).prefetch_related("items__product")

    purchased_ids = set()
    name_keywords = set()
    for order in past_orders:
        for item in order.items.all():
            purchased_ids.add(str(item.product_id))
            name_keywords.update(item.product.name.lower().split())

    qs = Product.objects.filter(
        is_active=True,
        business__status=BusinessStatus.APPROVED,
        stock__gt=0,
    ).exclude(pk__in=purchased_ids).select_related("business__location", "business__ratings")

    scored = []
    for product in qs[:100]:
        score = 0
        score += len(set(product.name.lower().split()) & name_keywords) * 2
        if lat and lng and hasattr(product.business, "location") and product.business.location:
            dist = _haversine_km(lat, lng, product.business.location.latitude, product.business.location.longitude)
            score += max(0, 10 - int(dist))
        ratings = product.business.ratings.all()
        if ratings:
            score += sum(r.score for r in ratings) / len(ratings)
        scored.append((score, product))

    scored.sort(key=lambda x: x[0], reverse=True)
    return {
        "recommendations": [
            {
                "product_id": str(p.pk),
                "name": p.name,
                "price": float(p.price),
                "shop": p.business.name,
                "reason": "Based on your history" if name_keywords else "Popular on SmartMall",
            }
            for _, p in scored[:limit]
        ]
    }


def get_order_status(order_id: str, customer_id: str) -> dict:
    """Get order status and tracking info."""
    from apps.orders.models import Order

    order = Order.objects.filter(
        pk=order_id, customer_id=customer_id
    ).prefetch_related("items__product").first()

    if not order:
        return {"error": "Order not found"}

    tracking = None
    try:
        if hasattr(order, "shipment"):
            s = order.shipment
            tracking = {
                "tracking_number": s.tracking_number,
                "status": s.status,
                "events": [
                    {"status": e.status, "note": e.note, "time": e.created_at.strftime("%d %b %Y %H:%M")}
                    for e in s.tracking_events.all()[:5]
                ],
            }
    except Exception:
        pass

    return {
        "order_id": str(order.pk),
        "status": order.status,
        "total": float(order.total),
        "fulfilment_type": order.fulfilment_type,
        "pickup_code": order.pickup_code or None,
        "items": [{"product": i.product.name, "qty": i.quantity} for i in order.items.all()],
        "tracking": tracking,
    }


def get_featured_deals(lat: float = None, lng: float = None, limit: int = 6) -> dict:
    """Get current featured deals and flash sales."""
    from apps.ads.services.promotion_service import get_featured_products, get_active_discounts

    featured = get_featured_products(limit=limit)
    discounts = get_active_discounts()[:limit]

    return {
        "featured": [
            {
                "product": p.product.name,
                "product_id": str(p.product.pk),
                "shop": p.product.business.name,
                "price": float(p.product.price),
                "discounted_price": float(p.discounted_price),
                "discount_percent": float(p.discount_percent) if p.discount_percent else 0,
            }
            for p in featured
        ],
        "flash_sales": [
            {
                "product": p.product.name,
                "product_id": str(p.product.pk),
                "original_price": float(p.product.price),
                "discounted_price": float(p.discounted_price),
                "discount_percent": float(p.discount_percent),
                "ends_at": p.ends_at.strftime("%d %b %Y %H:%M"),
            }
            for p in discounts
        ],
    }


# ─── Vendor Tools ──────────────────────────────────────────────────────────────

def get_vendor_sales_summary(business_id: str, days: int = 30) -> dict:
    """Get vendor sales summary."""
    from apps.orders.models import Order, OrderItem, OrderStatus
    from django.utils import timezone

    since = timezone.now() - timezone.timedelta(days=days)
    items = OrderItem.objects.filter(
        product__business_id=business_id,
        order__status__in=[OrderStatus.PAID, OrderStatus.PROCESSING, OrderStatus.DELIVERED, OrderStatus.COLLECTED],
        order__created_at__gte=since,
    ).select_related("product")

    total_revenue = sum(i.line_total for i in items)
    top = {}
    for i in items:
        top[i.product.name] = top.get(i.product.name, 0) + i.quantity

    return {
        "period_days": days,
        "total_revenue": float(total_revenue),
        "total_orders": items.values("order").distinct().count(),
        "top_products": [{"name": n, "units_sold": q} for n, q in sorted(top.items(), key=lambda x: x[1], reverse=True)[:5]],
    }


def get_vendor_pending_orders(business_id: str) -> dict:
    """Get vendor's pending orders."""
    from apps.orders.models import Order, OrderStatus

    orders = Order.objects.filter(
        items__product__business_id=business_id,
        status__in=[OrderStatus.PAID, OrderStatus.PROCESSING, OrderStatus.PACKAGING, OrderStatus.READY_FOR_PICKUP],
    ).distinct().prefetch_related("items__product").order_by("-created_at")[:20]

    return {
        "pending_orders": [
            {
                "order_id": str(o.pk),
                "status": o.status,
                "total": float(o.total),
                "fulfilment_type": o.fulfilment_type,
                "created_at": o.created_at.strftime("%d %b %Y %H:%M"),
                "items": [{"product": i.product.name, "qty": i.quantity} for i in o.items.filter(product__business_id=business_id)],
            }
            for o in orders
        ],
    }


def get_vendor_low_stock(business_id: str, threshold: int = 5) -> dict:
    """Get vendor's low stock products."""
    from apps.products.models import Product

    low = Product.objects.filter(business_id=business_id, is_active=True, stock__lte=threshold).order_by("stock")
    return {
        "low_stock_products": [
            {"product_id": str(p.pk), "name": p.name, "stock": p.stock, "price": float(p.price)}
            for p in low
        ],
        "threshold": threshold,
    }


# ─── Tool Dispatcher ───────────────────────────────────────────────────────────

TOOL_FUNCTIONS = {
    "search_products": search_products,
    "get_product_details": get_product_details,
    "compare_products": compare_products,
    "find_nearby_shops": find_nearby_shops,
    "get_recommendations": get_recommendations,
    "get_order_status": get_order_status,
    "get_featured_deals": get_featured_deals,
    "get_vendor_sales_summary": get_vendor_sales_summary,
    "get_vendor_pending_orders": get_vendor_pending_orders,
    "get_vendor_low_stock": get_vendor_low_stock,
}


def dispatch_tool(tool_name: str, tool_input: dict) -> str:
    """Execute a tool call and return the result as a JSON string."""
    import json
    func = TOOL_FUNCTIONS.get(tool_name)
    if not func:
        return json.dumps({"error": f"Unknown tool: {tool_name}"})
    try:
        result = func(**tool_input)
        return json.dumps(result, default=str)
    except Exception as exc:
        logger.exception("tool_error tool=%s", tool_name)
        return json.dumps({"error": str(exc)})
