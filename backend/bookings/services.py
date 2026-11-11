from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rooms.models import Room
from promotions.models import Promotion
from payments.models import Payment
from notifications.models import Notification
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
        room=room, status="confirmed", check_in__lt=end, check_out__gt=start
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
    Payment.objects.create(booking=booking, amount=booking.total)
    Notification.objects.create(
        user=customer,
        title="Reservation confirmed",
        message=f"{room.floor.hotel.name}, room {room.number}, {start} to {end}. Simulated payment approved. Reference: {booking.reference}",
    )
    Notification.objects.create(
        user=room.floor.hotel.owner,
        title="New reservation",
        message=f"Room {room.number} reserved from {start} to {end}.",
    )
    return booking


@transaction.atomic
def cancel(booking_id):
    room_id = Booking.objects.values_list("room_id", flat=True).get(pk=booking_id)
    Room.objects.select_for_update().get(pk=room_id)
    booking = Booking.objects.select_for_update().get(pk=booking_id)
    if booking.status == "cancelled":
        return booking
    if booking.check_in <= timezone.localdate():
        raise ValidationError("Reservations can only be cancelled before check-in day.")
    booking.status = "cancelled"
    booking.save(update_fields=["status"])
    Payment.objects.filter(booking=booking).update(status="refunded")
    Notification.objects.create(
        user=booking.customer,
        title="Reservation cancelled",
        message=f"Reservation {booking.reference} cancelled. Simulated payment refunded.",
    )
    Notification.objects.create(
        user=booking.room.floor.hotel.owner,
        title="Reservation cancelled",
        message=f"Room {booking.room.number}: {booking.check_in} to {booking.check_out}.",
    )
    return booking
