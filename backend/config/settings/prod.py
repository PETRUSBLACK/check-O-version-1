"""
Production settings for Check-O.
Extends base.py with secure production overrides.

All secrets must come from environment variables - never hardcoded here.

Required env vars:
    SECRET_KEY           - long random string
    DATABASE_URL         - postgres://user:pass@host:5432/db  (Railway sets automatically)
    REDIS_URL            - redis://host:6379/0  (Railway sets automatically)
    ALLOWED_HOSTS        - comma-separated domains; Railway domain included automatically
    CORS_ALLOWED_ORIGINS - comma-separated list of allowed frontend origins
    DEFAULT_FROM_EMAIL   - sender address for transactional emails
    EMAIL_HOST           - SMTP host
    EMAIL_HOST_USER      - SMTP user
    EMAIL_HOST_PASSWORD  - SMTP password
    FRONTEND_ORIGIN      - base URL of the React Native / web frontend
"""

import os

from .base import *  # noqa: F401, F403

# --- Core ---

DEBUG = False

SECRET_KEY = os.environ["SECRET_KEY"]  # Hard fail if missing

# Railway auto-injects RAILWAY_PUBLIC_DOMAIN (e.g. checko.up.railway.app).
# Without it Django rejects every request with 400 Bad Request.
_railway_domain = os.environ.get("RAILWAY_PUBLIC_DOMAIN", "")
ALLOWED_HOSTS = [
    h.strip()
    for h in os.environ.get("ALLOWED_HOSTS", "").split(",")
    if h.strip()
] + ([_railway_domain] if _railway_domain else [])

# --- Security headers ---

# Railway terminates SSL at their proxy and forwards plain HTTP internally.
# SECURE_SSL_REDIRECT=True causes an infinite redirect loop on Railway.
SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 31_536_000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
# Tells Django the original request from the client was HTTPS.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
X_FRAME_OPTIONS = "DENY"

# --- Static files (WhiteNoise) ---

# DEBUG=False disables Django's dev static server. WhiteNoise serves static
# files directly from Daphne without needing a separate nginx/CDN layer.
# Must be inserted directly after SecurityMiddleware.
MIDDLEWARE = [  # noqa: F405
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    *MIDDLEWARE[1:],  # noqa: F405
]
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
STATIC_ROOT = BASE_DIR / "staticfiles"  # noqa: F405

# --- Branding ---

SPECTACULAR_SETTINGS = {  # noqa: F405
    **SPECTACULAR_SETTINGS,  # noqa: F405
    "TITLE": "Check-O API",
}

JAZZMIN_SETTINGS = {  # noqa: F405
    **JAZZMIN_SETTINGS,  # noqa: F405
    "site_title": "Check-O Admin",
    "site_header": "Check-O",
    "site_brand": "Check-O Platform",
    "welcome_sign": "Welcome to Check-O administration",
    "copyright": "Check-O",
}

# --- Database ---
# Inherited from base.py via dj_database_url + DATABASE_URL env var

# --- Email ---

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.environ.get("EMAIL_HOST", "smtp.mailgun.org")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", 587))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")

# --- CORS ---
# Inherited from base.py - reads CORS_ALLOWED_ORIGINS env var

CORS_ALLOW_ALL_ORIGINS = False

# --- Throttling ---

REST_FRAMEWORK = {
    **REST_FRAMEWORK,  # noqa: F405
    "DEFAULT_THROTTLE_RATES": {
        "auth_register": "10/minute",
        "auth_token": "30/minute",
        "auth_password_reset": "5/minute",
        "payment_webhook": "60/minute",
    },
}

# --- Logging ---

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "format": '{"time": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s"}',
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django.security": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
        "django.db.backends": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
    },
}
