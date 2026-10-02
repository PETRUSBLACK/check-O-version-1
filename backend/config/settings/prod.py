"""
Production settings for Check-O.
Extends base.py with secure production overrides.

All secrets must come from environment variables - never hardcoded here.

Required:
    SECRET_KEY           - long random string
    DATABASE_URL         - postgres://...  (Neon, or whatever the host provides)
    PAYSTACK_SECRET_KEY  - from the Paystack dashboard

Strongly recommended:
    CLOUDINARY_URL       - cloudinary://key:secret@cloud_name
                           Without it, product photos are written to the
                           container's own disk, which free hosts wipe on every
                           deploy. A vendor's photos would vanish silently.
    TASK_RUNNER_TOKEN    - long random string; the secret a cron service presents
                           to POST /api/internal/run-tasks/. Without it, unpaid
                           orders are never cancelled and stock stays held.

Optional:
    ALLOWED_HOSTS        - comma-separated extra domains. The host's own domain is
                           picked up automatically (Render and Railway both).
    REDIS_URL            - only needed to run more than one web process; without
                           it WebSocket notifications work within one process,
                           which is all a free tier gives you anyway.
    CORS_ALLOWED_ORIGINS - comma-separated allowed browser origins
    FRONTEND_ORIGIN      - base URL of the web front end, if there ever is one
    DEFAULT_FROM_EMAIL / EMAIL_HOST / EMAIL_HOST_USER / EMAIL_HOST_PASSWORD
"""

import logging
import os

from .base import *  # noqa: F401, F403

# --- Core ---

DEBUG = False

SECRET_KEY = os.environ["SECRET_KEY"]  # Hard fail if missing

# Hosts inject their own public domain under their own name, and Django answers
# 400 Bad Request to every request for a domain not listed here — which looks
# exactly like the app being broken. Pick up whichever one is present rather than
# making Petrus remember to paste a domain he has only just been given.
_host_domains = [
    os.environ.get("RENDER_EXTERNAL_HOSTNAME", ""),   # Render
    os.environ.get("RAILWAY_PUBLIC_DOMAIN", ""),      # Railway
    os.environ.get("FLY_APP_NAME", "") and f"{os.environ['FLY_APP_NAME']}.fly.dev",
]
ALLOWED_HOSTS = (
    [h.strip() for h in os.environ.get("ALLOWED_HOSTS", "").split(",") if h.strip()]
    + [d for d in _host_domains if d]
    + ["healthcheck.railway.app"]
)

# Django's CSRF check compares the Origin header against this list, and behind a
# TLS-terminating proxy it will not accept a bare hostname. Without these, the
# admin login page accepts the password and then refuses the form.
CSRF_TRUSTED_ORIGINS = [
    f"https://{d}" for d in _host_domains if d
] + [
    o.strip()
    for o in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",")
    if o.strip()
]

# --- Security headers ---

# Render and Railway both terminate TLS at their proxy and forward plain HTTP
# internally. SECURE_SSL_REDIRECT=True then sees "http" on every request and
# redirects forever.
SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 31_536_000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
# Tells Django the original request from the client was HTTPS.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
X_FRAME_OPTIONS = "DENY"

# --- Files: static, and the photos vendors upload ---

# DEBUG=False disables Django's dev static server. WhiteNoise serves static
# files directly from Daphne without needing a separate nginx/CDN layer.
# Must be inserted directly after SecurityMiddleware.
MIDDLEWARE = [  # noqa: F405
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    *MIDDLEWARE[1:],  # noqa: F405
]
STATIC_ROOT = BASE_DIR / "staticfiles"  # noqa: F405

# Product photos cannot live on the server's own disk. A free host rebuilds the
# container on every deploy and throws the old filesystem away, so a vendor's
# photos would disappear the next time Petrus pushed a change — silently, with
# the database still holding paths to files that no longer exist.
#
# CLOUDINARY_URL carries the cloud name, key and secret in one value:
#     cloudinary://<api_key>:<api_secret>@<cloud_name>
_cloudinary_url = os.environ.get("CLOUDINARY_URL", "")

if _cloudinary_url:
    # Media only, so WhiteNoise keeps serving static files. The library is strict
    # about this order.
    INSTALLED_APPS = [  # noqa: F405
        *INSTALLED_APPS,  # noqa: F405
        "cloudinary_storage",
        "cloudinary",
    ]
    _media_backend = "cloudinary_storage.storage.MediaCloudinaryStorage"
else:
    _media_backend = "django.core.files.storage.FileSystemStorage"
    logging.getLogger(__name__).warning(
        "CLOUDINARY_URL is not set. Product photos will be written to this "
        "container's disk and will be lost on the next deploy."
    )

# Django 5.1 removed STATICFILES_STORAGE and DEFAULT_FILE_STORAGE outright. This
# file still set STATICFILES_STORAGE, which Django 5.2 simply ignores — so
# WhiteNoise has been serving uncompressed, unhashed static files all along.
STORAGES = {
    "default": {"BACKEND": _media_backend},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

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

# --- Background tasks ---
#
# On a free host there is no second worker service to run the scheduler, so an
# external cron calls POST /api/internal/run-tasks/ every 5 minutes instead. That
# both runs the tasks and keeps the web service from falling asleep, which on a
# free tier otherwise means a one-minute wait for the first customer of the day.
#
# TASK_RUNNER_TOKEN is read in base.py. Unset, the endpoint refuses everything.
if not TASK_RUNNER_TOKEN:  # noqa: F405
    logging.getLogger(__name__).warning(
        "TASK_RUNNER_TOKEN is not set. Nothing will cancel unpaid orders, so "
        "abandoned payments will hold vendors' stock indefinitely."
    )

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
