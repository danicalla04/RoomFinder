from rest_framework import viewsets
from accounts.permissions import admin
from bookings.serializers import PaymentSerializer
from .models import Payment


class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PaymentSerializer

    def get_queryset(self):
        q = Payment.objects.select_related("booking")
        if admin(self.request.user):
            return q
        if self.request.user.role == "owner":
            return q.filter(booking__room__floor__hotel__owner=self.request.user)
        return q.filter(booking__customer=self.request.user)
