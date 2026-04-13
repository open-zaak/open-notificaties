from collections import deque
from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.test import override_settings
from django.utils import timezone

from freezegun import freeze_time
from privates.test import temp_private_root
from rest_framework.test import APITestCase

from nrc.api.tasks import execute_notifications
from nrc.datamodel.models import NotificationTypes, ScheduledNotification
from nrc.datamodel.tests.factories import FilterGroupFactory


@temp_private_root()
@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
class TestScheduling(APITestCase):
    def setUp(self):
        self.data = {
            "kanaal": "zaken",
            "source": "zaken.maykin.nl",
            "hoofdObject": "https://example.com/zrc/api/v1/zaken/d7a22",
            "resource": "status",
            "resourceUrl": "https://example.com/zrc/api/v1/statussen/d7a22/721c9",
            "actie": "create",
            "aanmaakdatum": "2018-01-01T17:00:00Z",
            "kenmerken": {
                "bron": "082096752011",
                "zaaktype": "example.com/api/v1/zaaktypen/5aa5c",
                "vertrouwelijkheidaanduiding": "openbaar",
            },
        }
        FilterGroupFactory.create(kanaal__naam="zaken")

    @freeze_time("01-01-2026")
    def test_selected_notifications(self):
        """
        1: not in progress and can be executed
        2: not in progress and can not yet be executed
        3: in progress and recently executed
        4: in progress and executed a 'long' time ago
        """
        a = ScheduledNotification.objects.create(
            in_progress=False,
            execute_after=timezone.now() - timedelta(seconds=5),
            task_args=self.data,
            attempt=0,
            type=NotificationTypes.notification,
        )

        ScheduledNotification.objects.create(
            in_progress=False,
            execute_after=timezone.now() + timedelta(seconds=5),
            task_args=self.data,
            attempt=0,
            type=NotificationTypes.notification,
        )

        ScheduledNotification.objects.create(
            in_progress=True,
            execute_after=timezone.now() - timedelta(seconds=5),
            task_args=self.data,
            attempt=0,
            type=NotificationTypes.notification,
        )

        b = ScheduledNotification.objects.create(
            in_progress=True,
            execute_after=timezone.now() - timedelta(seconds=500),
            task_args=self.data,
            attempt=0,
            type=NotificationTypes.notification,
        )

        def capture_chord(generator):
            deque(generator, 0)  # this consumes the generator, triggering .s() calls
            return MagicMock()

        with (
            patch("nrc.api.tasks.chord") as mock_chord,
            patch("nrc.api.tasks.handle_result"),
            patch("nrc.api.tasks.send_to_sub") as mock_send_to_sub,
        ):
            mock_chord.side_effect = capture_chord
            execute_notifications.run()

            scheduled_notif_ids = [
                call.args[1] for call in mock_send_to_sub.s.call_args_list
            ]
            self.assertCountEqual(scheduled_notif_ids, [a.id, b.id])

        with (
            patch("nrc.api.tasks.chord") as mock_chord,
            patch("nrc.api.tasks.handle_result"),
            patch("nrc.api.tasks.send_to_sub") as mock_send_to_sub,
        ):
            mock_chord.side_effect = capture_chord
            execute_notifications.run()
            self.assertEqual(mock_send_to_sub.s.call_count, 0)
