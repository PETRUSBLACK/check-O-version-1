"""
Demand Prediction Model.

Predicts which products a vendor should restock and when,
based on historical order data and seasonal patterns.

Uses a simple but effective approach:
- Calculates average daily sales per product
- Identifies seasonal trends (Sallah, Christmas, back-to-school)
- Computes days until stockout at current sales rate
- Flags products needing urgent restocking
"""

import logging
from collections import defaultdict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


NIGERIAN_SEASONS = {
    "sallah": [(3, 20), (4, 30)],
    "christmas": [(12, 15), (12, 31)],
    "new_year": [(1, 1), (1, 10)],
    "back_to_school": [(9, 1), (9, 20)],
    "rainy_season": [(5, 1), (10, 31)],
    "dry_season": [(11, 1), (3, 31)],
}

SEASONAL_PRODUCTS = {
    "sallah": ["ram", "cow", "goat", "fabric", "clothing", "clothes", "shoes"],
    "christmas": ["rice", "chicken", "turkey", "drinks", "wine", "fabric", "clothes", "gifts"],
    "back_to_school": ["bags", "shoes", "uniform", "book", "stationery", "pen", "pencil"],
    "rainy_season": ["umbrella", "raincoat", "boots", "waterproof"],
}


def _current_season() -> list[str]:
    now = datetime.now()
    active = []
    for season, ranges in NIGERIAN_SEASONS.items():
        start_m, start_d = ranges[0]
        end_m, end_d = ranges[1]
        start = now.replace(month=start_m, day=start_d)
        end = now.replace(month=end_m, day=end_d)
        if start <= now <= end:
            active.append(season)
    return active


def _seasonal_boost(product_name: str) -> float:
    """Return a demand multiplier based on active seasons."""
    name_lower = product_name.lower()
    active_seasons = _current_season()
    boost = 1.0
    for season in active_seasons:
        keywords = SEASONAL_PRODUCTS.get(season, [])
        if any(k in name_lower for k in keywords):
            boost *= 1.5
    return boost


class DemandPredictor:
    """
    Predicts product demand for a vendor's business.
    Uses 90 days of historical order data.
    """

    def forecast_for_business(self, business_id: str) -> dict:
        """
        Generate demand forecasts for all of a vendor's active products.
        Returns urgency-ranked list with restock recommendations.
        """
        try:
            from apps.orders.models import OrderItem, OrderStatus
            from apps.products.models import Product
            from django.utils import timezone

            since = timezone.now() - timedelta(days=90)

            # Get order history
            items = OrderItem.objects.filter(
                product__business_id=business_id,
                order__status__in=[
                    OrderStatus.PAID, OrderStatus.PROCESSING,
                    OrderStatus.DELIVERED, OrderStatus.COLLECTED,
                ],
                order__created_at__gte=since,
            ).select_related("product", "order")

            # Calculate daily sales per product
            sales_by_product = defaultdict(lambda: {"total_sold": 0, "days_active": set(), "product": None})
            for item in items:
                pid = str(item.product_id)
                sales_by_product[pid]["total_sold"] += item.quantity
                sales_by_product[pid]["days_active"].add(item.order.created_at.date())
                sales_by_product[pid]["product"] = item.product

            # Get all active products
            products = Product.objects.filter(business_id=business_id, is_active=True)

            forecasts = []
            for product in products:
                pid = str(product.pk)
                data = sales_by_product.get(pid, {})
                total_sold = data.get("total_sold", 0)
                days_active = len(data.get("days_active", set())) or 1

                avg_daily_sales = total_sold / 90
                seasonal_boost = _seasonal_boost(product.name)
                predicted_daily = avg_daily_sales * seasonal_boost

                if predicted_daily > 0:
                    days_until_stockout = product.stock / predicted_daily
                else:
                    days_until_stockout = 999

                if days_until_stockout <= 3:
                    urgency = "critical"
                elif days_until_stockout <= 7:
                    urgency = "high"
                elif days_until_stockout <= 14:
                    urgency = "medium"
                else:
                    urgency = "low"

                restock_qty = max(0, int(predicted_daily * 30) - product.stock)

                forecasts.append({
                    "product_id": pid,
                    "product_name": product.name,
                    "current_stock": product.stock,
                    "avg_daily_sales": round(avg_daily_sales, 2),
                    "predicted_daily_demand": round(predicted_daily, 2),
                    "seasonal_boost": round(seasonal_boost, 2),
                    "days_until_stockout": round(days_until_stockout, 1) if days_until_stockout < 999 else None,
                    "urgency": urgency,
                    "recommended_restock_qty": restock_qty,
                    "active_seasons": _current_season(),
                })

            # Sort by urgency
            urgency_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
            forecasts.sort(key=lambda x: urgency_order.get(x["urgency"], 4))

            critical = [f for f in forecasts if f["urgency"] == "critical"]
            high = [f for f in forecasts if f["urgency"] == "high"]

            return {
                "business_id": business_id,
                "forecast_period_days": 90,
                "active_seasons": _current_season(),
                "total_products_analysed": len(forecasts),
                "critical_restock_needed": len(critical),
                "high_priority_restock": len(high),
                "forecasts": forecasts,
                "summary": _generate_summary(forecasts),
            }

        except Exception as exc:
            logger.exception("demand_forecast_error business=%s", business_id)
            return {"error": str(exc), "forecasts": []}

    def _generate_summary(self, forecasts: list) -> str:
        return _generate_summary(forecasts)


def _generate_summary(forecasts: list) -> str:
    critical = [f for f in forecasts if f["urgency"] == "critical"]
    high = [f for f in forecasts if f["urgency"] == "high"]
    seasons = _current_season()

    parts = []
    if critical:
        names = ", ".join(f["product_name"] for f in critical[:3])
        parts.append(f"{len(critical)} product(s) critically low: {names}")
    if high:
        parts.append(f"{len(high)} product(s) need restocking within a week")
    if seasons:
        parts.append(f"Active seasons: {', '.join(seasons)} — expect higher demand on seasonal items")
    if not parts:
        parts.append("All products have healthy stock levels")

    return ". ".join(parts) + "."
