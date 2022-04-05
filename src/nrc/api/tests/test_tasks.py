import json
from unittest.mock import patch

from django.core.serializers.json import DjangoJSONEncoder
from django.utils.translation import gettext as _

import celery
import requests
import requests_mock
from rest_framework.test import APITestCase

from nrc.datamodel.models import NotificatieResponse
from nrc.datamodel.tests.factories import AbonnementFactory, NotificatieFactory

from ..tasks import deliver_message


class NotifCeleryTests(APITestCase):
    def test_notificatie_task_send_abonnement(self):
        """
        test /notificatie POST:
        check if message was send to subscribers callbackUrls

        """
        abon = AbonnementFactory.create()
        notif = NotificatieFactory.create()

        msg = {
            "kanaal": "zaken",
            "hoofdObject": "https://ref.tst.vng.cloud/zrc/api/v1/zaken/d7a22",
            "resource": "status",
            "resourceUrl": "https://ref.tst.vng.cloud/zrc/api/v1/statussen/d7a22/721c9",
            "actie": "create",
            "aanmaakdatum": "2018-01-01T17:00:00Z",
            "kenmerken": {
                "bron": "082096752011",
                "zaaktype": "example.com/api/v1/zaaktypen/5aa5c",
                "vertrouwelijkheidaanduiding": "openbaar",
            },
        }

        with requests_mock.mock() as m:
            m.post(abon.callback_url, status_code=204)

            deliver_message(abon.id, msg, notificatie_id=notif.id)

        self.assertEqual(m.last_request.url, abon.callback_url)
        self.assertEqual(m.last_request.json(), msg)
        self.assertEqual(m.last_request.headers["Content-Type"], "application/json")
        self.assertEqual(m.last_request.headers["Authorization"], abon.auth)

    def test_notificatie_task_log(self):
        """
        test /notificatie POST:
        check if message was send to subscribers callbackUrls

        """
        abon = AbonnementFactory.create()
        notif = NotificatieFactory.create()

        request_data = {
            "kanaal": "zaken",
            "hoofdObject": "https://ref.tst.vng.cloud/zrc/api/v1/zaken/d7a22",
            "resource": "status",
            "resourceUrl": "https://ref.tst.vng.cloud/zrc/api/v1/statussen/d7a22/721c9",
            "actie": "create",
            "aanmaakdatum": "2018-01-01T17:00:00Z",
            "kenmerken": {
                "bron": "082096752011",
                "zaaktype": "example.com/api/v1/zaaktypen/5aa5c",
                "vertrouwelijkheidaanduiding": "openbaar",
            },
        }
        msg = json.dumps(request_data, cls=DjangoJSONEncoder)

        with requests_mock.mock() as m:
            m.post(abon.callback_url, status_code=204)

            deliver_message(abon.id, msg, notificatie_id=notif.id)

        self.assertEqual(NotificatieResponse.objects.count(), 1)

        notif_response = NotificatieResponse.objects.get()

        self.assertEqual(notif_response.response_status, 204)
        self.assertEqual(notif_response.exception, "")

    @patch("nrc.api.tasks.deliver_message.retry")
    def test_notificatie_invalid_response_retry(self, retry_mock):
        """
        Verify that a retry is called when the sending of the notification didn't
        succeed due to an invalid response
        """
        retry_mock.side_effect = celery.exceptions.Retry

        abon = AbonnementFactory.create()
        notif = NotificatieFactory.create()

        request_data = {
            "kanaal": "zaken",
            "hoofdObject": "https://ref.tst.vng.cloud/zrc/api/v1/zaken/d7a22",
            "resource": "status",
            "resourceUrl": "https://ref.tst.vng.cloud/zrc/api/v1/statussen/d7a22/721c9",
            "actie": "create",
            "aanmaakdatum": "2018-01-01T17:00:00Z",
            "kenmerken": {
                "bron": "082096752011",
                "zaaktype": "example.com/api/v1/zaaktypen/5aa5c",
                "vertrouwelijkheidaanduiding": "openbaar",
            },
        }
        msg = json.dumps(request_data, cls=DjangoJSONEncoder)
        error_msg = {"error": "Something went wrong"}

        with requests_mock.mock() as m:
            m.post(abon.callback_url, status_code=400, json=error_msg)

            with self.assertRaises(celery.exceptions.Retry):
                deliver_message(abon.id, msg, notificatie_id=notif.id)

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

        request_data = {
            "kanaal": "zaken",
            "hoofdObject": "https://ref.tst.vng.cloud/zrc/api/v1/zaken/d7a22",
            "resource": "status",
            "resourceUrl": "https://ref.tst.vng.cloud/zrc/api/v1/statussen/d7a22/721c9",
            "actie": "create",
            "aanmaakdatum": "2018-01-01T17:00:00Z",
            "kenmerken": {
                "bron": "082096752011",
                "zaaktype": "example.com/api/v1/zaaktypen/5aa5c",
                "vertrouwelijkheidaanduiding": "openbaar",
            },
        }
        msg = json.dumps(request_data, cls=DjangoJSONEncoder)

        with requests_mock.mock() as m:
            m.post(
                abon.callback_url,
                exc=requests.exceptions.ConnectTimeout("Timeout exception"),
            )

            with self.assertRaises(celery.exceptions.Retry):
                deliver_message(abon.id, msg, notificatie_id=notif.id)

        self.assertEqual(NotificatieResponse.objects.count(), 1)

        notif_response = NotificatieResponse.objects.get()

        self.assertEqual(notif_response.exception, "Timeout exception")
