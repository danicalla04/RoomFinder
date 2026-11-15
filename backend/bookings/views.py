from rest_framework import viewsets, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from django.db.models import Prefetch
from django.utils import timezone
from accounts.permissions import admin
from .models import Booking, BookingMessage
from .serializers import BookingSerializer, BookingMessageSerializer
from .services import reserve, cancel, decide, checkout, request_cancellation, decide_cancellation
from notifications.models import Notification


class BookingViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = BookingSerializer

    def get_queryset(self):
        q = Booking.objects.select_related(
            "room__floor__hotel", "customer", "review"
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

    @action(detail=True, methods=["post"])
    def decision(self, request, pk=None):
        booking = self.get_object()
        if booking.room.floor.hotel.owner_id != request.user.pk:
            raise PermissionDenied("Only this hotel's owner may review the booking.")
        return Response(
            self.get_serializer(
                decide(
                    booking.pk,
                    request.data.get("decision"),
                    refund_confirmed=request.data.get("refund_confirmed", False),
                )
            ).data
        )

    @action(detail=True, methods=["post"])
    def checkout(self, request, pk=None):
        booking = self.get_object()
        if booking.customer_id != request.user.pk:
            raise PermissionDenied("Only this guest may check out.")
        return Response(self.get_serializer(checkout(booking.pk)).data)

    @action(detail=True, methods=["post"])
    def request_cancel(self, request, pk=None):
        booking = self.get_object()
        if booking.customer_id != request.user.pk:
            raise PermissionDenied("Only this guest may request cancellation.")
        return Response(self.get_serializer(request_cancellation(booking.pk)).data)

    @action(detail=True, methods=["post"])
    def cancel_decision(self, request, pk=None):
        booking = self.get_object()
        if booking.room.floor.hotel.owner_id != request.user.pk:
            raise PermissionDenied("Only this hotel's owner may review the cancellation request.")
        return Response(self.get_serializer(decide_cancellation(booking.pk, request.data.get("decision"))).data)

    @action(detail=False, methods=["get"], url_path="unread-messages")
    def unread_messages(self, request):
        messages = BookingMessage.objects.filter(read_at__isnull=True).exclude(sender=request.user)
        if request.user.role == "owner":
            messages = messages.filter(booking__room__floor__hotel__owner=request.user)
        elif request.user.role == "customer":
            messages = messages.filter(booking__customer=request.user)
        else:
            return Response({"count": 0})
        return Response({"count": messages.count()})

    @action(detail=False, methods=["get"])
    def conversations(self, request):
        if request.user.role not in ("customer", "owner"):
            return Response([])
        message_order = BookingMessage.objects.select_related("sender").order_by("-created_at", "-id")
        bookings = self.get_queryset().filter(messages__isnull=False).distinct().prefetch_related(
            Prefetch("messages", queryset=message_order, to_attr="ordered_messages")
        )
        rows = []
        for booking in bookings:
            messages = booking.ordered_messages
            latest = messages[0]
            unread = sum(1 for message in messages if message.sender_id != request.user.pk and message.read_at is None)
            row = dict(self.get_serializer(booking).data)
            row["last_message"] = BookingMessageSerializer(latest).data
            row["unread_count"] = unread
            rows.append(row)
        rows.sort(key=lambda row: row["last_message"]["created_at"], reverse=True)
        return Response(rows)

    @action(detail=True, methods=["get", "post"])
    def messages(self, request, pk=None):
        booking = self.get_object()
        owner = booking.room.floor.hotel.owner
        if request.user.pk not in (booking.customer_id, owner.pk):
            raise PermissionDenied("Only this guest and the hotel's owner may use this conversation.")

        if request.method == "GET":
            booking.messages.filter(read_at__isnull=True).exclude(sender=request.user).update(read_at=timezone.now())
            Notification.objects.filter(
                booking=booking,
                user=request.user,
                title__startswith="New message from",
                read=False,
            ).update(read=True)
            messages = booking.messages.select_related("sender").all()
            return Response(BookingMessageSerializer(messages, many=True).data)

        serializer = BookingMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        message = BookingMessage.objects.create(
            booking=booking, sender=request.user, message=serializer.validated_data["message"]
        )
        recipient = booking.customer if request.user.pk == owner.pk else owner
        Notification.objects.create(
            user=recipient,
            title=f"New message from {request.user.get_full_name() or request.user.username}",
            message=f"{request.user.get_full_name() or request.user.username} sent a message about {booking.room.floor.hotel.name}, room {booking.room.number}.",
            booking=booking,
        )
        return Response(BookingMessageSerializer(message).data, status=201)
