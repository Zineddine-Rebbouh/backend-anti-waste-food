"""
Base serializers for SaveFood DZ.
"""

from rest_framework import serializers


class TimestampedModelSerializer(serializers.ModelSerializer):
    """
    Base serializer for TimeStampedModel subclasses.
    Automatically sets id, created_at, and updated_at as read-only.
    """

    class Meta:
        read_only_fields = ["id", "created_at", "updated_at"]
