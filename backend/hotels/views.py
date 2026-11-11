import math
from datetime import date
from decimal import Decimal, InvalidOperation
from django.db.models import Q, Min, Avg
from django.db.models.deletion import ProtectedError
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from accounts.permissions import admin, manages, IsAdmin
from .models import Hotel, HotelPhoto
from .location import CITY_NAME
from .serializers import HotelSerializer, HotelPhotoSerializer
from notifications.models import Notification


def dates(query, required=False):
    start = query.get("check_in")
    end = query.get("check_out")
    if not start and not end and not required:
        return None, None
    try:
        start = date.fromisoformat(start)
        end = date.fromisoformat(end)
    except (ValueError, TypeError):
        raise ValidationError(
            "Provide valid check_in and check_out dates (YYYY-MM-DD)."
        )
    if end <= start:
        raise ValidationError("Check-out must follow check-in.")
    return start, end


def visible_hotels(user):
    q = Hotel.objects.filter(city=CITY_NAME)
    if admin(user):
        return q
    if user.is_authenticated and user.role == "owner":
        return q.filter(Q(status="verified") | Q(owner=user))
    return q.filter(status="verified")


class SafeDestroyMixin:
    def perform_destroy(self, instance):
        try:
            instance.delete()
        except ProtectedError:
            raise ValidationError(
                "This record has reservations or dependent rooms. Deactivate it instead."
            )


class HotelViewSet(SafeDestroyMixin, viewsets.ModelViewSet):
    serializer_class = HotelSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        q = (
            visible_hotels(self.request.user)
            .select_related("owner")
            .prefetch_related("photos")
        )
        p = self.request.query_params
        if p.get("mine") == "true":
            if not self.request.user.is_authenticated:
                return q.none()
            q = q.filter(owner=self.request.user)
        if p.get("status") and admin(self.request.user):
            q = q.filter(status=p["status"])
        if p.get("search"):
            q = q.filter(
                Q(name__icontains=p["search"])
                | Q(city__icontains=p["search"])
                | Q(address__icontains=p["search"])
            )
        if p.get("city"):
            q = q.filter(city__icontains=p["city"])
        if p.get("stars"):
            try:
                stars = int(p["stars"])
            except ValueError:
                raise ValidationError("Stars must be an integer.")
            q = q.filter(stars__gte=stars)
        for amenity in p.get("amenities", "").split(","):
            if amenity.strip():
                q = q.filter(amenities__icontains=amenity.strip())
        start, end = dates(p)
        from rooms.models import Room

        available = Room.objects.filter(active=True)
        if start:
            available = available.exclude(
                bookings__in=__import__(
                    "bookings.models", fromlist=["Booking"]
                ).Booking.objects.filter(
                    status="confirmed", check_in__lt=end, check_out__gt=start
                )
            )
        for key, lookup in [
            ("min_price", "price__gte"),
            ("max_price", "price__lte"),
            ("guests", "capacity__gte"),
        ]:
            if p.get(key):
                try:
                    value = Decimal(p[key])
                    if not value.is_finite() or value < 0:
                        raise InvalidOperation
                    available = available.filter(**{lookup: value})
                except (InvalidOperation, ValueError):
                    raise ValidationError(f"Invalid {key}.")
        q = (
            q.filter(floors__rooms__in=available).distinct()
            if (start or any(p.get(k) for k in ["min_price", "max_price", "guests"]))
            else q
        )
        q = q.annotate(
            starting_price=Min("floors__rooms__price"),
            average_rating=Avg("floors__rooms__bookings__review__rating"),
        )
        if p.get("rating"):
            try:
                q = q.filter(average_rating__gte=float(p["rating"]))
            except ValueError:
                raise ValidationError("Invalid rating.")
        return q.order_by(
            {
                "price": "starting_price",
                "rating": "-average_rating",
                "newest": "-created_at",
            }.get(p.get("sort"), "-created_at")
        )

    def perform_create(self, serializer):
        if self.request.user.role != "owner" and not admin(self.request.user):
            raise PermissionDenied("Register as an owner to list hotels.")
        if self.request.user.role == "owner" and self.request.user.owner_approval_status != "approved":
            raise PermissionDenied("An administrator must approve your owner account before you can list a hotel.")
        serializer.save(owner=self.request.user)

    def perform_update(self, serializer):
        if not manages(self.request.user, serializer.instance):
            raise PermissionDenied("You do not manage this hotel.")
        serializer.save(status="pending")

    def perform_destroy(self, instance):
        if not manages(self.request.user, instance):
            raise PermissionDenied()
        super().perform_destroy(instance)

    @action(detail=True, methods=["post"], permission_classes=[IsAdmin])
    def verify(self, request, pk=None):
        hotel = self.get_object()
        decision = request.data.get("status")
        if decision not in ["verified", "rejected"]:
            raise ValidationError("Choose verified or rejected.")
        hotel.status = decision
        hotel.verification_note = str(request.data.get("note", ""))[:2000]
        hotel.save()
        Notification.objects.create(
            user=hotel.owner,
            title=f"Hotel {decision}",
            message=f"{hotel.name}: {hotel.verification_note or decision}",
        )
        return Response(self.get_serializer(hotel).data)

    @action(detail=False, methods=["get"])
    def nearby(self, request):
        try:
            lat = float(request.query_params["lat"])
            lng = float(request.query_params["lng"])
            radius = float(request.query_params.get("radius", 50))
            if (
                not all(math.isfinite(v) for v in [lat, lng, radius])
                or not -90 <= lat <= 90
                or not -180 <= lng <= 180
                or not 0 < radius <= 500
            ):
                raise ValueError
        except (KeyError, ValueError):
            raise ValidationError("Valid lat, lng, and radius (1?500 km) are required.")
        result = []
        for hotel in self.get_queryset():
            a = (
                math.sin(math.radians(float(hotel.latitude) - lat) / 2) ** 2
                + math.cos(math.radians(lat))
                * math.cos(math.radians(float(hotel.latitude)))
                * math.sin(math.radians(float(hotel.longitude) - lng) / 2) ** 2
            )
            distance = 6371 * 2 * math.atan2(math.sqrt(a), math.sqrt(max(0, 1 - a)))
            if distance <= radius:
                result.append((distance, hotel))
        return Response(
            [
                dict(self.get_serializer(h).data, distance_km=round(d, 2))
                for d, h in sorted(result, key=lambda x: x[0])
            ]
        )


class HotelPhotoViewSet(viewsets.ModelViewSet):
    serializer_class = HotelPhotoSerializer

    def get_queryset(self):
        if admin(self.request.user):
            return HotelPhoto.objects.all()
        return HotelPhoto.objects.filter(hotel__owner=self.request.user)

    def perform_create(self, serializer):
        if not manages(self.request.user, serializer.validated_data["hotel"]):
            raise PermissionDenied()
        if serializer.validated_data["image"].size > 5 * 1024 * 1024:
            raise ValidationError("Maximum image size is 5 MB.")
        serializer.save()

    def perform_update(self, serializer):
        if not manages(
            self.request.user,
            serializer.validated_data.get("hotel", serializer.instance.hotel),
        ):
            raise PermissionDenied()
        serializer.save()
