from unittest.mock import MagicMock, patch
from uuid import uuid4

from django.test import override_settings
from django.utils import timezone

import requests
import requests_mock
from freezegun import freeze_time
from rest_framework import status
from rest_framework.reverse import reverse_lazy
from rest_framework.test import APITestCase
from vng_api_common.conf.api import BASE_REST_FRAMEWORK
from vng_api_common.tests import JWTAuthMixin

from nrc.api.tasks import execute_notifications
from nrc.datamodel.models import CloudEvent
from nrc.datamodel.tests.factories import (
    AbonnementFactory,
    CloudEventFilterFactory,
    CloudEventFilterGroupFactory,
)
from nrc.utils.tests.structlog import capture_logs


@override_settings(
    LINK_FETCHER="vng_api_common.mocks.link_fetcher_200",
    LOG_NOTIFICATIONS_IN_DB=True,
    CELERY_TASK_ALWAYS_EAGER=True,
)
@freeze_time("2025-01-01T12:00:00")
class CloudEventTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True
    maxDiff = None
    cloudevent_url = reverse_lazy(
        "cloudevent-list",
        kwargs={"version": BASE_REST_FRAMEWORK["DEFAULT_VERSION"]},
    )

    def test_cloudevent_send_success(self):
        """
        check if message was send to subscribers callbackUrls
        """
        abon = AbonnementFactory.create(
            callback_url="https://example.local/callback", send_cloudevents=True
        )
        CloudEventFilterGroupFactory.create(
            type_substring="nl.overheid.zaken",
            abonnement=abon,
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
                    self.cloudevent_url,
                    event,
                    headers={"content-type": "application/cloudevents+json"},
                )
                execute_notifications.run()

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

    def test_cloudevent_send_to_subscriptions_with_additional_filters(self):
        """
        check if message was send to subscribers callbackUrls, based on configured filters
        """
        abon_no_filters = AbonnementFactory.create(
            callback_url="https://example.local/callback1", send_cloudevents=True
        )
        CloudEventFilterGroupFactory.create(
            type_substring="nl.overheid.zaken",
            abonnement=abon_no_filters,
        )

        abon_matching_filter = AbonnementFactory.create(
            callback_url="https://example.local/callback2", send_cloudevents=True
        )
        CloudEventFilterFactory.create(
            cloud_event_filter_group__type_substring="nl.overheid.zaken",
            cloud_event_filter_group__abonnement=abon_matching_filter,
            key="vertrouwelijkheidaanduiding",
            value="zeer_geheim",
        )

        abon_non_matching_filter = AbonnementFactory.create(
            callback_url="https://example.local/callback3", send_cloudevents=True
        )
        filter_group = CloudEventFilterGroupFactory.create(
            type_substring="nl.overheid.zaken",
            abonnement=abon_non_matching_filter,
        )
        CloudEventFilterFactory.create(
            cloud_event_filter_group=filter_group,
            key="vertrouwelijkheidaanduiding",
            value="openbaar",
        )
        CloudEventFilterFactory.create(
            cloud_event_filter_group=filter_group,
            key="other_key",
            value="no_match",
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
            "data": {"vertrouwelijkheidaanduiding": "zeer_geheim"},
        }

        with requests_mock.mock() as m:
            m.post(abon_no_filters.callback_url, status_code=204)
            m.post(abon_matching_filter.callback_url, status_code=204)
            with capture_logs() as cap_logs:
                response = self.client.post(
                    self.cloudevent_url,
                    event,
                    headers={"content-type": "application/cloudevents+json"},
                )
                execute_notifications.run()

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

        # Requests must be sent to abonnementen that have no explicit filters defined
        # and to abonnement for which the defined filters match
        self.assertEqual(len(m.request_history), 2)

        request1, request2 = m.request_history

        self.assertEqual(request1.url, abon_no_filters.callback_url)
        self.assertEqual(request1.json(), event)
        self.assertEqual(
            request1.headers["Content-Type"], "application/cloudevents+json"
        )
        self.assertEqual(request1.headers["Authorization"], abon_no_filters.auth)
        self.assertEqual(request2.url, abon_matching_filter.callback_url)
        self.assertEqual(request2.json(), event)
        self.assertEqual(
            request2.headers["Content-Type"], "application/cloudevents+json"
        )
        self.assertEqual(request2.headers["Authorization"], abon_matching_filter.auth)

    def test_cloudevent_subscription_with_filters_but_no_data_defined_on_event(self):
        """
        if a subscription has filters defined, but the incoming event does not have
        values in `data`, the event will still be forwarded to the subscription
        """
        abon = AbonnementFactory.create(
            callback_url="https://example.local/callback", send_cloudevents=True
        )
        filter_group = CloudEventFilterGroupFactory.create(
            type_substring="nl.overheid.zaken",
            abonnement=abon,
        )
        CloudEventFilterFactory.create(
            cloud_event_filter_group=filter_group,
            key="vertrouwelijkheidaanduiding",
            value="openbaar",
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
                    self.cloudevent_url,
                    event,
                    headers={"content-type": "application/cloudevents+json"},
                )
                execute_notifications.run()

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

    @patch("nrc.api.tasks.get_exponential_backoff_interval", MagicMock(return_value=0))
    def test_cloudevent_send_failure(self):
        """
        check that cloudevent_failed log is emitted if the callback returns a non
        success status code
        """

        abon = AbonnementFactory.create(
            callback_url="https://example.local/callback", send_cloudevents=True
        )
        CloudEventFilterGroupFactory.create(
            type_substring="nl.overheid.zaken",
            abonnement=abon,
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
                    self.cloudevent_url,
                    event,
                    headers={"content-type": "application/cloudevents+json"},
                )
                execute_notifications.run()
                execute_notifications.run()

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
            self.assertEqual(retry_cloudevent_failed["cloudevent_attempt_count"], 2)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(CloudEvent.objects.count(), 1)

        self.assertEqual(m.last_request.url, abon.callback_url)
        self.assertEqual(m.last_request.json(), event)
        self.assertEqual(
            m.last_request.headers["Content-Type"], "application/cloudevents+json"
        )
        self.assertEqual(m.last_request.headers["Authorization"], abon.auth)

    @patch("nrc.api.tasks.get_exponential_backoff_interval", MagicMock(return_value=0))
    def test_cloudevent_send_request_exception(self):
        """
        check that cloudevent_failed log is emitted if the callback returns a non
        success status code
        """
        abon = AbonnementFactory.create(
            callback_url="https://example.local/callback", send_cloudevents=True
        )
        CloudEventFilterGroupFactory.create(
            type_substring="nl.overheid.zaken",
            abonnement=abon,
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
                    self.cloudevent_url,
                    event,
                    headers={"content-type": "application/cloudevents+json"},
                )
                execute_notifications.run()
                execute_notifications.run()

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
                    },
                },
            )
            self.assertEqual(retry_cloudevent_error["cloudevent_attempt_count"], 2)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(CloudEvent.objects.count(), 1)

        self.assertEqual(m.last_request.url, abon.callback_url)
        self.assertEqual(m.last_request.json(), event)
        self.assertEqual(
            m.last_request.headers["Content-Type"], "application/cloudevents+json"
        )
        self.assertEqual(m.last_request.headers["Authorization"], abon.auth)

    @patch("nrc.api.tasks.chord")
    def test_correct_subs_get_cloudevent(self, mock_chord):
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

        abon1 = AbonnementFactory.create(
            callback_url="https://example.local/abon1", send_cloudevents=True
        )
        abon2 = AbonnementFactory.create(
            callback_url="https://example.local/abon2", send_cloudevents=True
        )
        abon3 = AbonnementFactory.create(
            callback_url="https://example.local/abon3", send_cloudevents=True
        )

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
                self.cloudevent_url,
                event,
                headers={"Content-Type": "application/cloudevents+json"},
            )
            execute_notifications.run()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(CloudEvent.objects.count(), 1)

        signatures = list(mock_chord.call_args_list[0][0][0])
        subs = [signature.args[0] for signature in signatures]
        self.assertCountEqual(subs, [abon1.id, abon2.id])

    def test_data(self):
        abon = AbonnementFactory.create(
            callback_url="https://example.local/callback", send_cloudevents=True
        )
        CloudEventFilterGroupFactory.create(
            type_substring="nl.overheid.zaken",
            abonnement=abon,
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
                    self.cloudevent_url,
                    xml_event,
                    headers={"content-type": "application/cloudevents+json"},
                )
                execute_notifications.run()

                self.assertEqual(
                    response.status_code, status.HTTP_201_CREATED, response.data
                )
                self.assertEqual(
                    CloudEvent.objects.get(id=id).data, '<much wow="xml"/>'
                )
                self.assertEqual(m.last_request.json(), xml_event)

            with self.subTest("none"):
                id = str(uuid4())
                null_event = event | {
                    "datacontenttype": "application/json",
                    "data": None,
                    "id": id,
                }
                response = self.client.post(
                    self.cloudevent_url,
                    null_event,
                    headers={"content-type": "application/cloudevents+json"},
                )
                execute_notifications.run()
                self.assertEqual(
                    response.status_code, status.HTTP_201_CREATED, response.data
                )
                self.assertEqual(CloudEvent.objects.get(id=id).data, None)
                self.assertEqual(m.last_request.json(), null_event)

            with self.subTest("data omitted"):
                id = str(uuid4())
                omitted_data_event = event | {
                    "id": id,
                }
                response = self.client.post(
                    self.cloudevent_url,
                    omitted_data_event,
                    headers={"content-type": "application/cloudevents+json"},
                )
                execute_notifications.run()
                self.assertEqual(
                    response.status_code, status.HTTP_201_CREATED, response.data
                )
                self.assertEqual(CloudEvent.objects.get(id=id).data, None)
                self.assertEqual(m.last_request.json(), omitted_data_event)
