from rest_framework import serializers
from .models import Booking, BookingMessage
from .demo import DEMO_PREFIX
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal


class BookingSerializer(serializers.ModelSerializer):
    guests = serializers.IntegerField(min_value=1, default=1)
    hotel_name = serializers.CharField(source="room.floor.hotel.name", read_only=True)
    room_number = serializers.CharField(source="room.number", read_only=True)
    customer_name = serializers.CharField(source="customer.username", read_only=True)
    reviewed = serializers.SerializerMethodField()
    is_demo = serializers.SerializerMethodField()
    customer_display_name = serializers.SerializerMethodField()
    cancel_deadline = serializers.SerializerMethodField()
    can_cancel = serializers.SerializerMethodField()
    can_request_cancellation = serializers.SerializerMethodField()
    cancellation_requested = serializers.SerializerMethodField()

    def get_cancel_deadline(self, obj):
        return obj.created_at + timedelta(hours=2)

    def get_can_cancel(self, obj):
        return (
            obj.status == "pending"
            and timezone.now() < self.get_cancel_deadline(obj)
            and obj.check_in > timezone.localdate()
        )

    def get_can_request_cancellation(self, obj):
        return (
            obj.status == "confirmed"
            and not obj.checked_out_at
            and obj.check_out > timezone.localdate()
            and not obj.cancellation_requested_at
        )

    def get_cancellation_requested(self, obj):
        return bool(obj.cancellation_requested_at)

    def get_customer_display_name(self, obj):
        return obj.customer.get_full_name() or obj.customer.username

    def get_is_demo(self, obj):
        return obj.special_requests.startswith(DEMO_PREFIX)

    def get_reviewed(self, obj):
        return hasattr(obj, "review")

    class Meta:
        model = Booking
        fields = [
            "id",
            "reference",
            "customer",
            "customer_name",
            "customer_display_name",
            "room",
            "room_number",
            "hotel_name",
            "check_in",
            "check_out",
            "guests",
            "total",
            "discount",
            "promotion_code",
            "status",
            "special_requests",
            "created_at",
            "checked_out_at",
            "cancel_deadline",
            "can_cancel",
            "can_request_cancellation",
            "cancellation_requested",
            "reviewed",
            "is_demo",
        ]
        read_only_fields = [
            "reference",
            "customer",
            "total",
            "discount",
            "status",
            "created_at",
            "checked_out_at",
        ]

    def validate(self, data):
        from django.utils import timezone

        start = data["check_in"]
        end = data["check_out"]
        room = data["room"]
        if start < timezone.localdate():
            raise serializers.ValidationError("Check-in cannot be in the past.")
        if end <= start:
            raise serializers.ValidationError("Check-out must follow check-in.")
        if (end - start).days > 30:
            raise serializers.ValidationError("Maximum stay is 30 nights.")
        if data.get("guests", 1) > room.capacity:
            raise serializers.ValidationError("Room capacity exceeded.")
        if not room.active or room.floor.hotel.status != "verified":
            raise serializers.ValidationError(
                "This room is not accepting reservations."
            )
        return data


class BookingMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.SerializerMethodField()

    class Meta:
        model = BookingMessage
        fields = ["id", "booking", "sender", "sender_name", "message", "created_at", "read_at"]
        read_only_fields = ["id", "booking", "sender", "sender_name", "created_at", "read_at"]

    def get_sender_name(self, obj):
        return obj.sender.get_full_name() or obj.sender.username

    def validate_message(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Write a message before sending.")
        if len(value) > 2000:
            raise serializers.ValidationError("Messages must be 2,000 characters or fewer.")
        return value
