"""
django-filter FilterSet for Listing queries.
"""

import django_filters
from django.contrib.gis.geos import Point

from .models import Category, Listing


class CharInFilter(django_filters.BaseInFilter, django_filters.CharFilter):
    pass
class ListingFilter(django_filters.FilterSet):
    """Filter listings by category, price, grade, location, etc."""
    category = CharInFilter(field_name="category__slug", lookup_expr="in")
    min_price = django_filters.NumberFilter(
        field_name="discounted_price", lookup_expr="gte"
    )
    max_price = django_filters.NumberFilter(
        field_name="discounted_price", lookup_expr="lte"
    )
    freshness_grade = django_filters.CharFilter(lookup_expr="exact")
    status = django_filters.CharFilter(lookup_expr="exact")
    is_donation = django_filters.BooleanFilter()
    merchant = django_filters.UUIDFilter(field_name="merchant__id")
    min_rating = django_filters.NumberFilter(
        field_name="merchant__merchant_profile__average_rating", lookup_expr="gte"
    )
    # Geographic proximity – handled via overridden filter_queryset
    lat = django_filters.NumberFilter(label="Latitude", method="noop")
    lng = django_filters.NumberFilter(label="Longitude", method="noop")
    radius = django_filters.NumberFilter(label="Radius (km)", method="noop")

    def noop(self, queryset, name, value):
        return queryset

    class Meta:
        model = Listing
        fields = [
            "category",
            "min_price",
            "max_price",
            "freshness_grade",
            "status",
            "is_donation",
            "merchant",
        ]

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        data = self.data
        try:
            if "lat" in data and "lng" in data:
                lat = float(data.get("lat"))
                lng = float(data.get("lng"))
                radius_km = float(data.get("radius", 10))
                point = Point(lng, lat, srid=4326)
                return (
                    queryset.nearby(point, radius_km=radius_km)
                    .with_distance(point)
                    .order_by("distance")
                )
        except (TypeError, ValueError):
            pass
        return queryset

