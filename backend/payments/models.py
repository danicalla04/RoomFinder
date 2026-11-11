import uuid
from django.db import models


class Payment(models.Model):
    booking = models.OneToOneField(
        "bookings.Booking", on_delete=models.PROTECT, related_name="payment"
    )
    reference = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    method = models.CharField(max_length=20, default="simulation")
    status = models.CharField(
        max_length=12,
        choices=[("approved", "Approved"), ("refunded", "Refunded")],
        default="approved",
    )
    created_at = models.DateTimeField(auto_now_add=True)
