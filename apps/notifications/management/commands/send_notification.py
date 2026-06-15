from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from apps.notifications.services import NotificationService


class Command(BaseCommand):
    help = "Create and optionally dispatch a notification through the existing notification service."

    def add_arguments(self, parser):
        target = parser.add_mutually_exclusive_group(required=True)
        target.add_argument("--user-id", help="Target a single user UUID.")
        target.add_argument("--user-type", help="Target users by user_type, e.g. consumer, merchant, charity.")
        target.add_argument("--all-users", action="store_true", help="Target every active user.")

        parser.add_argument("--type", default="system", dest="notification_type")
        parser.add_argument("--title", required=True)
        parser.add_argument("--body", required=True)
        parser.add_argument(
            "--channels",
            default="in_app",
            help="Comma-separated channels supported by current backend: in_app,email,sms,push.",
        )
        parser.add_argument("--priority", default="normal")

    def handle(self, *args, **options):
        User = get_user_model()
        channels = [
            channel.strip()
            for channel in options["channels"].split(",")
            if channel.strip()
        ]
        if not channels:
            raise CommandError("At least one channel is required.")

        users = User.objects.filter(is_active=True)
        if options["user_id"]:
            users = users.filter(id=options["user_id"])
        elif options["user_type"]:
            users = users.filter(user_type=options["user_type"])

        sent_count = 0
        user_count = 0
        for user in users.iterator():
            user_count += 1
            notifications = NotificationService.create_and_send(
                recipient_user=user,
                notification_type=options["notification_type"],
                title=options["title"],
                body=options["body"],
                data={"source": "management_command"},
                channels=channels,
                priority=options["priority"],
            )
            sent_count += len(notifications)

        self.stdout.write(
            self.style.SUCCESS(
                f"Created {sent_count} notification record(s) for {user_count} user(s)."
            )
        )
