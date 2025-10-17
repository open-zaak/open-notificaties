import json
import random
import string
from unittest.mock import patch

from django.utils.translation import gettext as _

import celery
import requests
import requests_mock
from rest_framework.test import APITestCase
from structlog.testing import capture_logs

from nrc.api.tasks import NotificationException
from nrc.datamodel.models import NotificatieResponse
from nrc.datamodel.tests.factories import AbonnementFactory, NotificatieFactory

from ..tasks import deliver_cloudevent, deliver_message
from ..types import CloudEventKwargs, SendNotificationTaskKwargs


class NotifCeleryTests(APITestCase):
    @patch("nrc.api.tasks.deliver_message.retry")
    def test_notificatie_invalid_response_retry(self, retry_mock):
        """
        Verify that a retry is called when the sending of the notification didn't
        succeed due to an invalid response
        """
        retry_mock.side_effect = celery.exceptions.Retry

        abon = AbonnementFactory.create()
        notif = NotificatieFactory.create()

        request_data: SendNotificationTaskKwargs = {
            "kanaal": "zaken",
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

        error_msg = {"error": "Something went wrong"}

        with requests_mock.mock() as m:
            m.post(abon.callback_url, status_code=400, json=error_msg)

            with capture_logs() as cap_logs:
                with self.assertRaises(celery.exceptions.Retry):
                    deliver_message(abon.id, request_data, notificatie_id=notif.id)

                self.assertEqual(
                    cap_logs,
                    [
                        {
                            "http_status_code": 400,
                            "notification_attempt_count": 1,
                            "task_attempt_count": 1,
                            "event": "notification_failed",
                            "log_level": "warning",
                        }
                    ],
                )

        self.assertEqual(NotificatieResponse.objects.count(), 1)

        notif_response = NotificatieResponse.objects.get()

        self.assertEqual(
            notif_response.exception,
            _("Could not send notification: status {status_code} - {response}").format(
                status_code=400, response=json.dumps(error_msg)
            ),
        )

    @patch("nrc.api.tasks.deliver_message.retry")
    def test_notificatie_request_exception_retry(self, retry_mock):
        """
        Verify that a retry is called when the sending of the notification didn't
        succeed due to a request exception
        """
        retry_mock.side_effect = celery.exceptions.Retry

        abon = AbonnementFactory.create()
        notif = NotificatieFactory.create()

        request_data: SendNotificationTaskKwargs = {
            "kanaal": "zaken",
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

        exc = requests.exceptions.ConnectTimeout("Timeout exception")
        with requests_mock.mock() as m:
            m.post(
                abon.callback_url,
                exc=exc,
            )

            with capture_logs() as cap_logs:
                with self.assertRaises(celery.exceptions.Retry):
                    deliver_message(abon.id, request_data, notificatie_id=notif.id)

                self.assertEqual(
                    cap_logs,
                    [
                        {
                            "event": "notification_error",
                            "notification_attempt_count": 1,
                            "task_attempt_count": 1,
                            "log_level": "error",
                            "exc_info": exc,
                        }
                    ],
                )

        self.assertEqual(NotificatieResponse.objects.count(), 1)

        notif_response = NotificatieResponse.objects.get()

        self.assertEqual(notif_response.exception, "Timeout exception")

    def test_too_long_exception_message(self):
        """
        Verify that an exception is called when the response of the notification didn't
        succeed due to a too long exception message
        """
        abon = AbonnementFactory.create()
        notif = NotificatieFactory.create()

        request_data: SendNotificationTaskKwargs = {
            "kanaal": "zaken",
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

        str = "".join(random.choice(string.ascii_lowercase) for i in range(1502))

        with requests_mock.mock() as m:
            m.post(abon.callback_url, status_code=400, json=str)

            with self.assertRaises(NotificationException):
                deliver_message(abon.id, request_data, notificatie_id=notif.id)

        self.assertEqual(NotificatieResponse.objects.count(), 1)

        notif_response = NotificatieResponse.objects.get()

        self.assertEqual(len(notif_response.exception), 1000)

    @patch("nrc.api.tasks.deliver_message.retry")
    def test_notificatie_abonnement_does_not_exist(self, retry_mock):
        """
        Verify that an error is logged when the subscription doesn't exist.
        """
        retry_mock.side_effect = celery.exceptions.Retry

        notif = NotificatieFactory.create()

        request_data: SendNotificationTaskKwargs = {
            "kanaal": "zaken",
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

        with capture_logs() as cap_logs:
            deliver_message(-1, request_data, notificatie_id=notif.id)

            self.assertEqual(
                cap_logs,
                [
                    {
                        "event": "subscription_does_not_exist",
                        "log_level": "error",
                    }
                ],
            )

        self.assertEqual(NotificatieResponse.objects.count(), 0)


class CloudEventCeleryTests(APITestCase):
    @patch("nrc.api.tasks.deliver_cloudevent.retry")
    def test_cloudevent_invalid_response_retry(self, retry_mock):
        """
        Verify that a retry is called when the sending of the cloudevent didn't
        succeed due to an invalid response
        """
        retry_mock.side_effect = celery.exceptions.Retry

        abon = AbonnementFactory.create()

        request_data: CloudEventKwargs = {
            "id": "123",
            "source": "oz",
            "specversion": "1.0",
            "type": "nl.overheid.zaken.zaak.updated",
        }

        error_msg = {"error": "Something went wrong"}

        with requests_mock.mock() as m:
            m.post(abon.callback_url, status_code=400, json=error_msg)

            with capture_logs() as cap_logs:
                with self.assertRaises(celery.exceptions.Retry):
                    deliver_cloudevent(abon.id, request_data)

                self.assertEqual(
                    cap_logs,
                    [
                        {
                            "http_status_code": 400,
                            "cloudevent_attempt_count": 1,
                            "task_attempt_count": 1,
                            "event": "cloudevent_failed",
                            "log_level": "warning",
                        }
                    ],
                )

    @patch("nrc.api.tasks.deliver_cloudevent.retry")
    def test_cloudevent_request_exception_retry(self, retry_mock):
        """
        Verify that a retry is called when the sending of the cloudevent didn't
        succeed due to a request exception
        """
        retry_mock.side_effect = celery.exceptions.Retry

        abon = AbonnementFactory.create()

        request_data: CloudEventKwargs = {
            "id": "123",
            "source": "oz",
            "specversion": "1.0",
            "type": "nl.overheid.zaken.zaak.updated",
        }

        exc = requests.exceptions.ConnectTimeout("Timeout exception")
        with requests_mock.mock() as m:
            m.post(
                abon.callback_url,
                exc=exc,
            )

            with capture_logs() as cap_logs:
                with self.assertRaises(celery.exceptions.Retry):
                    deliver_cloudevent(abon.id, request_data)

                self.assertEqual(
                    cap_logs,
                    [
                        {
                            "event": "cloudevent_error",
                            "cloudevent_attempt_count": 1,
                            "task_attempt_count": 1,
                            "log_level": "error",
                            "exc_info": exc,
                        }
                    ],
                )

    @patch("nrc.api.tasks.deliver_cloudevent.retry")
    def test_cloudevent_abonnement_does_not_exist(self, retry_mock):
        """
        Verify that an error is logged when the subscription doesn't exist.
        """
        retry_mock.side_effect = celery.exceptions.Retry

        request_data: CloudEventKwargs = {
            "id": "123",
            "source": "oz",
            "specversion": "1.0",
            "type": "nl.overheid.zaken.zaak.updated",
        }

        with capture_logs() as cap_logs:
            deliver_cloudevent(-1, request_data)

            self.assertEqual(
                cap_logs,
                [
                    {
                        "event": "subscription_does_not_exist",
                        "log_level": "error",
                    }
                ],
            )
