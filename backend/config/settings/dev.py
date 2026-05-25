"""
Development settings for SmartMall.
Extends base.py with dev-friendly overrides.

Usage:
    export DJANGO_SETTINGS_MODULE=config.settings.dev
    python manage.py runserver
"""

from .base import *  # noqa: F401, F403

# ─── Core ─────────────────────────────────────────────────────────────────────

DEBUG = True

SECRET_KEY = "unsafe-dev-secret-key-do-not-use-in-production"

ALLOWED_HOSTS = ["*"]

# ─── Email ────────────────────────────────────────────────────────────────────

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# ─── CORS ─────────────────────────────────────────────────────────────────────

CORS_ALLOW_ALL_ORIGINS = True

# ─── Throttling ───────────────────────────────────────────────────────────────

REST_FRAMEWORK = {
    **REST_FRAMEWORK,  # noqa: F405
    "DEFAULT_THROTTLE_RATES": {
        "auth_register": "1000/minute",
        "auth_token": "1000/minute",
        "auth_password_reset": "1000/minute",
        "payment_webhook": "1000/minute",
    },
}

# ─── Logging ──────────────────────────────────────────────────────────────────

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "dev": {
            "format": "[{levelname}] {name}: {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "dev",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "DEBUG",
    },
    "loggers": {
        "django.db.backends": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}