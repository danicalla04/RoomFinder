from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import User
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework.exceptions import AuthenticationFailed


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "phone", "role"]
        read_only_fields = ["id", "username", "email", "role"]


class AdminUserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "phone"]


class AdminCreateAccountSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    role = serializers.ChoiceField(choices=[User.Role.CUSTOMER, User.Role.OWNER])

    class Meta:
        model = User
        fields = ["username", "email", "password", "first_name", "last_name", "phone", "role"]

    def create(self, validated_data):
        if validated_data["role"] == User.Role.OWNER:
            validated_data["owner_approval_status"] = User.OwnerApproval.APPROVED
        return User.objects.create_user(**validated_data, is_active=True)


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    role = serializers.ChoiceField(choices=["customer", "owner"], default="customer")

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "password",
            "first_name",
            "last_name",
            "phone",
            "role",
        ]

    def create(self, data):
        if data.get("role") == User.Role.OWNER:
            data["owner_approval_status"] = User.OwnerApproval.PENDING
        return User.objects.create_user(**data, is_active=True)


class RoleTokenObtainPairSerializer(TokenObtainPairSerializer):
    role = serializers.ChoiceField(choices=User.Role.choices, required=False)

    def validate(self, attrs):
        selected_role = attrs.pop("role", None)
        candidate = User.objects.filter(username=attrs.get("username", "")).first()
        password_matches = bool(candidate and candidate.check_password(attrs.get("password", "")))
        if password_matches and candidate.role == User.Role.OWNER:
            if candidate.owner_approval_status == User.OwnerApproval.PENDING:
                raise AuthenticationFailed("Your hotel-owner request is awaiting administrator approval.")
            if candidate.owner_approval_status == User.OwnerApproval.REJECTED:
                raise AuthenticationFailed("Your hotel-owner request was declined. Contact the administrator.")
        data = super().validate(attrs)
        if selected_role is not None and selected_role != self.user.role:
            raise AuthenticationFailed(
                "The selected role does not match this account. Choose the correct role and try again."
            )
        return data
