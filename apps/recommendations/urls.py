from rest_framework.routers import DefaultRouter

from apps.recommendations.views import RecommendationViewSet

router = DefaultRouter()
router.register(
    "recommendations",
    RecommendationViewSet,
    basename="recommendations",
)

urlpatterns = router.urls
