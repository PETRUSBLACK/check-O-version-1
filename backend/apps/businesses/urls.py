"""
Business application routes.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.businesses.views import BusinessViewSet

app_name = "businesses"

router = DefaultRouter()

router.register(
    r"businesses",
    BusinessViewSet,
    basename="business",
)

urlpatterns = [
    path("", include(router.urls)),
]