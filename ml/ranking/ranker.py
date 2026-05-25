"""
Smart Search Ranking.

Ranks search results using multiple signals:
- Text relevance (name match quality)
- Distance from customer (closer = higher rank)
- Shop rating (higher rated = higher rank)
- Stock availability (in-stock = higher rank)
- Promotion boost weight (featured products get a boost)
- Historical CTR from ad impressions/clicks

This gives customers the most relevant, trustworthy, nearby results first.
"""

import logging
from math import asin, cos, radians, sin, sqrt

logger = logging.getLogger(__name__)


def _haversine_km(lat1, lon1, lat2, lon2) -> float:
    R = 6371
    lat1, lon1, lat2, lon2 = map(radians, [float(lat1), float(lon1), float(lat2), float(lon2)])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return R * 2 * asin(sqrt(a))


class SearchRanker:
    """
    ML-inspired search ranker that scores products on multiple signals.
    No external ML library needed — uses weighted scoring.
    """

    WEIGHTS = {
        "relevance": 0.35,
        "rating": 0.25,
        "distance": 0.20,
        "stock": 0.10,
        "promotion": 0.10,
    }

    def rank(self, query: str, lat: float = None, lng: float = None, limit: int = 10) -> dict:
        """
        Search and rank products using multi-signal scoring.
        Returns results ordered from most to least relevant.
        """
        try:
            from apps.products.models import Product
            from apps.businesses.models import BusinessStatus
            from apps.ads.models import ProductPromotion
            from django.db.models import Q
            from django.utils import timezone

            if not query:
                return {"results": [], "query": query}

            # Fetch candidate products
            qs = Product.objects.filter(
                Q(name__icontains=query) | Q(description__icontains=query),
                is_active=True,
                business__status=BusinessStatus.APPROVED,
            ).select_related("business__location", "business__ratings")

            # Get active promotions for boost scores
            active_promos = {
                str(p.product_id): p
                for p in ProductPromotion.objects.filter(
                    is_active=True,
                    starts_at__lte=timezone.now(),
                    ends_at__gte=timezone.now(),
                ).select_related("product")
            }

            scored = []
            for product in qs[:200]:
                score = self._score(
                    product=product,
                    query=query,
                    lat=lat,
                    lng=lng,
                    promo=active_promos.get(str(product.pk)),
                )
                scored.append((score, product, active_promos.get(str(product.pk))))

            scored.sort(key=lambda x: x[0], reverse=True)

            results = []
            for score, product, promo in scored[:limit]:
                ratings = product.business.ratings.all()
                avg_rating = round(sum(r.score for r in ratings) / len(ratings), 1) if ratings else None

                distance = None
                if lat and lng and hasattr(product.business, "location") and product.business.location:
                    loc = product.business.location
                    distance = round(_haversine_km(lat, lng, loc.latitude, loc.longitude), 2)

                results.append({
                    "product_id": str(product.pk),
                    "name": product.name,
                    "price": float(product.price),
                    "discounted_price": float(promo.discounted_price) if promo and promo.discount_percent > 0 else None,
                    "stock": product.stock,
                    "in_stock": product.stock > 0,
                    "shop_name": product.business.name,
                    "shop_id": str(product.business.pk),
                    "avg_rating": avg_rating,
                    "distance_km": distance,
                    "relevance_score": round(score, 3),
                    "is_featured": promo is not None and promo.promotion_type == "featured",
                })

            return {
                "results": results,
                "query": query,
                "total_found": len(scored),
            }

        except Exception as exc:
            logger.exception("search_ranker_error query=%s", query)
            return {"results": [], "query": query, "error": str(exc)}

    def _score(self, product, query: str, lat: float, lng: float, promo) -> float:
        """Calculate composite relevance score for a product."""
        score = 0.0

        # 1. Relevance score (0-1)
        relevance = self._relevance_score(product, query)
        score += relevance * self.WEIGHTS["relevance"]

        # 2. Rating score (0-1)
        ratings = product.business.ratings.all()
        if ratings:
            avg = sum(r.score for r in ratings) / len(ratings)
            score += (avg / 5.0) * self.WEIGHTS["rating"]
        else:
            score += 0.3 * self.WEIGHTS["rating"]  # Neutral for unrated

        # 3. Distance score (0-1, closer = higher)
        if lat and lng and hasattr(product.business, "location") and product.business.location:
            loc = product.business.location
            dist = _haversine_km(lat, lng, loc.latitude, loc.longitude)
            dist_score = max(0, 1 - (dist / 50))  # 50km = 0 score
            score += dist_score * self.WEIGHTS["distance"]

        # 4. Stock score (0-1)
        if product.stock > 10:
            stock_score = 1.0
        elif product.stock > 0:
            stock_score = 0.5
        else:
            stock_score = 0.0
        score += stock_score * self.WEIGHTS["stock"]

        # 5. Promotion boost (0-1)
        if promo:
            boost = min(1.0, promo.boost_weight / 10.0)
            ctr = promo.ctr / 100 if promo.ctr else 0
            promo_score = (boost * 0.7) + (ctr * 0.3)
            score += promo_score * self.WEIGHTS["promotion"]

        return score

    def _relevance_score(self, product, query: str) -> float:
        """Score relevance of product to query."""
        query_lower = query.lower().strip()
        name_lower = product.name.lower()
        desc_lower = (product.description or "").lower()

        # Exact name match
        if query_lower == name_lower:
            return 1.0

        # Name starts with query
        if name_lower.startswith(query_lower):
            return 0.9

        # Name contains full query
        if query_lower in name_lower:
            return 0.8

        # All query words in name
        query_words = query_lower.split()
        name_words = set(name_lower.split())
        if all(w in name_words for w in query_words):
            return 0.7

        # Some query words in name
        match_count = sum(1 for w in query_words if w in name_lower)
        if match_count > 0:
            return 0.4 + (0.2 * match_count / len(query_words))

        # Query in description
        if query_lower in desc_lower:
            return 0.3

        return 0.1
