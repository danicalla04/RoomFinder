from rest_framework import viewsets, mixins
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from .models import Review
from .serializers import ReviewSerializer


class ReviewViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        q = Review.objects.filter(
            booking__room__floor__hotel__status="verified"
        ).select_related("booking__customer", "booking__room__floor")
        if self.request.query_params.get("hotel"):
            q = q.filter(
                booking__room__floor__hotel_id=self.request.query_params["hotel"]
            )
        return q
