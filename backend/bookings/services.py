from datetime import timedelta
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rooms.models import Room
from promotions.models import Promotion
from notifications.models import Notification
from payments.models import Payment
from .models import Booking


@transaction.atomic
def reserve(customer, data):
    room = (
        Room.objects.select_for_update()
        .select_related("floor__hotel")
        .get(pk=data["room"].pk)
    )
    start = data["check_in"]
    end = data["check_out"]
    if not room.active or room.floor.hotel.status != "verified":
        raise ValidationError("This room is no longer available.")
    if data.get("guests", 1) > room.capacity:
        raise ValidationError("Room capacity exceeded.")
    if Booking.objects.filter(
        room=room, status__in=["pending", "confirmed"], check_in__lt=end, check_out__gt=start
    ).exists():
        raise ValidationError(
            "This room is already reserved for those dates. Please choose another room."
        )
    subtotal = room.price * (end - start).days
    discount = Decimal("0.00")
    code = data.get("promotion_code", "").strip().upper()
    if code:
        promo = Promotion.objects.filter(
            code=code,
            hotel=room.floor.hotel,
            active=True,
            starts_on__lte=timezone.localdate(),
            ends_on__gte=timezone.localdate(),
        ).first()
        if not promo:
            raise ValidationError(
                {"promotion_code": "This promotion is invalid or expired."}
            )
        discount = (subtotal * promo.percent / 100).quantize(Decimal("0.01"))
    booking = Booking.objects.create(
        customer=customer,
        room=room,
        check_in=start,
        check_out=end,
        guests=data.get("guests", 1),
        special_requests=data.get("special_requests", ""),
        promotion_code=code,
        total=subtotal - discount,
        discount=discount,
    )
    Notification.objects.create(
        user=customer,
        title="Booking awaiting approval",
        message=f"{room.floor.hotel.name}, room {room.number}, {start} to {end}. Your request is waiting for owner approval. Reference: {booking.reference}",
    )
    Notification.objects.create(
        user=room.floor.hotel.owner,
        title="Booking needs your approval",
        message=f"Room {room.number} requested from {start} to {end}. Approve or reject it in your dashboard.",
    )
    return booking


@transaction.atomic
def cancel(booking_id):
    room_id = Booking.objects.values_list("room_id", flat=True).get(pk=booking_id)
    Room.objects.select_for_update().get(pk=room_id)
    booking = Booking.objects.select_for_update().get(pk=booking_id)
    if booking.status == "cancelled":
        return booking
    if booking.status != "pending":
        raise ValidationError("Confirmed bookings must be cancelled with the owner's approval.")
    if timezone.now() >= booking.created_at + timedelta(hours=2):
        raise ValidationError("The two-hour cancellation window has closed.")
    if booking.check_in <= timezone.localdate():
        raise ValidationError("Reservations can only be cancelled before check-in day.")
    booking.status = "cancelled"
    booking.save(update_fields=["status"])
    Notification.objects.create(
        user=booking.customer,
        title="Reservation cancelled",
        message=f"Reservation {booking.reference} cancelled. The room is available again.",
    )
    Notification.objects.create(
        user=booking.room.floor.hotel.owner,
        title="Reservation cancelled",
        message=f"Room {booking.room.number}: {booking.check_in} to {booking.check_out}. The guest cancelled the booking.",
    )
    return booking


@transaction.atomic
def request_cancellation(booking_id):
    booking = Booking.objects.select_for_update().select_related("room__floor__hotel").get(pk=booking_id)
    if booking.status != "confirmed" or booking.checked_out_at:
        raise ValidationError("Only an active, confirmed booking can request cancellation.")
    if booking.check_out <= timezone.localdate():
        raise ValidationError("Cancellation requests are unavailable after the stay ends.")
    if booking.cancellation_requested_at:
        return booking
    booking.cancellation_requested_at = timezone.now()
    booking.save(update_fields=["cancellation_requested_at"])
    hotel = booking.room.floor.hotel
    Notification.objects.create(
        user=hotel.owner,
        title="Guest requested cancellation",
        message=f"{booking.customer.get_full_name() or booking.customer.username} requested cancellation for room {booking.room.number}, {booking.check_in} to {booking.check_out}. Review it in your dashboard.",
        booking=booking,
    )
    Notification.objects.create(
        user=booking.customer,
        title="Cancellation request sent",
        message=f"Your request to cancel {hotel.name}, room {booking.room.number}, is waiting for the owner. Contact the owner about any refund.",
        booking=booking,
    )
    return booking


@transaction.atomic
def decide_cancellation(booking_id, decision):
    if decision not in ("approved", "rejected"):
        raise ValidationError("Choose approved or rejected.")
    booking = Booking.objects.select_for_update().select_related("customer", "room__floor__hotel").get(pk=booking_id)
    if booking.status != "confirmed" or booking.checked_out_at or not booking.cancellation_requested_at:
        raise ValidationError("There is no pending cancellation request for this booking.")
    hotel = booking.room.floor.hotel
    if decision == "approved":
        booking.status = "cancelled"
        title = "Cancellation approved"
        message = f"The owner approved cancellation of {hotel.name}, room {booking.room.number}. Contact the owner about your refund."
        booking.cancellation_requested_at = None
        booking.save(update_fields=["status", "cancellation_requested_at"])
    else:
        booking.cancellation_requested_at = None
        title = "Cancellation request declined"
        message = f"The owner declined your cancellation request for {hotel.name}, room {booking.room.number}. Message the owner if you have questions."
        booking.save(update_fields=["cancellation_requested_at"])
    Notification.objects.create(user=booking.customer, title=title, message=message, booking=booking)
    return booking


@transaction.atomic
def decide(booking_id, decision, refund_confirmed=False):
    if decision not in ("approved", "rejected"):
        raise ValidationError("Choose approved or rejected.")
    if refund_confirmed and decision != "rejected":
        raise ValidationError("A refund can only be recorded when rejecting a booking.")
    room_id = Booking.objects.values_list("room_id", flat=True).get(pk=booking_id)
    Room.objects.select_for_update().get(pk=room_id)
    booking = Booking.objects.select_for_update().select_related("room__floor__hotel").get(pk=booking_id)
    if booking.status != "pending":
        raise ValidationError("Only pending bookings can be reviewed.")
    if decision == "approved":
        booking.status = "confirmed"
        title = "Booking approved"
        message = f"Your stay at {booking.room.floor.hotel.name}, room {booking.room.number}, is confirmed."
    else:
        booking.status = "rejected"
        title = "Booking declined"
        if refund_confirmed:
            amount = (booking.total / Decimal("2")).quantize(Decimal("0.01"))
            payment, created = Payment.objects.get_or_create(
                booking=booking,
                defaults={"amount": amount, "method": "manual", "status": "refunded"},
            )
            if not created:
                payment.amount = amount
                payment.method = "manual"
                payment.status = "refunded"
                payment.save(update_fields=["amount", "method", "status"])
            message = (
                f"Your booking for room {booking.room.number} was declined. "
                f"The owner marked the {amount} PHP deposit refund as sent outside RoomFinder. "
                "Contact the hotel owner if you have not received it."
            )
        else:
            message = f"Your booking for room {booking.room.number} was declined. The room is available again."
    booking.save(update_fields=["status"])
    Notification.objects.create(user=booking.customer, title=title, message=message)
    return booking


@transaction.atomic
def checkout(booking_id):
    booking = Booking.objects.select_for_update().get(pk=booking_id)
    if booking.status != "confirmed" or timezone.localdate() < booking.check_in:
        raise ValidationError("Check-out is available only after check-in begins on a confirmed stay.")
    if booking.checked_out_at:
        return booking
    booking.checked_out_at = timezone.now()
    booking.save(update_fields=["checked_out_at"])
    Notification.objects.create(
        user=booking.room.floor.hotel.owner,
        title="Guest checked out",
        message=f"Booking {booking.reference}, room {booking.room.number}, was checked out by the guest.",
    )
    return booking
