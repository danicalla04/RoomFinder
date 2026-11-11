from rest_framework import viewsets, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from accounts.permissions import admin
from .models import Booking
from .serializers import BookingSerializer
from .services import reserve, cancel


class BookingViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = BookingSerializer

    def get_queryset(self):
        q = Booking.objects.select_related(
            "room__floor__hotel", "customer", "payment", "review"
        )
        user = self.request.user
        if admin(user):
            return q
        if user.role == "owner":
            return q.filter(room__floor__hotel__owner=user)
        return q.filter(customer=user)

    def perform_create(self, serializer):
        if self.request.user.role != "customer":
            raise PermissionDenied("Use a customer account to reserve a room.")
        serializer.instance = reserve(self.request.user, serializer.validated_data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        booking = self.get_object()
        if booking.customer_id != request.user.pk and not admin(request.user):
            raise PermissionDenied("Only the customer or administrator may cancel.")
        return Response(self.get_serializer(cancel(booking.pk)).data)
