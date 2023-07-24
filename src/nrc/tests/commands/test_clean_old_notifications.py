from datetime import datetime, timedelta

from django.core.management import call_command
from django.test import TestCase, override_settings

from nrc.datamodel.models import Notificatie, NotificatieResponse
from nrc.datamodel.tests.factories import (
    KanaalFactory,
    NotificatieFactory,
    NotificatieResponseFactory,
)


class CleanOldNotificationsTests(TestCase):
    @override_settings(NOTIFICATION_NUMBER_OF_DAYS_RETAINED=30)
    def setUp(self) -> None:
        self.kanaal = KanaalFactory.create(
            naam="zaken", filters=["bron", "zaaktype", "vertrouwelijkheidaanduiding"]
        )

        in_month = (datetime.now() - timedelta(days=25)).strftime(
            "%Y-%m-%dT%H:%M:%S.%fZ"
        )
        data = {"aanmaakdatum": in_month}
        self.notif_in_month = NotificatieFactory.create(
            forwarded_msg=data, kanaal=self.kanaal
        )

        out_month = (datetime.now() - timedelta(days=35)).strftime(
            "%Y-%m-%dT%H:%M:%S.%fZ"
        )
        data2 = {"aanmaakdatum": out_month}
        self.notif_out_month = NotificatieFactory.create(forwarded_msg=data2)

        self.notif_response_in_month = NotificatieResponseFactory.create(
            notificatie=self.notif_in_month
        )
        self.notif_response_out_month = NotificatieResponseFactory.create(
            notificatie=self.notif_out_month
        )

    def test_objects_are_deleted(self):
        self.assertEqual(Notificatie.objects.count(), 2)
        self.assertEqual(NotificatieResponse.objects.count(), 2)

        call_command("clean_old_notifications")

        self.assertEqual(Notificatie.objects.count(), 1)
        self.assertEqual(NotificatieResponse.objects.count(), 1)

        self.assertEqual(Notificatie.objects.last(), self.notif_in_month)
        self.assertEqual(
            NotificatieResponse.objects.last(), self.notif_response_in_month
        )

    @override_settings(NOTIFICATION_NUMBER_OF_DAYS_RETAINED=60)
    def test_change_of_period(self):
        self.assertEqual(Notificatie.objects.count(), 2)

        call_command("clean_old_notifications")

        self.assertEqual(Notificatie.objects.count(), 2)
        self.assertEqual(Notificatie.objects.last(), self.notif_out_month)
        self.assertEqual(Notificatie.objects.first(), self.notif_in_month)

        self.assertEqual(NotificatieResponse.objects.count(), 2)
        self.assertEqual(
            NotificatieResponse.objects.last(), self.notif_response_out_month
        )
        self.assertEqual(
            NotificatieResponse.objects.first(), self.notif_response_in_month
        )
