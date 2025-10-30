from unittest.mock import patch
from uuid import uuid4

from django.test import override_settings
from django.utils import timezone

import requests
import requests_mock
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase
from vng_api_common.conf.api import BASE_REST_FRAMEWORK
from vng_api_common.tests import JWTAuthMixin

from nrc.datamodel.models import CloudEvent
from nrc.datamodel.tests.factories import (
    AbonnementFactory,
    CloudEventFilterGroupFactory,
)
from nrc.utils.tests.structlog import capture_logs


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    LINK_FETCHER="vng_api_common.mocks.link_fetcher_200",
    LOG_NOTIFICATIONS_IN_DB=True,
)
class CloudEventTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True
    maxDiff = None

    def test_cloudevent_send_success(self):
        """
        test /notificatie POST:
        check if message was send to subscribers callbackUrls

        """
        abon = AbonnementFactory.create(callback_url="https://example.local/callback")
        CloudEventFilterGroupFactory.create(
            type_substring="nl.overheid.zaken",
            abonnement=abon,
        )
        cloudevent_url = reverse(
            "cloudevent-list",
            kwargs={"version": BASE_REST_FRAMEWORK["DEFAULT_VERSION"]},
        )

        event_id = str(uuid4())
        subject_id = str(uuid4())

        event = {
            "specversion": "1.0",
            "type": "nl.overheid.zaken.zaak.created",
            "source": "oz",
            "subject": subject_id,
            "id": event_id,
            "time": timezone.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "datacontenttype": "application/json",
            "data": {},
        }

        with requests_mock.mock() as m:
            m.post(abon.callback_url, status_code=204)
            with capture_logs() as cap_logs:
                response = self.client.post(
                    cloudevent_url,
                    event,
                    headers={"content-type": "application/cloudevents+json"},
                )

            cloudevent_received = next(
                log for log in cap_logs if log["event"] == "cloudevent_received"
            )
            cloudevent_successful = next(
                log for log in cap_logs if log["event"] == "cloudevent_successful"
            )
            self.assertEqual(
                cloudevent_received,
                {
                    **cloudevent_received,
                    **{
                        "id": event_id,
                        "source": "oz",
                        "type": "nl.overheid.zaken.zaak.created",
                        "subject": subject_id,
                        "log_level": "info",
                    },
                },
            )
            self.assertEqual(
                cloudevent_successful,
                {
                    **cloudevent_successful,
                    **{
                        "id": event_id,
                        "source": "oz",
                        "type": "nl.overheid.zaken.zaak.created",
                        "subject": subject_id,
                        "log_level": "info",
                    },
                },
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(CloudEvent.objects.count(), 1)

        self.assertEqual(m.last_request.url, abon.callback_url)
        self.assertEqual(m.last_request.json(), event)
        self.assertEqual(
            m.last_request.headers["Content-Type"], "application/cloudevents+json"
        )

        self.assertEqual(m.last_request.headers["Authorization"], abon.auth)

    def test_cloudevent_send_failure(self):
        """
        check that cloudevent_failed log is emitted if the callback returns a non
        success status code
        """

        abon = AbonnementFactory.create(callback_url="https://example.local/callback")
        CloudEventFilterGroupFactory.create(
            type_substring="nl.overheid.zaken",
            abonnement=abon,
        )
        cloudevent_url = reverse(
            "cloudevent-list",
            kwargs={"version": BASE_REST_FRAMEWORK["DEFAULT_VERSION"]},
        )

        event_id = str(uuid4())
        subject_id = str(uuid4())
        time = timezone.now()
        event = {
            "specversion": "1.0",
            "type": "nl.overheid.zaken.zaak.created",
            "source": "oz",
            "subject": subject_id,
            "id": event_id,
            "time": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "datacontenttype": "application/json",
            "data": {},
        }

        with requests_mock.mock() as m:
            m.post(
                abon.callback_url,
                status_code=400,
                json={"error": "Something went wrong"},
            )

            with capture_logs() as cap_logs:
                response = self.client.post(
                    cloudevent_url,
                    event,
                    headers={"content-type": "application/cloudevents+json"},
                )

            cloudevent_received = next(
                log for log in cap_logs if log["event"] == "cloudevent_received"
            )
            error_logs = (
                log for log in cap_logs if log["event"] == "cloudevent_failed"
            )
            cloudevent_failed = next(error_logs)
            retry_cloudevent_failed = next(error_logs)

            self.assertEqual(
                cloudevent_received,
                {
                    **cloudevent_received,
                    **{
                        "id": event_id,
                        "source": "oz",
                        "type": "nl.overheid.zaken.zaak.created",
                        "subject": subject_id,
                        "log_level": "info",
                    },
                },
            )
            self.assertEqual(
                cloudevent_failed,
                {
                    **cloudevent_failed,
                    **{
                        "id": event_id,
                        "source": "oz",
                        "type": "nl.overheid.zaken.zaak.created",
                        "subject": subject_id,
                        "log_level": "warning",
                    },
                },
            )
            self.assertEqual(retry_cloudevent_failed["task_attempt_count"], 2)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(CloudEvent.objects.count(), 1)

        self.assertEqual(m.last_request.url, abon.callback_url)
        self.assertEqual(m.last_request.json(), event)
        self.assertEqual(
            m.last_request.headers["Content-Type"], "application/cloudevents+json"
        )
        self.assertEqual(m.last_request.headers["Authorization"], abon.auth)

    def test_cloudevent_send_request_exception(self):
        """
        check that cloudevent_failed log is emitted if the callback returns a non
        success status code
        """
        abon = AbonnementFactory.create(callback_url="https://example.local/callback")
        CloudEventFilterGroupFactory.create(
            type_substring="nl.overheid.zaken",
            abonnement=abon,
        )
        cloudevent_url = reverse(
            "cloudevent-list",
            kwargs={"version": BASE_REST_FRAMEWORK["DEFAULT_VERSION"]},
        )

        event_id = str(uuid4())
        subject_id = str(uuid4())
        time = timezone.now()
        event = {
            "specversion": "1.0",
            "type": "nl.overheid.zaken.zaak.created",
            "source": "oz",
            "subject": subject_id,
            "id": event_id,
            "time": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "datacontenttype": "application/json",
            "data": {},
        }

        exc = requests.exceptions.ConnectTimeout("Timeout exception")
        with requests_mock.mock() as m:
            m.post(abon.callback_url, exc=exc)

            with capture_logs() as cap_logs:
                response = self.client.post(
                    cloudevent_url,
                    event,
                    headers={"content-type": "application/cloudevents+json"},
                )

            cloudevent_received = next(
                log for log in cap_logs if log["event"] == "cloudevent_received"
            )
            error_logs = (log for log in cap_logs if log["event"] == "cloudevent_error")
            cloudevent_error = next(error_logs)
            retry_cloudevent_error = next(error_logs)

            self.assertEqual(
                cloudevent_received,
                {
                    **cloudevent_received,
                    **{
                        "id": event_id,
                        "source": "oz",
                        "type": "nl.overheid.zaken.zaak.created",
                        "subject": subject_id,
                        "log_level": "info",
                    },
                },
            )
            self.assertEqual(
                cloudevent_error,
                {
                    **cloudevent_error,
                    **{
                        "id": event_id,
                        "source": "oz",
                        "type": "nl.overheid.zaken.zaak.created",
                        "subject": subject_id,
                        "log_level": "error",
                        "exc_info": exc,
                        "cloudevent_attempt_count": 1,
                        "task_attempt_count": 1,
                    },
                },
            )
            self.assertEqual(retry_cloudevent_error["task_attempt_count"], 2)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(CloudEvent.objects.count(), 1)

        self.assertEqual(m.last_request.url, abon.callback_url)
        self.assertEqual(m.last_request.json(), event)
        self.assertEqual(
            m.last_request.headers["Content-Type"], "application/cloudevents+json"
        )
        self.assertEqual(m.last_request.headers["Authorization"], abon.auth)

    @patch("nrc.api.tasks.deliver_cloudevent.delay")
    def test_correct_subs_get_cloudevent(self, mock_delay):
        cloudevent_url = reverse(
            "cloudevent-list",
            kwargs={"version": BASE_REST_FRAMEWORK["DEFAULT_VERSION"]},
        )
        event = {
            "specversion": "1.0",
            "type": "nl.overheid.zaken.zaak.created",
            "source": "oz",
            "subject": str(uuid4()),
            "id": str(uuid4()),
            "time": timezone.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "datacontenttype": "application/json",
            "data": "{}",
        }

        abon1 = AbonnementFactory.create(callback_url="https://example.local/abon1")
        abon2 = AbonnementFactory.create(callback_url="https://example.local/abon2")
        abon3 = AbonnementFactory.create(callback_url="https://example.local/abon3")

        CloudEventFilterGroupFactory.create(
            type_substring="nl.overheid.zaken",
            abonnement=abon1,
        )
        CloudEventFilterGroupFactory.create(
            type_substring="nl.overheid",
            abonnement=abon1,
        )

        CloudEventFilterGroupFactory.create(
            type_substring="nl",
            abonnement=abon1,
        )

        CloudEventFilterGroupFactory.create(
            type_substring="nl.overheid.besluiten",
            abonnement=abon2,
        )
        CloudEventFilterGroupFactory.create(
            type_substring="nl.overheid",
            abonnement=abon2,
        )

        CloudEventFilterGroupFactory.create(
            type_substring="uk",
            abonnement=abon2,
        )

        CloudEventFilterGroupFactory.create(
            type_substring="test",
            abonnement=abon3,
        )

        with requests_mock.mock() as m:
            m.post(abon1.callback_url, status_code=204)
            m.post(abon2.callback_url, status_code=204)
            m.post(abon3.callback_url, status_code=204)

            response = self.client.post(
                cloudevent_url,
                event,
                headers={"Content-Type": "application/cloudevents+json"},
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(CloudEvent.objects.count(), 1)
        self.assertEqual(mock_delay.call_count, 2)

        sub_ids = [args[0][0] for args in mock_delay.call_args_list]
        self.assertEqual(sub_ids, [abon1.id, abon2.id])

    def test_data(self):
        abon = AbonnementFactory.create(callback_url="https://example.local/callback")
        CloudEventFilterGroupFactory.create(
            type_substring="nl.overheid.zaken",
            abonnement=abon,
        )
        cloudevent_url = reverse(
            "cloudevent-list",
            kwargs={"version": BASE_REST_FRAMEWORK["DEFAULT_VERSION"]},
        )
        event = {
            "specversion": "1.0",
            "type": "nl.overheid.zaken.zaak.created",
            "source": "oz",
            "subject": str(uuid4()),
            "id": str(uuid4()),
            "time": timezone.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

        with requests_mock.mock() as m:
            m.post(abon.callback_url, status_code=204)

            with self.subTest("xml str"):
                id = str(uuid4())
                xml_event = event | {
                    "datacontenttype": "application/xml",
                    "data": '<much wow="xml"/>',
                    "id": id,
                }
                response = self.client.post(
                    cloudevent_url,
                    xml_event,
                    headers={"content-type": "application/cloudevents+json"},
                )
                self.assertEqual(
                    response.status_code, status.HTTP_201_CREATED, response.data
                )
                self.assertEqual(
                    CloudEvent.objects.get(id=id).data, '<much wow="xml"/>'
                )
                self.assertEqual(m.last_request.json(), xml_event)

            with self.subTest("null"):
                id = str(uuid4())
                null_event = event | {
                    "datacontenttype": "application/json",
                    "data": None,
                    "id": id,
                }
                response = self.client.post(
                    cloudevent_url,
                    null_event,
                    headers={"content-type": "application/cloudevents+json"},
                )
                self.assertEqual(
                    response.status_code, status.HTTP_201_CREATED, response.data
                )
                self.assertEqual(CloudEvent.objects.get(id=id).data, "null")
                self.assertEqual(m.last_request.json(), null_event)

            with self.subTest("data omitted"):
                id = str(uuid4())
                omitted_data_event = event | {
                    "id": id,
                }
                response = self.client.post(
                    cloudevent_url,
                    omitted_data_event,
                    headers={"content-type": "application/cloudevents+json"},
                )
                self.assertEqual(
                    response.status_code, status.HTTP_201_CREATED, response.data
                )
                self.assertEqual(CloudEvent.objects.get(id=id).data, None)
                self.assertEqual(m.last_request.json(), omitted_data_event)
