"""
Reusable ViewSet mixins for SaveFood DZ.
"""


class SerializerByActionMixin:
    """
    Mixin that selects a different serializer class based on the current
    ViewSet action. Subclasses should define a `serializer_classes` dict
    mapping action names to serializer classes. Falls back to
    `serializer_class` if the action is not found.

    Example::

        class MyViewSet(SerializerByActionMixin, ModelViewSet):
            serializer_classes = {
                "list": MyListSerializer,
                "retrieve": MyDetailSerializer,
                "create": MyCreateSerializer,
            }
            serializer_class = MyListSerializer  # default fallback
    """

    serializer_classes: dict = {}

    def get_serializer_class(self):
        return self.serializer_classes.get(
            self.action, super().get_serializer_class()
        )


class OwnerQuerySetMixin:
    """
    Mixin that automatically filters the queryset to objects owned by the
    current request user. The owner field name is configurable via the
    `owner_field` attribute (defaults to 'user').

    Example::

        class MyViewSet(OwnerQuerySetMixin, ModelViewSet):
            owner_field = "author"  # Filter by obj.author == request.user
            queryset = MyModel.objects.all()
    """

    owner_field: str = "user"

    def get_queryset(self):
        qs = super().get_queryset()
        filter_kwargs = {self.owner_field: self.request.user}
        return qs.filter(**filter_kwargs)
