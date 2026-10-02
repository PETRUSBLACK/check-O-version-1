import re
from decimal import Decimal

from django import forms
from django.contrib import admin, messages
from django.contrib.admin.helpers import ACTION_CHECKBOX_NAME
from django.db.models import Count, Q
from django.shortcuts import render

from .choices import BusinessStatus
from .services.registration import (
    BusinessFlowError,
    approve_business,
    missing_before_review,
    reject_business,
)

from .models import (
    Business,
    BusinessLocation,
    Branch,
    BusinessMember,
    BusinessHours,
    BusinessRating,
    BusinessGallery,
    RestaurantProfile,
    DeliveryZone,
    BusinessVerification,
    BusinessDocument,
)


# =========================================================
# Where a shop is
# =========================================================
#
# "Shops near you" works by measuring distance, so a shop has to have
# coordinates or it never appears in the app. Nobody should be typing them by
# hand, though: in the seller app the shop owner stands in their shop and taps
# "Use my location", and the phone fills these in. Until that exists, paste a
# Google Maps link or a "6.2003, 6.7331" pair into Coordinates below and the
# two fields fill themselves.

# Matches "6.2003, 6.7331" and the coordinates inside a Google Maps URL
# (.../@6.2003,6.7331,17z  or  ?q=6.2003,6.7331  or  !3d6.2003!4d6.7331).
_PAIR = re.compile(r"(-?\d{1,3}\.\d+)\s*,\s*(-?\d{1,3}\.\d+)")
_GOOGLE_3D4D = re.compile(r"!3d(-?\d{1,3}\.\d+)!4d(-?\d{1,3}\.\d+)")


def parse_coordinates(text: str):
    """Pull a latitude and longitude out of pasted text. None if there isn't one."""
    if not text:
        return None
    match = _GOOGLE_3D4D.search(text) or _PAIR.search(text)
    if not match:
        return None
    lat, lng = float(match.group(1)), float(match.group(2))
    if not (-90 <= lat <= 90 and -180 <= lng <= 180):
        return None
    return lat, lng


class BusinessLocationForm(forms.ModelForm):
    coordinates = forms.CharField(
        required=False,
        label="Coordinates",
        help_text=(
            "Paste a Google Maps link, or \"6.2003, 6.7331\". "
            "In Google Maps: right-click the shop, then click the numbers to copy them. "
            "Fills latitude and longitude below."
        ),
        widget=forms.TextInput(attrs={"size": 60}),
    )

    class Meta:
        model = BusinessLocation
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Either paste coordinates or type the numbers — don't demand both.
        self.fields["latitude"].required = False
        self.fields["longitude"].required = False

    def clean(self):
        cleaned = super().clean()
        pasted = parse_coordinates(cleaned.get("coordinates", ""))
        if pasted:
            # The model stores 7 decimal places — about a centimetre, far finer
            # than any phone's GPS — so trim rather than letting a long decimal
            # from a map URL fail validation.
            cleaned["latitude"] = Decimal(f"{pasted[0]:.7f}")
            cleaned["longitude"] = Decimal(f"{pasted[1]:.7f}")
            self.errors.pop("latitude", None)
            self.errors.pop("longitude", None)
        elif cleaned.get("coordinates"):
            raise forms.ValidationError(
                "Couldn't find coordinates in that. Paste a Google Maps link, "
                "or two numbers like 6.2003, 6.7331."
            )
        if cleaned.get("latitude") is None or cleaned.get("longitude") is None:
            raise forms.ValidationError(
                "This shop needs coordinates, or it won't show up in the app. "
                "Paste a Google Maps link into Coordinates."
            )
        return cleaned


class BusinessLocationInline(admin.StackedInline):
    """Edited on the shop's own page — a shop and where it is belong together."""
    model = BusinessLocation
    form = BusinessLocationForm
    can_delete = False
    extra = 1
    max_num = 1
    verbose_name_plural = "Where this shop is"
    fields = ("coordinates", "latitude", "longitude", "address", "city", "state", "country", "postal_code")


@admin.register(BusinessLocation)
class BusinessLocationAdmin(admin.ModelAdmin):
    form = BusinessLocationForm
    list_display = ("business", "address", "city", "state", "latitude", "longitude")
    search_fields = ("business__name", "address", "city")
    list_filter = ("state", "city")


# =========================================================
# Business
# =========================================================

class RejectionForm(forms.Form):
    """
    Rejecting without a reason is worse than not rejecting at all: the vendor is
    told no and has nothing to act on, so they either give up or submit exactly
    the same shop again. The reason is sent to them word for word.
    """

    reason = forms.CharField(
        label="What does this shop need to fix?",
        widget=forms.Textarea(attrs={"rows": 4, "style": "width: 36em"}),
        help_text="The vendor reads this exactly as you type it. Be specific.",
    )


@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    # Shops awaiting review come first — that is the whole reason to open this
    # page most days. After that, newest first.
    ordering = ("-created_at",)

    list_display = (
        "name",
        "category",
        "owner",
        "status",
        "ready_for_review",
        "is_active",
        "delivers",
        "delivery_fee",
        "vendor_cancellations",
        "created_at",
    )

    actions = ("approve_shops", "reject_shops")

    @admin.display(description="Still needs")
    def ready_for_review(self, obj):
        """
        For a shop that is not approved yet, what it is still missing. An empty
        cell on a pending shop means there is nothing stopping you approving it.
        """
        if obj.status == BusinessStatus.APPROVED:
            return "—"
        outstanding = missing_before_review(obj)
        if not outstanding:
            return "Nothing"
        return ", ".join(item.split(",")[0].lower() for item in outstanding)

    @admin.action(description="Approve selected shops (they go live)")
    def approve_shops(self, request, queryset):
        done, refused = 0, []
        for shop in queryset:
            try:
                approve_business(business_id=shop.pk)
                done += 1
            except BusinessFlowError as exc:
                refused.append(f"{shop.name}: {exc}")

        if done:
            self.message_user(
                request,
                f"{done} shop(s) approved and told. Customers can see them now.",
                messages.SUCCESS,
            )
        for line in refused:
            self.message_user(request, line, messages.WARNING)

    @admin.action(description="Reject selected shops (with a reason)")
    def reject_shops(self, request, queryset):
        """
        Two steps: pick the shops, then type the reason on the next page. One
        reason covers the batch, which is right — you reject a batch because
        they share a problem.
        """
        if "apply" in request.POST:
            form = RejectionForm(request.POST)
            if form.is_valid():
                reason = form.cleaned_data["reason"]
                done, refused = 0, []
                for shop in queryset:
                    try:
                        reject_business(business_id=shop.pk, reason=reason)
                        done += 1
                    except BusinessFlowError as exc:
                        refused.append(f"{shop.name}: {exc}")

                if done:
                    self.message_user(
                        request,
                        f"{done} shop(s) rejected. The reason was sent to each owner.",
                        messages.SUCCESS,
                    )
                for line in refused:
                    self.message_user(request, line, messages.WARNING)
                return None
        else:
            form = RejectionForm()

        return render(
            request,
            "admin/businesses/reject_shops.html",
            {
                "shops": queryset,
                "form": form,
                "action_checkbox_name": ACTION_CHECKBOX_NAME,
                "opts": self.model._meta,
                "title": "Reject shops",
            },
        )

    # Delivery is edited constantly while shops are being signed up, so make it
    # changeable straight from the list.
    list_editable = (
        "delivers",
        "delivery_fee",
    )

    inlines = [BusinessLocationInline]

    list_filter = (
        "category",
        "status",
        "is_active",
        "delivers",
    )

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            _vendor_cancellations=Count(
                "products__orderitem__order",
                filter=Q(products__orderitem__order__cancelled_by="vendor"),
                distinct=True,
            )
        )

    @admin.display(description="Vendor cancellations", ordering="_vendor_cancellations")
    def vendor_cancellations(self, obj):
        """Orders this shop cancelled itself (out of stock, damaged, other)."""
        return obj._vendor_cancellations

    search_fields = (
        "name",
        "slug",
        "business_email",
        "business_phone",
        "owner__email",
    )

    autocomplete_fields = (
        "owner",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    prepopulated_fields = {
        "slug": ("name",),
    }

    date_hierarchy = "created_at"

    list_select_related = (
        "owner",
    )


# =========================================================
# Branch
# =========================================================

@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "business",
        "city",
        "state",
        "phone_number",
        "is_active",
    )

    list_filter = (
        "city",
        "state",
        "country",
        "is_active",
    )

    search_fields = (
        "name",
        "business__name",
        "city",
        "state",
    )

    autocomplete_fields = (
        "business",
    )

    list_select_related = (
        "business",
    )


# =========================================================
# Business Members
# =========================================================

@admin.register(BusinessMember)
class BusinessMemberAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "business",
        "branch",
        "role",
        "status",
        "is_active",
        "joined_at",
    )

    list_filter = (
        "role",
        "status",
    )

    search_fields = (
        "user__email",
        "business__name",
    )

    autocomplete_fields = (
        "user",
        "business",
        "branch",
        "invited_by",
    )

    list_select_related = (
        "user",
        "business",
        "branch",
    )

# =========================================================
# Business Hours
# =========================================================

@admin.register(BusinessHours)
class BusinessHoursAdmin(admin.ModelAdmin):
    list_display = (
        "branch",
        "weekday",
        "opening_time",
        "closing_time",
        "is_closed",
        "is_twenty_four_hours",
    )

    list_filter = (
        "weekday",
        "is_closed",
        "is_twenty_four_hours",
    )

    autocomplete_fields = (
        "branch",
    )

    list_select_related = (
        "branch",
    )


# =========================================================
# Gallery
# =========================================================

@admin.register(BusinessGallery)
class BusinessGalleryAdmin(admin.ModelAdmin):
    list_display = (
        "business",
        "caption",
        "display_order",
        "is_active",
        "created_at",
    )

    list_filter = (
        "is_active",
    )

    search_fields = (
        "business__name",
        "caption",
    )

    autocomplete_fields = (
        "business",
    )

    list_select_related = (
        "business",
    )

    ordering = (
        "display_order",
        "-created_at",
    )

# =========================================================
# Rating
# =========================================================

@admin.register(BusinessRating)
class BusinessRatingAdmin(admin.ModelAdmin):
    list_display = (
        "business",
        "customer",
        "score",
        "is_visible",
        "created_at",
    )

    list_filter = (
        "score",
        "is_visible",
    )

    search_fields = (
        "business__name",
        "customer__email",
        "review",
    )

    autocomplete_fields = (
        "business",
        "customer",
    )

    list_select_related = (
        "business",
        "customer",
    )

    ordering = (
        "-created_at",
    )

# =========================================================
# Restaurant
# =========================================================

@admin.register(RestaurantProfile)
class RestaurantProfileAdmin(admin.ModelAdmin):
    list_display = (
        "business",
        "cuisine",
        "accepts_delivery",
        "accepts_takeaway",
        "accepts_reservations",
    )

    search_fields = (
        "business__name",
        "cuisine",
    )

    autocomplete_fields = (
        "business",
    )


# =========================================================
# Delivery Zone
# =========================================================

@admin.register(DeliveryZone)
class DeliveryZoneAdmin(admin.ModelAdmin):
    list_display = (
        "branch",
        "name",
        "radius_km",
        "delivery_fee",
        "is_active",
    )

    list_filter = (
        "is_active",
    )

    search_fields = (
        "branch__name",
        "name",
    )

    autocomplete_fields = (
        "branch",
    )

    list_select_related = (
        "branch",
    )


# =========================================================
# Verification
# =========================================================

@admin.register(BusinessVerification)
class BusinessVerificationAdmin(admin.ModelAdmin):
    list_display = (
        "business",
        "status",
        "verified_by",
        "submitted_at",
        "verified_at",
    )

    list_filter = (
        "status",
    )

    search_fields = (
        "business__name",
        "registration_number",
        "legal_name",
    )

    autocomplete_fields = (
        "business",
        "verified_by",
    )

    list_select_related = (
        "business",
        "verified_by",
    )


# =========================================================
# Documents
# =========================================================

@admin.register(BusinessDocument)
class BusinessDocumentAdmin(admin.ModelAdmin):
    list_display = (
        "business",
        "document_type",
        "title",
        "uploaded_by",
        "is_verified",
        "expiry_date",
        "created_at",
    )

    list_filter = (
        "document_type",
        "is_verified",
    )

    search_fields = (
        "business__name",
        "title",
        "description",
    )

    autocomplete_fields = (
        "business",
        "uploaded_by",
        "verified_by",
    )

    list_select_related = (
        "business",
        "uploaded_by",
        "verified_by",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
        "verified_at",
    )

    ordering = (
        "-created_at",
    )