from rest_framework import serializers
from .models import Booking
from .demo import DEMO_PREFIX
from payments.models import Payment


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ["id", "reference", "amount", "method", "status", "created_at"]


class BookingSerializer(serializers.ModelSerializer):
    guests = serializers.IntegerField(min_value=1, default=1)
    payment = PaymentSerializer(read_only=True)
    hotel_name = serializers.CharField(source="room.floor.hotel.name", read_only=True)
    room_number = serializers.CharField(source="room.number", read_only=True)
    customer_name = serializers.CharField(source="customer.username", read_only=True)
    reviewed = serializers.SerializerMethodField()
    is_demo = serializers.SerializerMethodField()
    customer_display_name = serializers.SerializerMethodField()

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
            "payment",
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
