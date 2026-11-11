from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.exceptions import PermissionDenied, ValidationError
from accounts.permissions import manages, admin
from hotels.views import visible_hotels, SafeDestroyMixin, dates
from .models import Floor, Room, RoomPhoto
from .serializers import FloorSerializer, RoomSerializer, RoomPhotoSerializer


class FloorViewSet(SafeDestroyMixin, viewsets.ModelViewSet):
    serializer_class = FloorSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        q = Floor.objects.filter(
            hotel__in=visible_hotels(self.request.user)
        ).select_related("hotel")
        if self.request.query_params.get("hotel"):
            q = q.filter(hotel_id=self.request.query_params["hotel"])
        return q

    def perform_destroy(self, instance):
        if not manages(self.request.user, instance.hotel):
            raise PermissionDenied()
        super().perform_destroy(instance)


class RoomViewSet(SafeDestroyMixin, viewsets.ModelViewSet):
    serializer_class = RoomSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        dates(self.request.query_params)
        q = (
            Room.objects.filter(floor__hotel__in=visible_hotels(self.request.user))
            .select_related("floor__hotel")
            .prefetch_related("photos")
        )
        for key, field in [("hotel", "floor__hotel_id"), ("floor", "floor_id")]:
            if self.request.query_params.get(key):
                q = q.filter(**{field: self.request.query_params[key]})
        return q

    def perform_destroy(self, instance):
        if not manages(self.request.user, instance.floor.hotel):
            raise PermissionDenied()
        super().perform_destroy(instance)


class RoomPhotoViewSet(viewsets.ModelViewSet):
    serializer_class = RoomPhotoSerializer

    def get_queryset(self):
        return (
            RoomPhoto.objects.all()
            if admin(self.request.user)
            else RoomPhoto.objects.filter(room__floor__hotel__owner=self.request.user)
        )

    def perform_create(self, serializer):
        if not manages(
            self.request.user, serializer.validated_data["room"].floor.hotel
        ):
            raise PermissionDenied()
        if serializer.validated_data["image"].size > 5 * 1024 * 1024:
            raise ValidationError("Maximum image size is 5 MB.")
        serializer.save()

    def perform_update(self, serializer):
        if not manages(
            self.request.user,
            serializer.validated_data.get("room", serializer.instance.room).floor.hotel,
        ):
            raise PermissionDenied()
        serializer.save()
