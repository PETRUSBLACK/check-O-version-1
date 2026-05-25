"""Rate limits for unauthenticated auth endpoints (registration, login, password reset)."""

from rest_framework.throttling import AnonRateThrottle


class AuthRegisterThrottle(AnonRateThrottle):
    scope = "auth_register"


class AuthTokenThrottle(AnonRateThrottle):
    scope = "auth_token"


class AuthPasswordResetThrottle(AnonRateThrottle):
    scope = "auth_password_reset"
