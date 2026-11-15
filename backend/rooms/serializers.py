from rest_framework import serializers
from .models import Floor, Room, RoomPhoto
from accounts.permissions import manages
from django.utils import timezone
from datetime import date, timedelta
from decimal import Decimal
import math


def measured_rectangle(value, label):
    if not isinstance(value, dict):
        raise serializers.ValidationError(f"{label} must be a rectangle.")
    result = {}
    for key in ("x", "y", "width", "height"):
        raw = value.get(key)
        if isinstance(raw, bool) or not isinstance(raw, (int, float)) or not math.isfinite(raw):
            raise serializers.ValidationError(f"{label} needs a valid {key} in metres.")
        result[key] = round(float(raw), 2)
    if result["x"] < 0 or result["y"] < 0 or result["width"] < 1 or result["height"] < 1:
        raise serializers.ValidationError(f"{label} must have positive dimensions and a position inside the plan.")
    return result


def overlaps(first, second):
    return (
        first["x"] < second["x"] + second["width"] - 0.01
        and second["x"] < first["x"] + first["width"] - 0.01
        and first["y"] < second["y"] + second["height"] - 0.01
        and second["y"] < first["y"] + first["height"] - 0.01
    )


def named_area(value, label, parent_width, parent_height):
    rectangle = measured_rectangle(value, label)
    name = value.get("label") or value.get("kind")
    if not isinstance(name, str) or not name.strip() or len(name.strip()) > 60:
        raise serializers.ValidationError(f"{label} needs a name of up to 60 characters.")
    if rectangle["x"] + rectangle["width"] > parent_width + 0.01 or rectangle["y"] + rectangle["height"] > parent_height + 0.01:
        raise serializers.ValidationError(f"{label} must fit inside its plan.")
    return {**rectangle, "label": name.strip()}


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
        fields = ["id", "hotel", "number", "name", "columns", "plan_width_m", "plan_height_m", "areas"]

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
        width = data.get("plan_width_m", self.instance.plan_width_m if self.instance else Decimal("30"))
        height = data.get("plan_height_m", self.instance.plan_height_m if self.instance else Decimal("20"))
        if not 5 <= width <= 200 or not 5 <= height <= 200:
            raise serializers.ValidationError("Floor dimensions must be between 5 and 200 metres.")
        if self.instance:
            for room in self.instance.rooms.all():
                if room.plan and (
                    room.plan["x"] + room.plan["width"] > float(width) + 0.01
                    or room.plan["y"] + room.plan["height"] > float(height) + 0.01
                ):
                    raise serializers.ValidationError("Move or resize rooms before shrinking this floor plan.")
        areas = data.get("areas", self.instance.areas if self.instance else [])
        if not isinstance(areas, list) or len(areas) > 50:
            raise serializers.ValidationError("A floor can have up to 50 named areas.")
        checked_areas = []
        for area in areas:
            rectangle = named_area(area, "Floor area", float(width), float(height))
            if any(overlaps(rectangle, other) for other in checked_areas):
                raise serializers.ValidationError("Floor areas cannot overlap.")
            checked_areas.append(rectangle)
        if self.instance:
            for room in self.instance.rooms.all():
                room_plan = room.plan or {"x": room.column * 5, "y": room.row * 5, "width": 5, "height": 5}
                if any(overlaps(room_plan, area) for area in checked_areas):
                    raise serializers.ValidationError(f"A floor area overlaps room {room.number}.")
        if "areas" in data:
            data["areas"] = checked_areas
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
                status__in=["pending", "confirmed"], check_in__lt=end, check_out__gt=start
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
            "plan",
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
        if "plan" in data:
            plan = measured_rectangle(data["plan"], "Room")
            if plan["x"] + plan["width"] > float(floor.plan_width_m) + 0.01 or plan["y"] + plan["height"] > float(floor.plan_height_m) + 0.01:
                raise serializers.ValidationError("Room must fit inside the floor plan.")
            zones = data["plan"].get("zones", [])
            if not isinstance(zones, list) or len(zones) > 50:
                raise serializers.ValidationError("A room can have up to 50 interior areas.")
            checked_zones = []
            for zone in zones:
                rectangle = named_area(zone, "Interior area", plan["width"], plan["height"])
                if any(overlaps(rectangle, other) for other in checked_zones):
                    raise serializers.ValidationError("Interior areas cannot overlap.")
                checked_zones.append(rectangle)
            for room in floor.rooms.exclude(pk=self.instance.pk if self.instance else None):
                other = room.plan or {"x": room.column * 5, "y": room.row * 5, "width": 5, "height": 5}
                if overlaps(plan, other):
                    raise serializers.ValidationError(f"Room overlaps room {room.number}.")
            if any(overlaps(plan, area) for area in floor.areas):
                raise serializers.ValidationError("Room overlaps a named floor area.")
            data["plan"] = {**plan, "zones": checked_zones}
            data["area"] = Decimal(str(round(plan["width"] * plan["height"], 2)))
        return data
