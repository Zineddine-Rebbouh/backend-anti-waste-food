import logging
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="apps.analytics.tasks.aggregate_daily_metrics")
def aggregate_daily_metrics():
    from .services import AnalyticsService
    metrics = AnalyticsService.aggregate_daily_metrics()
    logger.info(f"aggregate_daily_metrics: done for {metrics.date}")
    return str(metrics.date)


@shared_task(name="apps.analytics.tasks.cleanup_old_activity_logs")
def cleanup_old_activity_logs():
    from datetime import timedelta
    from django.utils import timezone
    from .models import UserActivity

    cutoff = timezone.now() - timedelta(days=365)
    deleted_count, _ = UserActivity.objects.filter(created_at__lt=cutoff).delete()
    logger.info(f"cleanup_old_activity_logs: deleted {deleted_count} entries")
    return deleted_count
