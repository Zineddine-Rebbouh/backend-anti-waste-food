import logging
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from .models import Review

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Review)
def on_review_save(sender, instance, **kwargs):
    from .services import ReviewService
    ReviewService.update_merchant_rating(instance.merchant)


@receiver(post_delete, sender=Review)
def on_review_delete(sender, instance, **kwargs):
    from .services import ReviewService
    ReviewService.update_merchant_rating(instance.merchant)
