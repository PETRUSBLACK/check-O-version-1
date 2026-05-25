import logging

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from drf_spectacular.utils import extend_schema

from core.auth_throttles import (
    AuthPasswordResetThrottle,
    AuthRegisterThrottle,
    AuthTokenThrottle,
)

from .models import User, UserRole
from .serializers import UserSerializer

logger = logging.getLogger(__name__)


class VendorBusinessPayloadSerializer(serializers.Serializer):
    """Optional: create draft business profile during vendor registration."""

    name = serializers.CharField(max_length=255)
    slug = serializers.SlugField(max_length=255)
    legal_name = serializers.CharField(max_length=255)
    registration_number = serializers.CharField(max_length=128)
    tax_identifier = serializers.CharField(
        max_length=64, required=False, allow_blank=True, default=""
    )
    business_phone = serializers.CharField(
        max_length=32, required=False, allow_blank=True, default=""
    )
    address = serializers.CharField()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    role = serializers.ChoiceField(
        choices=[UserRole.CUSTOMER, UserRole.VENDOR],
        required=False,
        default=UserRole.CUSTOMER,
    )
    vendor_business = VendorBusinessPayloadSerializer(
        write_only=True, required=False, allow_null=True
    )

    class Meta:
        model = User
        fields = (
            "email",
            "password",
            "first_name",
            "last_name",
            "role",
            "vendor_business",
        )

    def validate_password(self, value):
        validate_password(value)
        return value

    def validate(self, attrs):
        role = attrs.get("role", UserRole.CUSTOMER)
        vb = attrs.get("vendor_business")
        if vb and role != UserRole.VENDOR:
            raise serializers.ValidationError(
                {"vendor_business": "Only vendors can submit business details at signup."}
            )
        return attrs

    def create(self, validated_data):
        from apps.businesses.services.registration import register_business

        vendor_payload = validated_data.pop("vendor_business", None)
        password = validated_data.pop("password")
        user = User.objects.create_user(password=password, **validated_data)
        if user.role == UserRole.VENDOR and vendor_payload:
            register_business(
                owner=user,
                name=vendor_payload["name"],
                slug=vendor_payload["slug"],
                legal_name=vendor_payload["legal_name"],
                registration_number=vendor_payload["registration_number"],
                tax_identifier=vendor_payload.get("tax_identifier") or "",
                business_phone=vendor_payload.get("business_phone") or "",
                address=vendor_payload["address"],
            )
        return user


class PasswordChangeSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate_new_password(self, value):
        validate_password(value)
        return value


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(min_length=8, write_only=True)

    def validate_new_password(self, value):
        validate_password(value)
        return value


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField(help_text="Refresh token to blacklist.")


class RegisterView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthRegisterThrottle]

    @extend_schema(
        request=RegisterSerializer,
        responses={201: UserSerializer},
        tags=["auth"],
        summary="Register customer or vendor account",
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: UserSerializer},
        tags=["auth"],
        summary="Get current authenticated user",
    )
    def get(self, request):
        return Response(UserSerializer(request.user).data)


class PasswordChangeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=PasswordChangeSerializer,
        tags=["auth"],
        summary="Change password (authenticated)",
    )
    def post(self, request):
        ser = PasswordChangeSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        user = request.user
        if not user.check_password(ser.validated_data["old_password"]):
            return Response(
                {"detail": "Old password is incorrect."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.set_password(ser.validated_data["new_password"])
        user.save(update_fields=["password"])
        return Response({"detail": "Password updated."})


class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthPasswordResetThrottle]

    @extend_schema(
        request=PasswordResetRequestSerializer,
        tags=["auth"],
        summary="Request password reset (email with uid + token)",
        description=(
            "Always returns the same success message if the account exists or not. "
            "In development, reset link may be logged to the console via EMAIL_BACKEND."
        ),
    )
    def post(self, request):
        ser = PasswordResetRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        email = ser.validated_data["email"].strip().lower()
        user = User.objects.filter(email__iexact=email).first()
        detail = {
            "detail": "If an account exists for that email, reset instructions were sent."
        }
        if not user:
            return Response(detail, status=status.HTTP_200_OK)

        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        reset_path = getattr(
            settings,
            "PASSWORD_RESET_FRONTEND_PATH",
            "/reset-password",
        )
        base = getattr(settings, "FRONTEND_ORIGIN", "http://localhost:3000").rstrip("/")
        link = f"{base}{reset_path}?uid={uid}&token={token}"

        subject = "SmartMall password reset"
        body = (
            f"You requested a password reset.\n\n"
            f"Use this link (or copy uid/token into the API confirm endpoint):\n{link}\n\n"
            f"uid: {uid}\ntoken: {token}\n"
        )
        try:
            send_mail(
                subject,
                body,
                getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@smartmall.local"),
                [user.email],
                fail_silently=False,
            )
        except Exception:
            logger.exception("password_reset_email_failed uid=%s", uid)
            if settings.DEBUG:
                logger.info("DEV password reset link:\n%s", body)

        return Response(detail, status=status.HTTP_200_OK)


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthPasswordResetThrottle]

    @extend_schema(
        request=PasswordResetConfirmSerializer,
        tags=["auth"],
        summary="Confirm password reset with uid + token",
    )
    def post(self, request):
        ser = PasswordResetConfirmSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        uid_b64 = ser.validated_data["uid"]
        raw_token = ser.validated_data["token"]
        new_password = ser.validated_data["new_password"]

        try:
            uid = force_str(urlsafe_base64_decode(uid_b64))
            user = User.objects.get(pk=uid)
        except (User.DoesNotExist, ValueError, TypeError, OverflowError):
            return Response(
                {"detail": "Invalid uid."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not default_token_generator.check_token(user, raw_token):
            return Response(
                {"detail": "Invalid or expired token."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(new_password)
        user.save(update_fields=["password"])
        return Response({"detail": "Password has been reset."})


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=LogoutSerializer,
        tags=["auth"],
        summary="Logout (blacklist refresh token)",
    )
    def post(self, request):
        ser = LogoutSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            token = RefreshToken(ser.validated_data["refresh"])
            token.blacklist()
        except TokenError:
            return Response(
                {"detail": "Invalid refresh token."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_205_RESET_CONTENT)


class ThrottledTokenObtainPairView(TokenObtainPairView):
    throttle_classes = [AuthTokenThrottle]


class ThrottledTokenRefreshView(TokenRefreshView):
    throttle_classes = [AuthTokenThrottle]
