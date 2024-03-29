from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from ...models import Notificatie


class Command(BaseCommand):
    def handle(self, **options):
        date_limit = timezone.now() - timedelta(
            days=settings.NOTIFICATION_NUMBER_OF_DAYS_RETAINED
        )

        notifications_filtered = Notificatie.objects.filter(
            forwarded_msg__aanmaakdatum__lt=date_limit
        ).delete()

        self.stdout.write(
            str(notifications_filtered[0])
            + " notifications have been deleted : "
            + str(notifications_filtered[1])
        )
