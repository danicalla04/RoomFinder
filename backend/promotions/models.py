from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class Promotion(models.Model):
    hotel = models.ForeignKey(
        "hotels.Hotel", on_delete=models.CASCADE, related_name="promotions"
    )
    code = models.CharField(max_length=32, unique=True)
    percent = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(80)]
    )
    starts_on = models.DateField()
    ends_on = models.DateField()
    active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(ends_on__gte=models.F("starts_on")),
                name="valid_promotion_dates",
            )
        ]
