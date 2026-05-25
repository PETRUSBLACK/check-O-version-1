"""
Production settings for SmartMall.
Extends base.py with secure production overrides.

All secrets must come from environment variables — never hardcoded here.

Required env vars:
    SECRET_KEY          — long random string
    DATABASE_URL        — postgres://user:pass@host:5432/db
    REDIS_URL           — redis://host:6379/0
    ALLOWED_HOSTS       — comma-separated list of domains
    CORS_ALLOWED_ORIGINS — comma-separated list of allowed frontend origins
    DEFAULT_FROM_EMAIL  — sender address for transactional emails
    EMAIL_HOST          — SMTP host
    EMAIL_HOST_USER     — SMTP user
    EMAIL_HOST_PASSWORD — SMTP password
    FRONTEND_ORIGIN     — base URL of the React Native / web frontend
"""

import os

from .base import *  # noqa: F401, F403

# ─── Core ─────────────────────────────────────────────────────────────────────

DEBUG = False

SECRET_KEY = os.environ["SECRET_KEY"]  # Hard fail if missing

ALLOWED_HOSTS = [
    h.strip()
    for h in os.environ.get("ALLOWED_HOSTS", "").split(",")
    if h.strip()
]

# ─── Security headers ─────────────────────────────────────────────────────────

SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31_536_000          # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
X_FRAME_OPTIONS = "DENY"

# ─── Database ─────────────────────────────────────────────────────────────────
# Inherited from base.py via dj_database_url + DATABASE_URL env var

# ─── Static files ─────────────────────────────────────────────────────────────

STATIC_ROOT = BASE_DIR / "staticfiles"  # noqa: F405

# ─── Email ────────────────────────────────────────────────────────────────────

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.environ.get("EMAIL_HOST", "smtp.mailgun.org")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", 587))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")

# ─── CORS ─────────────────────────────────────────────────────────────────────
# Inherited from base.py — reads CORS_ALLOWED_ORIGINS env var

CORS_ALLOW_ALL_ORIGINS = False

# ─── Throttling ───────────────────────────────────────────────────────────────

REST_FRAMEWORK = {
    **REST_FRAMEWORK,  # noqa: F405
    "DEFAULT_THROTTLE_RATES": {
        "auth_register": "10/minute",
        "auth_token": "30/minute",
        "auth_password_reset": "5/minute",
        "payment_webhook": "60/minute",
    },
}

# ─── Logging ──────────────────────────────────────────────────────────────────

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