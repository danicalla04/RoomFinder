from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        CUSTOMER = "customer", "Customer"
        OWNER = "owner", "Hotel owner"
        ADMIN = "admin", "Administrator"

    class OwnerApproval(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    role = models.CharField(max_length=10, choices=Role.choices, default=Role.CUSTOMER)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=30, blank=True)
    owner_approval_status = models.CharField(
        max_length=10, choices=OwnerApproval.choices, default=OwnerApproval.APPROVED
    )
