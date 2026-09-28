from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
    path("api/", include("config.api_urls")),
]

# Product photos are saved to MEDIA_ROOT, but Django does not serve files on its
# own — without this, an upload succeeds and then every photo is a 404. This is
# the development server only: static() returns nothing when DEBUG is off, and in
# production the photos belong on real file hosting (Cloudinary or S3), because a
# Railway container's disk is wiped on every deploy.
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
