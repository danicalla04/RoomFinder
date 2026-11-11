from rest_framework import serializers
from .models import Floor, Room, RoomPhoto
from accounts.permissions import manages
from django.utils import timezone
from datetime import date, timedelta


class RoomPhotoSerializer(serializers.ModelSerializer):
    def validate_image(self, value):
        if value.size > 5 * 1024 * 1024:
            raise serializers.ValidationError("Maximum image size is 5 MB.")
        return value

    class Meta:
        model = RoomPhoto
        fields = ["id", "room", "image", "caption"]


class FloorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Floor
        fields = ["id", "hotel", "number", "name", "columns"]

    def validate(self, data):
        hotel = data.get("hotel", self.instance.hotel if self.instance else None)
        if not manages(self.context["request"].user, hotel):
            raise serializers.ValidationError("You do not manage this hotel.")
        if self.instance and hotel.pk != self.instance.hotel_id:
            raise serializers.ValidationError("A floor cannot be moved between hotels.")
        if (
            self.instance
            and self.instance.rooms.filter(
                column__gte=data.get("columns", self.instance.columns)
            ).exists()
        ):
            raise serializers.ValidationError(
                "Move rooms inside the new column count before shrinking the grid."
            )
        if data.get("columns", 6) > 12:
            raise serializers.ValidationError("Maximum 12 columns.")
        return data


class RoomSerializer(serializers.ModelSerializer):
    photos = RoomPhotoSerializer(many=True, read_only=True)
    hotel_id = serializers.IntegerField(source="floor.hotel_id", read_only=True)
    floor_number = serializers.IntegerField(source="floor.number", read_only=True)
    available = serializers.SerializerMethodField()
    availability_status = serializers.SerializerMethodField()
    can_delete = serializers.SerializerMethodField()

    def get_availability_status(self, obj):
        cache = self.context.setdefault("room_availability", {})
        if obj.pk not in cache:
            query = self.context["request"].query_params
            start = query.get("check_in") or timezone.localdate().isoformat()
            end = (
                query.get("check_out")
                or (date.fromisoformat(start) + timedelta(days=1)).isoformat()
            )
            if not obj.active:
                state = "unavailable"
            elif obj.bookings.filter(
                status="confirmed", check_in__lt=end, check_out__gt=start
            ).exists():
                state = "booked"
            else:
                state = "available"
            cache[obj.pk] = state
        return cache[obj.pk]

    def get_available(self, obj):
        return self.get_availability_status(obj) == "available"

    def get_can_delete(self, obj):
        return (
            manages(self.context["request"].user, obj.floor.hotel)
            and not obj.bookings.exists()
        )

    class Meta:
        model = Room
        fields = [
            "id",
            "floor",
            "hotel_id",
            "floor_number",
            "number",
            "kind",
            "description",
            "price",
            "capacity",
            "beds",
            "area",
            "row",
            "column",
            "active",
            "photos",
            "available",
            "availability_status",
            "can_delete",
        ]

    def validate(self, data):
        floor = data.get("floor", self.instance.floor if self.instance else None)
        if not manages(self.context["request"].user, floor.hotel):
            raise serializers.ValidationError("You do not manage this hotel.")
        if self.instance and floor.pk != self.instance.floor_id:
            raise serializers.ValidationError(
                "A room cannot be moved to another floor."
            )
        if (
            data.get("column", self.instance.column if self.instance else 0)
            >= floor.columns
        ):
            raise serializers.ValidationError("Column must be inside the floor grid.")
        if data.get("row", 0) > 30:
            raise serializers.ValidationError("Maximum row index is 30.")
        return data
