"""
Serializers for the users app.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import (
    Charity, Consumer, FavoriteListing, Merchant, UserAddress,
    ProfileUpdateRequest, ProfileUpdateDocument
)

User = get_user_model()


class UserBasicSerializer(serializers.ModelSerializer):
    """Minimal user info serializer for embedding in other responses."""

    class Meta:
        model = User
        fields = ["id", "email", "user_type", "avatar_url"]
        read_only_fields = fields


class ConsumerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Consumer
        fields = [
            "eco_score",
            "eco_tier",
            "eco_score_updated_at",
            "last_active_at",
            "total_orders",
            "completed_orders",
            "cancelled_orders",
            "no_show_orders",
            "total_food_saved_kg",
            "dietary_preferences",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "eco_score",
            "eco_tier",
            "eco_score_updated_at",
            "last_active_at",
            "total_orders",
            "completed_orders",
            "cancelled_orders",
            "no_show_orders",
            "total_food_saved_kg",
            "created_at",
            "updated_at",
        ]


class MerchantProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Merchant
        fields = [
            "id",
            "business_name",
            "business_name_ar",
            "business_type",
            "description",
            "address",
            "wilaya",
            "latitude",
            "longitude",
            "logo_url",
            "cover_image_url",
            "phone",
            "website",
            "verification_status",
            "average_rating",
            "total_reviews",
            "eco_score",
            "eco_tier",
            "eco_score_updated_at",
            "last_active_at",
            "total_no_shows",
            "total_listings",
            "total_orders_fulfilled",
            "total_donations",
            "food_saved_kg",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "verification_status",
            "average_rating",
            "total_reviews",
            "eco_score",
            "eco_tier",
            "eco_score_updated_at",
            "last_active_at",
            "total_no_shows",
            "total_listings",
            "total_orders_fulfilled",
            "total_donations",
            "food_saved_kg",
            "created_at",
            "updated_at",
        ]


class CharityProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Charity
        fields = [
            "id",
            "organization_name",
            "organization_name_ar",
            "description",
            "address",
            "wilaya",
            "service_area",
            "phone",
            "website",
            "logo_url",
            "verification_status",
            "eco_score",
            "eco_tier",
            "eco_score_updated_at",
            "last_active_at",
            "total_no_shows",
            "total_donations_received",
            "total_meals_provided",
            "total_families_helped",
            "food_received_kg",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "verification_status",
            "eco_score",
            "eco_tier",
            "eco_score_updated_at",
            "last_active_at",
            "total_no_shows",
            "total_donations_received",
            "total_meals_provided",
            "total_families_helped",
            "food_received_kg",
            "created_at",
            "updated_at",
        ]


class UserRegistrationSerializer(serializers.Serializer):
    """Handles new user registration including profile creation."""

    email = serializers.EmailField()
    phone = serializers.CharField(max_length=20)
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)
    user_type = serializers.ChoiceField(choices=["consumer", "merchant", "charity"])
    preferred_language = serializers.ChoiceField(
        choices=["fr", "ar", "en"], default="fr"
    )
    # Optional profile data
    profile_data = serializers.DictField(required=False, default=dict)

    def validate_email(self, value):
        if User.objects.filter(email=value.lower()).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value.lower()

    def validate_phone(self, value):
        from apps.core.validators import validate_algerian_phone
        from django.core.exceptions import ValidationError as DjangoValidationError

        try:
            validate_algerian_phone(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(e.message)

        if User.objects.filter(phone=value).exists():
            raise serializers.ValidationError(
                "A user with this phone number already exists."
            )
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError(
                {"password_confirm": "Passwords do not match."}
            )
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        profile_data = validated_data.pop("profile_data", {})
        validated_data.pop("password_confirm")
        password = validated_data.pop("password")
        user_type = validated_data["user_type"]

        user = User(**validated_data)
        user.set_password(password)
        user.save()

        # Create the appropriate profile
        if user_type == "consumer":
            Consumer.objects.create(
                user=user,
                **{k: v for k, v in profile_data.items() if k in ["dietary_preferences"]},
            )
        elif user_type == "merchant":
            Merchant.objects.create(
                user=user,
                business_name=profile_data.get("business_name", ""),
                business_type=profile_data.get("business_type", "restaurant"),
                **{
                    k: v
                    for k, v in profile_data.items()
                    if k
                    not in [
                        "business_name",
                        "business_type",
                    ]
                },
            )
        elif user_type == "charity":
            Charity.objects.create(
                user=user,
                organization_name=profile_data.get("organization_name", ""),
                **{
                    k: v
                    for k, v in profile_data.items()
                    if k != "organization_name"
                },
            )

        return user


class UserDetailSerializer(serializers.ModelSerializer):
    """Full user detail with nested profile data."""

    profile = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "phone",
            "user_type",
            "avatar_url",
            "preferred_language",
            "email_verified",
            "phone_verified",
            "is_active",
            "date_joined",
            "last_login",
            "profile",
        ]
        read_only_fields = [
            "id",
            "email",
            "user_type",
            "email_verified",
            "phone_verified",
            "date_joined",
            "last_login",
        ]

    def get_profile(self, obj):
        if obj.is_consumer:
            profile = getattr(obj, "consumer_profile", None)
            return ConsumerProfileSerializer(profile).data if profile else None
        elif obj.is_merchant:
            profile = getattr(obj, "merchant_profile", None)
            return MerchantProfileSerializer(profile).data if profile else None
        elif obj.is_charity:
            profile = getattr(obj, "charity_profile", None)
            return CharityProfileSerializer(profile).data if profile else None
        return None


class MerchantPublicSerializer(serializers.ModelSerializer):
    """Public merchant information for consumer-facing listing pages."""

    class Meta:
        model = Merchant
        fields = [
            "id",
            "business_name",
            "business_type",
            "description",
            "address",
            "wilaya",
            "logo_url",
            "cover_image_url",
            "average_rating",
            "total_reviews",
            "verification_status",
            "is_active",
        ]


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    JWT token serializer that adds user_type and user_id to the token claims.
    """

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["user_type"] = user.user_type
        token["email"] = user.email
        token["email_verified"] = user.email_verified
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data["user_id"] = str(self.user.id)
        data["user_type"] = self.user.user_type
        data["email"] = self.user.email
        data["email_verified"] = self.user.email_verified
        data["is_staff"] = self.user.is_staff

        # Include verification_status so Flutter can decide which screen to show.
        if self.user.is_merchant:
            profile = getattr(self.user, "merchant_profile", None)
            data["verification_status"] = profile.verification_status if profile else "pending"
        elif self.user.is_charity:
            profile = getattr(self.user, "charity_profile", None)
            data["verification_status"] = profile.verification_status if profile else "pending"
        else:
            data["verification_status"] = "approved"  # consumers need no approval

        return data


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)
    new_password_confirm = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError(
                {"new_password_confirm": "New passwords do not match."}
            )
        try:
            validate_password(attrs["new_password"])
        except Exception as e:
            raise serializers.ValidationError({"new_password": list(e.messages)})
        return attrs


class EmailVerificationSerializer(serializers.Serializer):
    token = serializers.CharField()


class ResendVerificationEmailSerializer(serializers.Serializer):
    """No body required — user identity comes from the JWT token."""
    pass


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, min_length=8)
    new_password_confirm = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError(
                {"new_password_confirm": "Passwords do not match."}
            )
        try:
            validate_password(attrs["new_password"])
        except Exception as e:
            raise serializers.ValidationError({"new_password": list(e.messages)})
        return attrs


class MerchantVerificationSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=["approved", "rejected", "suspended"]
    )
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class CharityVerificationSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=["approved", "rejected", "suspended"]
    )
    notes = serializers.CharField(required=False, allow_blank=True, default="")


# ── Admin serializers ─────────────────────────────────────────────────────────

class AdminMerchantSerializer(serializers.ModelSerializer):
    """Full merchant detail for admin listing/management."""

    email = serializers.EmailField(source="user.email", read_only=True)
    owner_name = serializers.SerializerMethodField()

    class Meta:
        model = Merchant
        fields = [
            "id", "business_name", "business_type", "wilaya", "address",
            "phone", "website", "logo_url", "registration_number",
            "verification_status", "verification_notes",
            "eco_score", "eco_tier", "total_no_shows", 
            "total_orders_fulfilled", "average_rating",
            "total_reviews", "total_listings", "food_saved_kg",
            "is_active", "created_at", "verified_at",
            "email", "owner_name",
        ]
        read_only_fields = fields

    def get_owner_name(self, obj):
        user = obj.user
        name = f"{user.first_name} {user.last_name}".strip()
        return name or user.email


class AdminCharitySerializer(serializers.ModelSerializer):
    """Full charity detail for admin listing/management."""

    email = serializers.EmailField(source="user.email", read_only=True)
    contact_name = serializers.SerializerMethodField()

    class Meta:
        model = Charity
        fields = [
            "id", "organization_name", "wilaya", "address", "service_area",
            "phone", "website", "logo_url", "registration_number",
            "verification_status", "verification_notes",
            "total_donations_received", "total_meals_provided",
            "total_families_helped", "food_received_kg",
            "is_active", "created_at", "verified_at",
            "email", "contact_name",
        ]
        read_only_fields = fields

    def get_contact_name(self, obj):
        user = obj.user
        name = f"{user.first_name} {user.last_name}".strip()
        return name or user.email


class AdminUserSerializer(serializers.ModelSerializer):
    """User summary for admin listing."""

    eco_score = serializers.SerializerMethodField()
    total_orders = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "email", "phone", "user_type", "is_active",
            "email_verified", "date_joined", "last_login",
            "eco_score", "total_orders",
        ]
        read_only_fields = fields

    def get_eco_score(self, obj):
        profile = getattr(obj, "consumer_profile", None)
        return profile.eco_score if profile else None

    def get_total_orders(self, obj):
        profile = getattr(obj, "consumer_profile", None)
        return profile.total_orders if profile else None


class UserAddressSerializer(serializers.ModelSerializer):
    """Serializer for a user's saved delivery address."""

    class Meta:
        model = UserAddress
        fields = [
            "id",
            "label",
            "street",
            "city",
            "wilaya",
            "postal_code",
            "notes",
            "is_default",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


# ── Geographic location serializers ───────────────────────────────────────────

ALGERIA_LAT_MIN = 19.0
ALGERIA_LAT_MAX = 38.0
ALGERIA_LNG_MIN = -9.0
ALGERIA_LNG_MAX = 12.0


class MerchantLocationSerializer(serializers.Serializer):
    """
    Validates and stores a merchant's business coordinates.
    Enforces that coordinates lie within Algeria's bounding box.
    """

    latitude = serializers.DecimalField(max_digits=10, decimal_places=7)
    longitude = serializers.DecimalField(max_digits=10, decimal_places=7)
    address = serializers.CharField(max_length=500, required=False, allow_blank=True)
    wilaya = serializers.CharField(max_length=100, required=False, allow_blank=True)

    def validate_latitude(self, value):
        if not (ALGERIA_LAT_MIN <= float(value) <= ALGERIA_LAT_MAX):
            raise serializers.ValidationError(
                f"Latitude must be between {ALGERIA_LAT_MIN} and {ALGERIA_LAT_MAX} for Algeria."
            )
        return value

    def validate_longitude(self, value):
        if not (ALGERIA_LNG_MIN <= float(value) <= ALGERIA_LNG_MAX):
            raise serializers.ValidationError(
                f"Longitude must be between {ALGERIA_LNG_MIN} and {ALGERIA_LNG_MAX} for Algeria."
            )
        return value


class CharityServiceAreaSerializer(serializers.Serializer):
    """
    Validates and stores a charity's wilaya-based service area.
    Each element must be a name from ALGERIAN_WILAYAS; max 10 entries.
    """

    service_area = serializers.ListField(
        child=serializers.CharField(max_length=100),
        min_length=1,
    )

    def validate_service_area(self, value):
        from apps.core.constants import ALGERIAN_WILAYAS

        valid_set = set(ALGERIAN_WILAYAS)
        errors = []
        normalized = []
        for name in value:
            stripped = name.strip()
            if stripped in valid_set:
                normalized.append(stripped)
            else:
                # Case-insensitive match attempt for better UX
                match = next(
                    (w for w in ALGERIAN_WILAYAS if w.lower() == stripped.lower()),
                    None,
                )
                if match:
                    normalized.append(match)
                else:
                    errors.append(f"'{stripped}' is not a valid Algerian wilaya.")
        if errors:
            raise serializers.ValidationError(errors)
        # Remove duplicates while preserving order
        seen = set()
        deduped = [w for w in normalized if not (w in seen or seen.add(w))]
        if len(deduped) > 10:
            raise serializers.ValidationError("Maximum 10 wilayas allowed per service area.")
        return deduped


class FavoriteListingCreateSerializer(serializers.Serializer):
    """Validates input for creating a favorite relation."""

    listing_id = serializers.UUIDField()


class FavoriteListingSerializer(serializers.ModelSerializer):
    """Represents one favorite relation in lightweight responses."""

    listing_id = serializers.UUIDField(source="listing.id", read_only=True)

    class Meta:
        model = FavoriteListing
        fields = ["listing_id", "created_at"]


class EcoScoreEventSerializer(serializers.ModelSerializer):
    """Represents a single score event in the user's history."""

    class Meta:
        from .models import EcoScoreEvent
        model = EcoScoreEvent
        fields = [
            "id",
            "event_type",
            "delta",
            "score_before",
            "score_after",
            "reason",
            "created_at",
        ]
        read_only_fields = fields


class ProfileUpdateDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProfileUpdateDocument
        fields = ["id", "document_type", "file_url", "file_name", "created_at"]
        read_only_fields = ["id", "created_at"]


class ProfileUpdateRequestSerializer(serializers.ModelSerializer):
    documents = ProfileUpdateDocumentSerializer(many=True, read_only=True)
    user_email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = ProfileUpdateRequest
        fields = [
            "id", "user", "user_email", "changes", "status", 
            "admin_note", "documents", "created_at", 
            "processed_at", "processed_by"
        ]
        read_only_fields = [
            "id", "user", "user_email", "status", "documents", 
            "created_at", "processed_at", "processed_by"
        ]


class ProfileUpdateRequestCreateSerializer(serializers.Serializer):
    changes = serializers.DictField(
        help_text="Dictionary of fields to change. Sensitive fields only."
    )
    documents = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        default=list,
        help_text="List of {document_type, file_url, file_name} objects."
    )

    def validate_changes(self, value):
        if not value:
            raise serializers.ValidationError("At least one change must be requested.")
        return value


class ProfileUpdateRequestProcessSerializer(serializers.Serializer):
    admin_note = serializers.CharField(required=False, allow_blank=True, default="")
