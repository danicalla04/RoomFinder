from rest_framework import serializers
from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    booking = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Notification
        fields = ["id", "title", "message", "booking", "read", "created_at"]
        read_only_fields = ["title", "message", "created_at"]
