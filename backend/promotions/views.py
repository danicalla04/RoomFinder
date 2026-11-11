from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.exceptions import PermissionDenied
from django.utils import timezone
from django.db.models import Q
from accounts.permissions import admin, manages
from .models import Promotion
from .serializers import PromotionSerializer


class PromotionViewSet(viewsets.ModelViewSet):
    serializer_class = PromotionSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        q = Promotion.objects.select_related("hotel")
        if not admin(self.request.user):
            public = Q(
                active=True,
                hotel__status="verified",
                starts_on__lte=timezone.localdate(),
                ends_on__gte=timezone.localdate(),
            )
            if self.request.user.is_authenticated and self.request.user.role == "owner":
                public |= Q(hotel__owner=self.request.user)
            q = q.filter(public)
        if self.request.query_params.get("hotel"):
            q = q.filter(hotel_id=self.request.query_params["hotel"])
        return q

    def perform_destroy(self, instance):
        if not manages(self.request.user, instance.hotel):
            raise PermissionDenied()
        instance.delete()
