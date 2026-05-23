import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")

app = Celery("savefood")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

# Periodic tasks schedule
app.conf.beat_schedule = {
    "expire-old-listings": {
        "task": "apps.listings.tasks.expire_old_listings",
        "schedule": 900.0,  # 15 minutes
    },
    "cleanup-old-notifications": {
        "task": "apps.notifications.tasks.cleanup_old_notifications",
        "schedule": crontab(hour=2, minute=0),  # Daily 2 AM
    },
    "aggregate-daily-metrics": {
        "task": "apps.analytics.tasks.aggregate_daily_metrics",
        "schedule": crontab(hour=1, minute=0),  # Daily 1 AM
    },
    "auto-cancel-expired-orders": {
        "task": "apps.orders.tasks.auto_cancel_expired_orders",
        "schedule": 600.0,  # 10 minutes
    },
    "process-no-show-orders": {
        "task": "apps.orders.tasks.process_no_show_orders",
        "schedule": 1800.0,  # 30 minutes
    },
    # ── Hybrid support: admin heartbeat monitor ─────────────────────────────
    "monitor-stale-admin-assignments": {
        "task": "chat.monitor_stale_admin_assignments",
        "schedule": 60.0,  # Every 60 seconds
    },
}


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
