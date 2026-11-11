from rest_framework import serializers
from .models import Hotel, HotelPhoto
from rooms.models import Room
from django.db.models import Avg, Min


class HotelPhotoSerializer(serializers.ModelSerializer):
    def validate_image(self, value):
        if value.size > 5 * 1024 * 1024:
            raise serializers.ValidationError("Maximum image size is 5 MB.")
        return value

    class Meta:
        model = HotelPhoto
        fields = ["id", "hotel", "image", "caption"]


class HotelSerializer(serializers.ModelSerializer):
    photos = HotelPhotoSerializer(many=True, read_only=True)
    min_price = serializers.SerializerMethodField()
    rating = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()
    owner_name = serializers.CharField(source="owner.username", read_only=True)

    def get_min_price(self, obj):
        return obj.floors.filter(rooms__active=True).aggregate(p=Min("rooms__price"))[
            "p"
        ]

    def get_rating(self, obj):
        return obj.floors.aggregate(r=Avg("rooms__bookings__review__rating"))["r"]

    def get_review_count(self, obj):
        return obj.floors.filter(rooms__bookings__review__isnull=False).count()

    class Meta:
        model = Hotel
        fields = [
            "id",
            "owner",
            "owner_name",
            "name",
            "description",
            "city",
            "address",
            "latitude",
            "longitude",
            "amenities",
            "stars",
            "status",
            "verification_note",
            "photos",
            "min_price",
            "rating",
            "review_count",
        ]
        read_only_fields = ["owner", "status", "verification_note"]

    def validate_amenities(self, value):
        if not isinstance(value, list) or any(
            not isinstance(x, str) or len(x) > 60 for x in value
        ):
            raise serializers.ValidationError(
                "Use a list of amenity names (max 60 characters each)."
            )
        return value
