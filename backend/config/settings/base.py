import os
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("SECRET_KEY", "unsafe-dev-key")
DEBUG = os.environ.get("DEBUG", "1") == "1"
ALLOWED_HOSTS = [
    h.strip()
    for h in os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if h.strip()
]

# Allow Railway deployment domains automatically
ALLOWED_HOSTS += [".railway.app", ".up.railway.app"]
RAILWAY_PUBLIC_DOMAIN = os.environ.get("RAILWAY_PUBLIC_DOMAIN", "")
if RAILWAY_PUBLIC_DOMAIN:
    ALLOWED_HOSTS.append(RAILWAY_PUBLIC_DOMAIN)

INSTALLED_APPS = [
    "jazzmin",
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "django_filters",
    "corsheaders",
    "channels",
    "drf_spectacular",
    "drf_spectacular_sidecar",
    "rest_framework_simplejwt.token_blacklist",
    "core",
    "apps.users",
    "apps.businesses",
    "apps.products",
    "apps.orders",
    "apps.payments",
    "apps.delivery",
    "apps.notifications",
    "apps.subscriptions",
    "apps.ads",
    "apps.analytics",
    "apps.ai_assistant",
    "apps.cart",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "core.middleware.RequestIdMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": dj_database_url.config(
        default=os.environ.get(
            "DATABASE_URL",
            f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        ),
        conn_max_age=600,
    ),
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# STATIC_URL = "static/"
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "users.User"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "EXCEPTION_HANDLER": "core.exceptions.custom_exception_handler",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_RATES": {
        "auth_register": "10/minute",
        "auth_token": "30/minute",
        "auth_password_reset": "5/minute",
    },
}

SIMPLE_JWT = {
    "AUTH_HEADER_TYPES": ("Bearer",),
    "BLACKLIST_AFTER_ROTATION": True,
    "ROTATE_REFRESH_TOKENS": True,
}

SPECTACULAR_SETTINGS = {
    "TITLE": "SmartMall API",
    "DESCRIPTION": """
## SmartMall — Location-Aware Multi-Vendor Marketplace

SmartMall enables customers to search for products, find nearby shops with prices and ratings,
order online, and track delivery in real time.

### Authentication
All protected endpoints require a **Bearer JWT token**.

1. Register: `POST /api/auth/register/`
2. Login: `POST /api/auth/token/` — returns `access` and `refresh` tokens
3. Pass the access token in the header: `Authorization: Bearer <access_token>`
4. Refresh: `POST /api/auth/token/refresh/`

### User Roles
| Role | Description |
|---|---|
| `customer` | Can browse, add to cart, checkout, pay, track orders |
| `vendor` | Can register a business, list products, manage orders and shipments |
| `admin` | Full platform access — approve businesses, manage all data |

### Commerce Flow
```
Customer → Cart → Checkout → Order → Payment → Delivery/Pickup → Completed
```

### WebSocket
Real-time notifications via WebSocket:
```
ws://<host>/ws/notifications/
```
Events: `order.placed`, `payment.confirmed`, `order.status_changed`,
`shipment.updated`, `order.pickup_reminder`, `order.pickup_expired`
""",
    "VERSION": "3.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SWAGGER_UI_DIST": "SIDECAR",
    "SWAGGER_UI_FAVICON_HREF": "SIDECAR",
    "REDOC_DIST": "SIDECAR",
    "COMPONENT_SPLIT_REQUEST": True,
    "SECURITY": [{"BearerAuth": []}],
    "COMPONENTS": {
        "securitySchemes": {
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
                "description": "Enter JWT access token from POST /api/auth/token/",
            }
        }
    },
    "SORT_OPERATIONS": False,
    "TAGS": [
        {"name": "system", "description": "Health check and platform status"},
        {"name": "auth", "description": "Registration, login, JWT tokens, password management"},
        {"name": "users", "description": "User profile management"},
        {"name": "businesses", "description": "Vendor business registration, verification, location, ratings"},
        {"name": "products", "description": "Product catalog management"},
        {"name": "cart", "description": "Shopping cart and checkout"},
        {"name": "orders", "description": "Order lifecycle, status transitions, pickup flow"},
        {"name": "payments", "description": "Payment initiation, confirmation, and gateway webhooks"},
        {"name": "delivery", "description": "Shipment management and delivery tracking"},
        {"name": "notifications", "description": "In-app notifications"},
        {"name": "subscriptions", "description": "Vendor subscription plans"},
        {"name": "ads", "description": "Product promotions and advertisements"},
        {"name": "analytics", "description": "Platform event tracking"},
    ],
    "SWAGGER_UI_SETTINGS": {
        "deepLinking": True,
        "persistAuthorization": True,
        "displayOperationId": False,
        "defaultModelsExpandDepth": 2,
        "defaultModelExpandDepth": 2,
        "docExpansion": "none",
        "filter": True,
        "tagsSorter": "alpha",
    },
}

JAZZMIN_SETTINGS = {
    "site_title": "SmartMall Admin",
    "site_header": "SmartMall",
    "site_brand": "SmartMall Platform",
    "welcome_sign": "Welcome to SmartMall administration",
    "copyright": "SmartMall",
    "show_sidebar": True,
    "navigation_expanded": True,
    "search_model": ["users.User", "businesses.Business", "orders.Order", "payments.Payment"],
    "topmenu_links": [
        {"name": "API Docs", "url": "swagger-ui", "permissions": ["auth.view_user"]},
        {"name": "ReDoc", "url": "redoc", "permissions": ["auth.view_user"]},
    ],
    "icons": {
        "auth": "fas fa-users-cog",
        "users.User": "fas fa-user",
        "businesses.Business": "fas fa-store",
        "products.Product": "fas fa-box-open",
        "orders.Order": "fas fa-shopping-cart",
        "orders.OrderItem": "fas fa-list",
        "payments.Payment": "fas fa-credit-card",
        "delivery.Shipment": "fas fa-truck",
        "notifications.Notification": "fas fa-bell",
        "subscriptions.SubscriptionPlan": "fas fa-layer-group",
        "subscriptions.VendorSubscription": "fas fa-star",
        "ads.ProductPromotion": "fas fa-bullhorn",
        "analytics.AnalyticsEvent": "fas fa-chart-line",
    },
    "order_with_respect_to": [
        "users",
        "businesses",
        "products",
        "orders",
        "payments",
        "delivery",
        "notifications",
        "subscriptions",
        "ads",
        "analytics",
    ],
    "changeform_format": "horizontal_tabs",
}

CORS_ALLOWED_ORIGINS = [
    o.strip()
    for o in os.environ.get(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:8081,http://127.0.0.1:8081",
    ).split(",")
    if o.strip()
]

_redis_url = os.environ.get("REDIS_URL")
if _redis_url:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {"hosts": [_redis_url]},
        },
    }
else:
    CHANNEL_LAYERS = {
        "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"},
    }

# Email (password reset). Override in production.
EMAIL_BACKEND = os.environ.get(
    "EMAIL_BACKEND",
    "django.core.mail.backends.console.EmailBackend",
)
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "noreply@smartmall.local")
FRONTEND_ORIGIN = os.environ.get("FRONTEND_ORIGIN", "http://localhost:3000")
PASSWORD_RESET_FRONTEND_PATH = os.environ.get(
    "PASSWORD_RESET_FRONTEND_PATH",
    "/reset-password",
)

# Payment Gateways
PAYSTACK_SECRET_KEY = os.environ.get("PAYSTACK_SECRET_KEY", "")
FLUTTERWAVE_SECRET_KEY = os.environ.get("FLUTTERWAVE_SECRET_KEY", "")
FLUTTERWAVE_WEBHOOK_SECRET = os.environ.get("FLUTTERWAVE_WEBHOOK_SECRET", "")
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")

# AI Assistant
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# CSRF trusted origins — required for Railway and production domains
CSRF_TRUSTED_ORIGINS = [
    "https://*.railway.app",
    "https://*.up.railway.app",
] + [
    f"https://{h}" for h in os.environ.get("ALLOWED_HOSTS", "").split(",") if h.strip()
]
