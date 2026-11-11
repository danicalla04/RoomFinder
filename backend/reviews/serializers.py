from rest_framework import serializers
from .models import Review
from django.utils import timezone


class ReviewSerializer(serializers.ModelSerializer):
    author = serializers.CharField(source="booking.customer.first_name", read_only=True)
    hotel = serializers.IntegerField(
        source="booking.room.floor.hotel_id", read_only=True
    )

    class Meta:
        model = Review
        fields = ["id", "booking", "author", "hotel", "rating", "comment", "created_at"]
        read_only_fields = ["created_at"]

    def validate_booking(self, booking):
        if booking.customer_id != self.context["request"].user.id:
            raise serializers.ValidationError("Review your own reservation only.")
        if booking.status != "confirmed" or booking.check_out > timezone.localdate():
            raise serializers.ValidationError(
                "Reviews are available after a completed stay."
            )
        return booking
