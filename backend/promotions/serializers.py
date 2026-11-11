from rest_framework import serializers
from .models import Promotion
from accounts.permissions import manages


class PromotionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Promotion
        fields = ["id", "hotel", "code", "percent", "starts_on", "ends_on", "active"]

    def validate(self, data):
        hotel = data.get("hotel", self.instance.hotel if self.instance else None)
        if not manages(self.context["request"].user, hotel):
            raise serializers.ValidationError("You do not manage this hotel.")
        if self.instance and hotel.pk != self.instance.hotel_id:
            raise serializers.ValidationError("Promotion hotel cannot change.")
        start = data.get(
            "starts_on", self.instance.starts_on if self.instance else None
        )
        end = data.get("ends_on", self.instance.ends_on if self.instance else None)
        if start and end and end < start:
            raise serializers.ValidationError("End date must follow start date.")
        if "code" in data:
            data["code"] = data["code"].strip().upper()
        return data
