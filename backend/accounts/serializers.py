from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import User
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework.exceptions import AuthenticationFailed
from django.db import transaction
from smtplib import SMTPException
from rest_framework.exceptions import APIException
from .email_verification import send_verification


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "phone", "role"]
        read_only_fields = ["id", "username", "email", "role"]


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
        try:
            with transaction.atomic():
                if data.get("role") == User.Role.OWNER:
                    data["owner_approval_status"] = User.OwnerApproval.PENDING
                user = User.objects.create_user(**data, is_active=False)
                send_verification(user)
                return user
        except (OSError, RuntimeError, SMTPException) as exc:
            raise EmailDeliveryUnavailable() from exc


class EmailDeliveryUnavailable(APIException):
    status_code = 503
    default_detail = "Verification email could not be sent. Please try again later."


class RoleTokenObtainPairSerializer(TokenObtainPairSerializer):
    role = serializers.ChoiceField(choices=User.Role.choices, required=False)

    def validate(self, attrs):
        selected_role = attrs.pop("role", None)
        candidate = User.objects.filter(username=attrs.get("username", "")).first()
        password_matches = bool(candidate and candidate.check_password(attrs.get("password", "")))
        if password_matches and not candidate.email_verified_at and not candidate.is_active:
            raise AuthenticationFailed("Verify your email before signing in.")
        if password_matches and candidate.role == User.Role.OWNER and candidate.email_verified_at:
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
