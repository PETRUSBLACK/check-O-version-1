import logging

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.users.models import User, UserRole
from apps.users.serializers import UserSerializer
from core.utils import AuthPasswordResetThrottle, AuthRegisterThrottle, AuthTokenThrottle

logger = logging.getLogger(__name__)


class VendorBusinessPayloadSerializer(serializers.Serializer):
    """
    Shop details a vendor may send along with sign-up. Optional — the app signs
    the person up first and sets the shop up on its own screen afterwards, which
    is how it can ask for GPS and a photo.

    Only the name is required. A market trader in Asaba has no CAC certificate
    and no tax number, and demanding one at the door would end Check-O's vendor
    list at about three shops. `slug` is built from the name when left out.
    """

    name = serializers.CharField(max_length=255)
    slug = serializers.SlugField(max_length=255, required=False, allow_blank=True, default="")
    category = serializers.CharField(max_length=50, required=False, allow_blank=True, default="")
    legal_name = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")
    registration_number = serializers.CharField(max_length=128, required=False, allow_blank=True, default="")
    business_phone = serializers.CharField(max_length=32, required=False, allow_blank=True, default="")
    address = serializers.CharField(required=False, allow_blank=True, default="")


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    role = serializers.ChoiceField(choices=[UserRole.CUSTOMER, UserRole.VENDOR], required=False, default=UserRole.CUSTOMER)
    vendor_business = VendorBusinessPayloadSerializer(write_only=True, required=False, allow_null=True)

    class Meta:
        model = User
        fields = ("email", "password", "first_name", "last_name", "role", "vendor_business")

    def validate_password(self, value):
        validate_password(value)
        return value

    def validate(self, attrs):
        role = attrs.get("role", UserRole.CUSTOMER)
        vb = attrs.get("vendor_business")
        if vb and role != UserRole.VENDOR:
            raise serializers.ValidationError({"vendor_business": "Only vendors can submit business details at signup."})
        return attrs

    def create(self, validated_data):
        from apps.businesses.services.registration import register_business
        vendor_payload = validated_data.pop("vendor_business", None)
        password = validated_data.pop("password")
        user = User.objects.create_user(password=password, **validated_data)
        if user.role == UserRole.VENDOR and vendor_payload:
            # No tax_identifier here: that field lives on BusinessVerification,
            # not on Business, and passing it raised TypeError on every vendor
            # sign-up that carried shop details.
            kwargs = {
                "owner": user,
                "name": vendor_payload["name"],
                "slug": vendor_payload.get("slug") or "",
                "legal_name": vendor_payload.get("legal_name") or "",
                "registration_number": vendor_payload.get("registration_number") or "",
                "business_phone": vendor_payload.get("business_phone") or "",
                "address": vendor_payload.get("address") or "",
            }
            if vendor_payload.get("category"):
                kwargs["category"] = vendor_payload["category"]
            register_business(**kwargs)
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

    @extend_schema(request=RegisterSerializer, responses={201: UserSerializer}, tags=["auth"], summary="Register customer or vendor account")
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: UserSerializer}, tags=["auth"], summary="Get current authenticated user")
    def get(self, request):
        return Response(UserSerializer(request.user).data)


class PasswordChangeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=PasswordChangeSerializer, tags=["auth"], summary="Change password (authenticated)")
    def post(self, request):
        ser = PasswordChangeSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        user = request.user
        if not user.check_password(ser.validated_data["old_password"]):
            return Response({"detail": "Old password is incorrect."}, status=status.HTTP_400_BAD_REQUEST)
        user.set_password(ser.validated_data["new_password"])
        user.save(update_fields=["password"])
        return Response({"detail": "Password updated."})


class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthPasswordResetThrottle]

    @extend_schema(request=PasswordResetRequestSerializer, tags=["auth"], summary="Request password reset")
    def post(self, request):
        ser = PasswordResetRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        email = ser.validated_data["email"].strip().lower()
        user = User.objects.filter(email__iexact=email).first()
        detail = {"detail": "If an account exists for that email, reset instructions were sent."}
        if not user:
            return Response(detail, status=status.HTTP_200_OK)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        reset_path = getattr(settings, "PASSWORD_RESET_FRONTEND_PATH", "/reset-password")
        base = getattr(settings, "FRONTEND_ORIGIN", "http://localhost:3000").rstrip("/")
        link = f"{base}{reset_path}?uid={uid}&token={token}"
        subject = "SmartMall password reset"
        body = f"You requested a password reset.\n\nUse this link:\n{link}\n\nuid: {uid}\ntoken: {token}\n"
        try:
            send_mail(subject, body, getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@smartmall.local"), [user.email], fail_silently=False)
        except Exception:
            logger.exception("password_reset_email_failed uid=%s", uid)
            if settings.DEBUG:
                logger.info("DEV password reset link:\n%s", body)
        return Response(detail, status=status.HTTP_200_OK)


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthPasswordResetThrottle]

    @extend_schema(request=PasswordResetConfirmSerializer, tags=["auth"], summary="Confirm password reset with uid + token")
    def post(self, request):
        ser = PasswordResetConfirmSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            uid = force_str(urlsafe_base64_decode(ser.validated_data["uid"]))
            user = User.objects.get(pk=uid)
        except (User.DoesNotExist, ValueError, TypeError, OverflowError):
            return Response({"detail": "Invalid uid."}, status=status.HTTP_400_BAD_REQUEST)
        if not default_token_generator.check_token(user, ser.validated_data["token"]):
            return Response({"detail": "Invalid or expired token."}, status=status.HTTP_400_BAD_REQUEST)
        user.set_password(ser.validated_data["new_password"])
        user.save(update_fields=["password"])
        return Response({"detail": "Password has been reset."})


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=LogoutSerializer, tags=["auth"], summary="Logout (blacklist refresh token)")
    def post(self, request):
        ser = LogoutSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            token = RefreshToken(ser.validated_data["refresh"])
            token.blacklist()
        except TokenError:
            return Response({"detail": "Invalid refresh token."}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_205_RESET_CONTENT)


class ThrottledTokenObtainPairView(TokenObtainPairView):
    throttle_classes = [AuthTokenThrottle]


class ThrottledTokenRefreshView(TokenRefreshView):
    throttle_classes = [AuthTokenThrottle]
