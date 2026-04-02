import logging
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Donation

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Donation)
def on_donation_available(sender, instance, created, **kwargs):
    """When a new donation is created/becomes available, notify nearby charities."""
    if created and instance.status == "available":
        from .tasks import notify_nearby_charities
        notify_nearby_charities.delay(str(instance.id))
