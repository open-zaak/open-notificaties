from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings
from django.utils import timezone
from django.utils.timezone import now

import requests
import requests_mock
from notifications_api_common.models import NotificationsConfig
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase
from vng_api_common.conf.api import BASE_REST_FRAMEWORK
from vng_api_common.tests import JWTAuthMixin

from nrc.api.tasks import execute_notifications
from nrc.datamodel.models import (
    Notificatie,
    NotificatieResponse,
    NotificationTypes,
    ScheduledNotification,
)
from nrc.datamodel.tests.factories import (
    AbonnementFactory,
    FilterFactory,
    FilterGroupFactory,
    KanaalFactory,
)
from nrc.utils.tests.structlog import capture_logs


@override_settings(
    LINK_FETCHER="vng_api_common.mocks.link_fetcher_200",
    LOG_NOTIFICATIONS_IN_DB=True,
    CELERY_TASK_ALWAYS_EAGER=True,
)
class NotificatieTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True
    maxDiff = None

    def test_notificatie_send_success(self):
        """
        test /notificatie POST:
        check if message was send to subscribers callbackUrls

        """
        kanaal = KanaalFactory.create(
            naam="zaken", filters=["bron", "zaaktype", "vertrouwelijkheidaanduiding"]
        )
        abon = AbonnementFactory.create(callback_url="https://example.local/callback")
        filter_group = FilterGroupFactory.create(kanaal=kanaal, abonnement=abon)
        FilterFactory.create(
            filter_group=filter_group, key="bron", value="082096752011"
        )
        notificatie_url = reverse(
            "notificaties-list",
            kwargs={"version": BASE_REST_FRAMEWORK["DEFAULT_VERSION"]},
        )
        msg = {
            "kanaal": "zaken",
            "source": "zaken.maykin.nl",
            "hoofdObject": "https://example.com/zrc/api/v1/zaken/d7a22",
            "resource": "status",
            "resourceUrl": "https://example.com/zrc/api/v1/statussen/d7a22/721c9",
            "actie": "create",
            "aanmaakdatum": "2025-01-01T12:00:00Z",
            "kenmerken": {
                "bron": "082096752011",
                "zaaktype": "example.com/api/v1/zaaktypen/5aa5c",
                "vertrouwelijkheidaanduiding": "openbaar",
            },
        }

        with requests_mock.mock() as m:
            m.post(abon.callback_url, status_code=204)

            with capture_logs() as cap_logs:
                response = self.client.post(notificatie_url, msg)
                execute_notifications.run()

            notification_received = next(
                log for log in cap_logs if log["event"] == "notification_received"
            )
            notification_successful = next(
                log for log in cap_logs if log["event"] == "notification_successful"
            )
            notification_id = Notificatie.objects.last().pk

            self.assertEqual(
                notification_received,
                {
                    **notification_received,
                    **{
                        "action": "create",
                        "additional_attributes": {
                            "bron": "082096752011",
                            "zaaktype": "example.com/api/v1/zaaktypen/5aa5c",
                            "vertrouwelijkheidaanduiding": "openbaar",
                        },
                        "channel_name": "zaken",
                        "creation_date": "2025-01-01T12:00:00Z",
                        "event": "notification_received",
                        "log_level": "info",
                        "main_object_url": "https://example.com/zrc/api/v1/zaken/d7a22",
                        "resource": "status",
                        "resource_url": "https://example.com/zrc/api/v1/statussen/d7a22/721c9",
                        "user_id": None,
                    },
                },
            )
            self.assertEqual(
                notification_successful,
                {
                    **notification_successful,
                    **{
                        "action": "create",
                        "additional_attributes": {
                            "bron": "082096752011",
                            "zaaktype": "example.com/api/v1/zaaktypen/5aa5c",
                            "vertrouwelijkheidaanduiding": "openbaar",
                        },
                        "channel_name": "zaken",
                        "creation_date": "2025-01-01T12:00:00Z",
                        "event": "notification_successful",
                        "log_level": "info",
                        "main_object_url": "https://example.com/zrc/api/v1/zaken/d7a22",
                        "notification_id": notification_id,
                        "resource": "status",
                        "resource_url": "https://example.com/zrc/api/v1/statussen/d7a22/721c9",
                        "subscription_callback": abon.callback_url,
                        "subscription_pk": abon.pk,
                    },
                },
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(Notificatie.objects.count(), 1)

        self.assertEqual(m.last_request.url, abon.callback_url)
        self.assertEqual(m.last_request.json(), msg)
        self.assertEqual(m.last_request.headers["Content-Type"], "application/json")
        self.assertEqual(m.last_request.headers["Authorization"], abon.auth)

    @patch("nrc.api.tasks.get_exponential_backoff_interval", MagicMock(return_value=0))
    def test_notificatie_send_failure(self):
        """
        check that notification_failed log is emitted if the callback returns a non
        success status code
        """
        kanaal = KanaalFactory.create(
            naam="zaken", filters=["bron", "zaaktype", "vertrouwelijkheidaanduiding"]
        )
        abon = AbonnementFactory.create(callback_url="https://example.local/callback")
        filter_group = FilterGroupFactory.create(kanaal=kanaal, abonnement=abon)
        FilterFactory.create(
            filter_group=filter_group, key="bron", value="082096752011"
        )
        notificatie_url = reverse(
            "notificaties-list",
            kwargs={"version": BASE_REST_FRAMEWORK["DEFAULT_VERSION"]},
        )
        msg = {
            "kanaal": "zaken",
            "source": "zaken.maykin.nl",
            "hoofdObject": "https://example.com/zrc/api/v1/zaken/d7a22",
            "resource": "status",
            "resourceUrl": "https://example.com/zrc/api/v1/statussen/d7a22/721c9",
            "actie": "create",
            "aanmaakdatum": "2025-01-01T12:00:00Z",
            "kenmerken": {
                "bron": "082096752011",
                "zaaktype": "example.com/api/v1/zaaktypen/5aa5c",
                "vertrouwelijkheidaanduiding": "openbaar",
            },
        }

        with requests_mock.mock() as m:
            m.post(
                abon.callback_url,
                status_code=400,
                json={"error": "Something went wrong"},
            )

            with capture_logs() as cap_logs:
                response = self.client.post(notificatie_url, msg)
                execute_notifications.run()
                execute_notifications.run()

            notification_received = next(
                log for log in cap_logs if log["event"] == "notification_received"
            )
            error_logs = (
                log for log in cap_logs if log["event"] == "notification_failed"
            )
            notification_failed = next(error_logs)
            retry_notification_failed = next(error_logs)
            notification_id = Notificatie.objects.last().pk

            self.assertEqual(
                notification_received,
                {
                    **notification_received,
                    **{
                        "action": "create",
                        "additional_attributes": {
                            "bron": "082096752011",
                            "zaaktype": "example.com/api/v1/zaaktypen/5aa5c",
                            "vertrouwelijkheidaanduiding": "openbaar",
                        },
                        "channel_name": "zaken",
                        "creation_date": "2025-01-01T12:00:00Z",
                        "event": "notification_received",
                        "log_level": "info",
                        "main_object_url": "https://example.com/zrc/api/v1/zaken/d7a22",
                        "resource": "status",
                        "resource_url": "https://example.com/zrc/api/v1/statussen/d7a22/721c9",
                        "user_id": None,
                    },
                },
            )
            self.assertEqual(
                notification_failed,
                {
                    **notification_failed,
                    **{
                        "action": "create",
                        "additional_attributes": {
                            "bron": "082096752011",
                            "zaaktype": "example.com/api/v1/zaaktypen/5aa5c",
                            "vertrouwelijkheidaanduiding": "openbaar",
                        },
                        "channel_name": "zaken",
                        "creation_date": "2025-01-01T12:00:00Z",
                        "event": "notification_failed",
                        "http_status_code": 400,
                        "notification_attempt_count": 1,
                        "log_level": "warning",
                        "main_object_url": "https://example.com/zrc/api/v1/zaken/d7a22",
                        "notification_id": notification_id,
                        "resource": "status",
                        "resource_url": "https://example.com/zrc/api/v1/statussen/d7a22/721c9",
                        "subscription_callback": abon.callback_url,
                        "subscription_pk": abon.pk,
                    },
                },
            )
            self.assertEqual(retry_notification_failed["notification_attempt_count"], 2)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(Notificatie.objects.count(), 1)

        self.assertEqual(m.last_request.url, abon.callback_url)
        self.assertEqual(m.last_request.json(), msg)
        self.assertEqual(m.last_request.headers["Content-Type"], "application/json")
        self.assertEqual(m.last_request.headers["Authorization"], abon.auth)

    @patch("nrc.api.tasks.get_exponential_backoff_interval", MagicMock(return_value=0))
    def test_notificatie_send_request_exception(self):
        """
        check that notification_failed log is emitted if the callback returns a non
        success status code
        """
        kanaal = KanaalFactory.create(
            naam="zaken", filters=["bron", "zaaktype", "vertrouwelijkheidaanduiding"]
        )
        abon = AbonnementFactory.create(callback_url="https://example.local/callback")
        filter_group = FilterGroupFactory.create(kanaal=kanaal, abonnement=abon)
        FilterFactory.create(
            filter_group=filter_group, key="bron", value="082096752011"
        )
        notificatie_url = reverse(
            "notificaties-list",
            kwargs={"version": BASE_REST_FRAMEWORK["DEFAULT_VERSION"]},
        )
        msg = {
            "kanaal": "zaken",
            "source": "zaken.maykin.nl",
            "hoofdObject": "https://example.com/zrc/api/v1/zaken/d7a22",
            "resource": "status",
            "resourceUrl": "https://example.com/zrc/api/v1/statussen/d7a22/721c9",
            "actie": "create",
            "aanmaakdatum": "2025-01-01T12:00:00Z",
            "kenmerken": {
                "bron": "082096752011",
                "zaaktype": "example.com/api/v1/zaaktypen/5aa5c",
                "vertrouwelijkheidaanduiding": "openbaar",
            },
        }

        exc = requests.exceptions.ConnectTimeout("Timeout exception")
        with requests_mock.mock() as m:
            m.post(abon.callback_url, exc=exc)

            with capture_logs() as cap_logs:
                response = self.client.post(notificatie_url, msg)
                execute_notifications.run()
                execute_notifications.run()

            notification_received = next(
                log for log in cap_logs if log["event"] == "notification_received"
            )
            error_logs = (
                log for log in cap_logs if log["event"] == "notification_error"
            )
            notification_error = next(error_logs)
            retry_notification_error = next(error_logs)
            notification_id = Notificatie.objects.last().pk

            self.assertEqual(
                notification_received,
                {
                    **notification_received,
                    **{
                        "action": "create",
                        "additional_attributes": {
                            "bron": "082096752011",
                            "zaaktype": "example.com/api/v1/zaaktypen/5aa5c",
                            "vertrouwelijkheidaanduiding": "openbaar",
                        },
                        "channel_name": "zaken",
                        "creation_date": "2025-01-01T12:00:00Z",
                        "event": "notification_received",
                        "log_level": "info",
                        "main_object_url": "https://example.com/zrc/api/v1/zaken/d7a22",
                        "resource": "status",
                        "resource_url": "https://example.com/zrc/api/v1/statussen/d7a22/721c9",
                        "user_id": None,
                    },
                },
            )
            self.assertEqual(
                notification_error,
                {
                    **notification_error,
                    **{
                        "action": "create",
                        "additional_attributes": {
                            "bron": "082096752011",
                            "zaaktype": "example.com/api/v1/zaaktypen/5aa5c",
                            "vertrouwelijkheidaanduiding": "openbaar",
                        },
                        "channel_name": "zaken",
                        "creation_date": "2025-01-01T12:00:00Z",
                        "event": "notification_error",
                        "exc_info": exc,
                        "notification_attempt_count": 1,
                        "log_level": "error",
                        "main_object_url": "https://example.com/zrc/api/v1/zaken/d7a22",
                        "notification_id": notification_id,
                        "resource": "status",
                        "resource_url": "https://example.com/zrc/api/v1/statussen/d7a22/721c9",
                        "subscription_callback": abon.callback_url,
                        "subscription_pk": abon.pk,
                    },
                },
            )
            self.assertEqual(retry_notification_error["notification_attempt_count"], 2)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(Notificatie.objects.count(), 1)

        self.assertEqual(m.last_request.url, abon.callback_url)
        self.assertEqual(m.last_request.json(), msg)
        self.assertEqual(m.last_request.headers["Content-Type"], "application/json")
        self.assertEqual(m.last_request.headers["Authorization"], abon.auth)

    def test_notificatie_for_abonnement_without_filter_group_does_not_work(self):
        """
        test /notificatie POST:
        verify that having an Abonnement without filtergroup results in no notificaties
        being sent to that subscriber

        """
        KanaalFactory.create(
            naam="zaken", filters=["bron", "zaaktype", "vertrouwelijkheidaanduiding"]
        )
        abon = AbonnementFactory.create(callback_url="https://example.com/callback")

        notificatie_url = reverse(
            "notificaties-list",
            kwargs={"version": BASE_REST_FRAMEWORK["DEFAULT_VERSION"]},
        )
        msg = {
            "kanaal": "zaken",
            "source": "zaken.maykin.nl",
            "hoofdObject": "https://example.com/zrc/api/v1/zaken/d7a22",
            "resource": "status",
            "resourceUrl": "https://example.com/zrc/api/v1/statussen/d7a22/721c9",
            "actie": "create",
            "aanmaakdatum": "2025-01-01T12:00:00Z",
            "kenmerken": {
                "bron": "082096752011",
                "zaaktype": "example.com/api/v1/zaaktypen/5aa5c",
                "vertrouwelijkheidaanduiding": "openbaar",
            },
        }

        with requests_mock.mock() as m:
            m.post(abon.callback_url, status_code=204)

            response = self.client.post(notificatie_url, msg)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(Notificatie.objects.count(), 1)
        self.assertEqual(len(m.request_history), 0)

        # mock_task.assert_not_called()

    def test_notificatie_send_inconsistent_kenmerken(self):
        """
        test /notificatie POST:
        send message with kenmekren inconsistent with kanaal filters
        check if response contains status 400

        """
        kanaal = KanaalFactory.create(naam="zaken")
        abon = AbonnementFactory.create(callback_url="https://example.com/callback")
        filter_group = FilterGroupFactory.create(kanaal=kanaal, abonnement=abon)
        FilterFactory.create(
            filter_group=filter_group, key="bron", value="082096752011"
        )
        notificatie_url = reverse(
            "notificaties-list",
            kwargs={"version": BASE_REST_FRAMEWORK["DEFAULT_VERSION"]},
        )
        request_data = {
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

        with requests_mock.mock() as m:
            m.post(abon.callback_url, status_code=204)

            response = self.client.post(notificatie_url, request_data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        validation_error = response.data["kenmerken"][0]
        self.assertEqual(validation_error.code, "kenmerken_inconsistent")
        self.assertEqual(len(m.request_history), 0)

    def test_notificatie_send_empty_kenmerk_value(self):
        """
        test /notificatie POST:
        check if message was send to subscribers callbackUrls

        """
        kanaal = KanaalFactory.create(
            naam="zaken", filters=["bron", "zaaktype", "vertrouwelijkheidaanduiding"]
        )
        abon = AbonnementFactory.create(callback_url="https://example.com/callback")
        filter_group = FilterGroupFactory.create(kanaal=kanaal, abonnement=abon)
        FilterFactory.create(filter_group=filter_group, key="bron", value="")
        notificatie_url = reverse(
            "notificaties-list",
            kwargs={"version": BASE_REST_FRAMEWORK["DEFAULT_VERSION"]},
        )
        msg = {
            "kanaal": "zaken",
            "source": "zaken.maykin.nl",
            "hoofdObject": "https://example.com/zrc/api/v1/zaken/d7a22",
            "resource": "status",
            "resourceUrl": "https://example.com/zrc/api/v1/statussen/d7a22/721c9",
            "actie": "create",
            "aanmaakdatum": "2025-01-01T12:00:00Z",
            "kenmerken": {
                "bron": "",
                "zaaktype": "example.com/api/v1/zaaktypen/5aa5c",
                "vertrouwelijkheidaanduiding": "openbaar",
            },
        }

        with requests_mock.mock() as m:
            m.post(abon.callback_url, status_code=204)

            response = self.client.post(notificatie_url, msg)
            execute_notifications.run()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(Notificatie.objects.count(), 1)

        self.assertEqual(len(m.request_history), 1)
        self.assertEqual(m.last_request.url, abon.callback_url)
        self.assertEqual(m.last_request.json(), msg)
        self.assertEqual(m.last_request.headers["Content-Type"], "application/json")
        self.assertEqual(m.last_request.headers["Authorization"], abon.auth)

    def test_objects_api_sent_notification(self):
        """
        Regression test for https://github.com/open-zaak/open-notificaties/issues/171
        Check that notifications.kenmerken in camelcase match Abonnement.filters in snake_case
        """
        object_kanaal = KanaalFactory.create(naam="objecten", filters=["object_type"])
        abon1 = AbonnementFactory.create(
            callback_url="https://example.com/callback1"
        )  # should receive
        abon2 = AbonnementFactory.create(
            callback_url="https://example.com/callback2"
        )  # shouldn't receive
        filter_group1 = FilterGroupFactory.create(
            kanaal=object_kanaal, abonnement=abon1
        )
        filter_group2 = FilterGroupFactory.create(
            kanaal=object_kanaal, abonnement=abon2
        )
        FilterFactory.create(
            filter_group=filter_group1,
            key="object_type",
            value="https://example.com/objecttypes/api/v2/objecttypes/0686234f-776f-42f5-b1b9-6e1aecbebab0",
        )
        FilterFactory.create(
            filter_group=filter_group2,
            key="object_type",
            value="https://example.com/objecttypes/api/v2/objecttypes/4523c63b-daaf-4fd1-8ae4-bf9239d05769",
        )
        notificatie_url = reverse(
            "notificaties-list",
            kwargs={"version": BASE_REST_FRAMEWORK["DEFAULT_VERSION"]},
        )
        msg = {
            "kanaal": "objecten",
            "source": "objecten.maykin.nl",
            "hoofdObject": "http://example.com/objects/api/v2/objects/4523c63b-daaf-4fd1-8ae4-bf9239d05769",
            "resource": "object",
            "resourceUrl": "http://example.com/objects/api/v2/objects/4523c63b-daaf-4fd1-8ae4-bf9239d05769",
            "actie": "create",
            "aanmaakdatum": "2025-01-01T12:00:00Z",
            "kenmerken": {
                "objectType": "https://example.com/objecttypes/api/v2/objecttypes/0686234f-776f-42f5-b1b9-6e1aecbebab0"
            },
        }

        with requests_mock.mock() as m:
            m.post(abon1.callback_url, status_code=204)

            response = self.client.post(notificatie_url, msg)
            execute_notifications.run()

        self.assertEqual(NotificatieResponse.objects.count(), 1)

        notif_response = NotificatieResponse.objects.get()

        self.assertEqual(notif_response.response_status, 204)
        self.assertEqual(notif_response.exception, "")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(Notificatie.objects.count(), 1)
        self.assertEqual(len(m.request_history), 1)
        self.assertEqual(m.last_request.url, abon1.callback_url)
        self.assertEqual(m.last_request.json(), msg)
        self.assertEqual(m.last_request.headers["Content-Type"], "application/json")
        self.assertEqual(m.last_request.headers["Authorization"], abon1.auth)

    def test_notificatie_send_success_as_cloudevent(self):
        kanaal = KanaalFactory.create(
            naam="zaken", filters=["bron", "zaaktype", "vertrouwelijkheidaanduiding"]
        )
        abon = AbonnementFactory.create(
            callback_url="https://example.local/callback", send_cloudevents=True
        )
        FilterGroupFactory.create(kanaal=kanaal, abonnement=abon)

        notificatie_url = reverse(
            "notificaties-list",
            kwargs={"version": BASE_REST_FRAMEWORK["DEFAULT_VERSION"]},
        )

        msg = {
            "kanaal": "zaken",
            "source": "zaken.maykin.nl",
            "hoofdObject": "https://example.com/zrc/api/v1/zaken/d7a22",
            "resource": "status",
            "resourceUrl": "https://example.com/zrc/api/v1/statussen/d7a22/721c9",
            "actie": "create",
            "aanmaakdatum": "2025-01-01T12:00:00Z",
            "kenmerken": {
                "bron": "082096752011",
                "zaaktype": "example.com/api/v1/zaaktypen/5aa5c",
                "vertrouwelijkheidaanduiding": "openbaar",
            },
        }

        with requests_mock.mock() as m:
            m.post(abon.callback_url, status_code=204)

            with capture_logs() as cap_logs:
                response = self.client.post(notificatie_url, msg)
                execute_notifications.run()

            notification_received = next(
                log for log in cap_logs if log["event"] == "notification_received"
            )
            cloudevent_successful = next(
                log for log in cap_logs if log["event"] == "cloudevent_successful"
            )

            self.assertFalse(
                any(log["event"] == "notification_successful" for log in cap_logs)
            )

            self.assertEqual(
                notification_received,
                {
                    **notification_received,
                    **{
                        "action": "create",
                        "additional_attributes": {
                            "bron": "082096752011",
                            "zaaktype": "example.com/api/v1/zaaktypen/5aa5c",
                            "vertrouwelijkheidaanduiding": "openbaar",
                        },
                        "channel_name": "zaken",
                        "creation_date": "2025-01-01T12:00:00Z",
                        "event": "notification_received",
                        "log_level": "info",
                        "main_object_url": "https://example.com/zrc/api/v1/zaken/d7a22",
                        "resource": "status",
                        "resource_url": "https://example.com/zrc/api/v1/statussen/d7a22/721c9",
                        "user_id": None,
                    },
                },
            )
            self.assertEqual(
                cloudevent_successful,
                {
                    **cloudevent_successful,
                    **{
                        "source": "zaken.maykin.nl",
                        "type": "nl.overheid.zaken.status.create",
                        "subject": "721c9",
                        "log_level": "info",
                    },
                },
            )

            self.assertEqual(
                response.status_code, status.HTTP_201_CREATED, response.data
            )
            self.assertEqual(Notificatie.objects.count(), 1)

            self.assertEqual(m.last_request.url, abon.callback_url)
            expected_cloudevent = {
                "id": m.last_request.json()["id"],
                "source": "zaken.maykin.nl",
                "specversion": "1.0",
                "type": "nl.overheid.zaken.status.create",
                "datacontenttype": "application/json",
                "subject": "721c9",
                "time": "2025-01-01T12:00:00Z",
                "data": {
                    "hoofdObject": "https://example.com/zrc/api/v1/zaken/d7a22",
                    "bron": "082096752011",
                    "zaaktype": "example.com/api/v1/zaaktypen/5aa5c",
                    "vertrouwelijkheidaanduiding": "openbaar",
                },
            }
            self.assertEqual(m.last_request.json(), expected_cloudevent)
            self.assertEqual(
                m.last_request.headers["Content-Type"], "application/cloudevents+json"
            )
            self.assertEqual(m.last_request.headers["Authorization"], abon.auth)

    @patch("nrc.api.tasks.get_exponential_backoff_interval", MagicMock(return_value=0))
    def test_notificatie_send_failure_as_cloudevent(self):
        kanaal = KanaalFactory.create(
            naam="zaken", filters=["bron", "zaaktype", "vertrouwelijkheidaanduiding"]
        )
        abon = AbonnementFactory.create(
            callback_url="https://example.local/callback", send_cloudevents=True
        )
        FilterGroupFactory.create(kanaal=kanaal, abonnement=abon)

        notificatie_url = reverse(
            "notificaties-list",
            kwargs={"version": BASE_REST_FRAMEWORK["DEFAULT_VERSION"]},
        )
        msg = {
            "kanaal": "zaken",
            "source": "zaken.maykin.nl",
            "hoofdObject": "https://example.com/zrc/api/v1/zaken/d7a22",
            "resource": "status",
            "resourceUrl": "https://example.com/zrc/api/v1/statussen/d7a22/721c9",
            "actie": "create",
            "aanmaakdatum": "2025-01-01T12:00:00Z",
            "kenmerken": {
                "bron": "082096752011",
                "zaaktype": "example.com/api/v1/zaaktypen/5aa5c",
                "vertrouwelijkheidaanduiding": "openbaar",
            },
        }

        with requests_mock.mock() as m:
            m.post(
                abon.callback_url,
                status_code=400,
                json={"error": "Something went wrong"},
            )

            with capture_logs() as cap_logs:
                response = self.client.post(notificatie_url, msg)
                execute_notifications.run()
                execute_notifications.run()

            notification_received = next(
                log for log in cap_logs if log["event"] == "notification_received"
            )
            error_logs = (
                log for log in cap_logs if log["event"] == "cloudevent_failed"
            )
            cloudevent_failed = next(error_logs)
            retry_cloudevent_failed = next(error_logs)

            self.assertEqual(
                notification_received,
                {
                    **notification_received,
                    **{
                        "action": "create",
                        "additional_attributes": {
                            "bron": "082096752011",
                            "zaaktype": "example.com/api/v1/zaaktypen/5aa5c",
                            "vertrouwelijkheidaanduiding": "openbaar",
                        },
                        "channel_name": "zaken",
                        "creation_date": "2025-01-01T12:00:00Z",
                        "event": "notification_received",
                        "log_level": "info",
                        "main_object_url": "https://example.com/zrc/api/v1/zaken/d7a22",
                        "resource": "status",
                        "resource_url": "https://example.com/zrc/api/v1/statussen/d7a22/721c9",
                        "user_id": None,
                    },
                },
            )
            self.assertEqual(
                cloudevent_failed,
                {
                    **cloudevent_failed,
                    **{
                        "source": "zaken.maykin.nl",
                        "type": "nl.overheid.zaken.status.create",
                        "subject": "721c9",
                        "log_level": "warning",
                    },
                },
            )
            self.assertEqual(retry_cloudevent_failed["cloudevent_attempt_count"], 2)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(Notificatie.objects.count(), 1)

        self.assertEqual(m.last_request.url, abon.callback_url)
        expected_cloudevent = {
            "id": m.last_request.json()["id"],
            "source": "zaken.maykin.nl",
            "specversion": "1.0",
            "type": "nl.overheid.zaken.status.create",
            "datacontenttype": "application/json",
            "subject": "721c9",
            "time": "2025-01-01T12:00:00Z",
            "data": {
                "hoofdObject": "https://example.com/zrc/api/v1/zaken/d7a22",
                "bron": "082096752011",
                "zaaktype": "example.com/api/v1/zaaktypen/5aa5c",
                "vertrouwelijkheidaanduiding": "openbaar",
            },
        }
        self.assertEqual(m.last_request.json(), expected_cloudevent)
        self.assertEqual(
            m.last_request.headers["Content-Type"], "application/cloudevents+json"
        )
        self.assertEqual(m.last_request.headers["Authorization"], abon.auth)

    @patch("nrc.api.tasks.get_exponential_backoff_interval", MagicMock(return_value=0))
    def test_notificatie_send_request_exception_as_cloudevent(self):
        kanaal = KanaalFactory.create(
            naam="zaken", filters=["bron", "zaaktype", "vertrouwelijkheidaanduiding"]
        )
        abon = AbonnementFactory.create(
            callback_url="https://example.local/callback", send_cloudevents=True
        )
        FilterGroupFactory.create(kanaal=kanaal, abonnement=abon)
        notificatie_url = reverse(
            "notificaties-list",
            kwargs={"version": BASE_REST_FRAMEWORK["DEFAULT_VERSION"]},
        )
        msg = {
            "kanaal": "zaken",
            "source": "zaken.maykin.nl",
            "hoofdObject": "https://example.com/zrc/api/v1/zaken/d7a22",
            "resource": "status",
            "resourceUrl": "https://example.com/zrc/api/v1/statussen/d7a22/721c9",
            "actie": "create",
            "aanmaakdatum": "2025-01-01T12:00:00Z",
            "kenmerken": {
                "bron": "082096752011",
                "zaaktype": "example.com/api/v1/zaaktypen/5aa5c",
                "vertrouwelijkheidaanduiding": "openbaar",
            },
        }

        exc = requests.exceptions.ConnectTimeout("Timeout exception")
        with requests_mock.mock() as m:
            m.post(abon.callback_url, exc=exc)

            with capture_logs() as cap_logs:
                response = self.client.post(notificatie_url, msg)
                execute_notifications.run()
                execute_notifications.run()

            notification_received = next(
                log for log in cap_logs if log["event"] == "notification_received"
            )
            error_logs = (log for log in cap_logs if log["event"] == "cloudevent_error")
            cloudevent_error = next(error_logs)
            retry_cloudevent_error = next(error_logs)

            self.assertEqual(
                notification_received,
                {
                    **notification_received,
                    **{
                        "action": "create",
                        "additional_attributes": {
                            "bron": "082096752011",
                            "zaaktype": "example.com/api/v1/zaaktypen/5aa5c",
                            "vertrouwelijkheidaanduiding": "openbaar",
                        },
                        "channel_name": "zaken",
                        "creation_date": "2025-01-01T12:00:00Z",
                        "event": "notification_received",
                        "log_level": "info",
                        "main_object_url": "https://example.com/zrc/api/v1/zaken/d7a22",
                        "resource": "status",
                        "resource_url": "https://example.com/zrc/api/v1/statussen/d7a22/721c9",
                        "user_id": None,
                    },
                },
            )
            self.assertEqual(
                cloudevent_error,
                {
                    **cloudevent_error,
                    **{
                        "source": "zaken.maykin.nl",
                        "type": "nl.overheid.zaken.status.create",
                        "subject": "721c9",
                        "log_level": "error",
                        "exc_info": exc,
                        "cloudevent_attempt_count": 1,
                    },
                },
            )
            self.assertEqual(retry_cloudevent_error["cloudevent_attempt_count"], 2)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(Notificatie.objects.count(), 1)

        self.assertEqual(m.last_request.url, abon.callback_url)
        expected_cloudevent = {
            "id": m.last_request.json()["id"],
            "source": "zaken.maykin.nl",
            "specversion": "1.0",
            "type": "nl.overheid.zaken.status.create",
            "datacontenttype": "application/json",
            "subject": "721c9",
            "time": "2025-01-01T12:00:00Z",
            "data": {
                "hoofdObject": "https://example.com/zrc/api/v1/zaken/d7a22",
                "bron": "082096752011",
                "zaaktype": "example.com/api/v1/zaaktypen/5aa5c",
                "vertrouwelijkheidaanduiding": "openbaar",
            },
        }
        self.assertEqual(m.last_request.json(), expected_cloudevent)

        self.assertEqual(
            m.last_request.headers["Content-Type"], "application/cloudevents+json"
        )
        self.assertEqual(m.last_request.headers["Authorization"], abon.auth)

    def test_notificatie_without_source(self):
        kanaal = KanaalFactory.create(
            naam="zaken", filters=["bron", "zaaktype", "vertrouwelijkheidaanduiding"]
        )
        abon = AbonnementFactory.create(
            callback_url="https://example.local/callback", send_cloudevents=False
        )
        FilterGroupFactory.create(kanaal=kanaal, abonnement=abon)

        notificatie_url = reverse(
            "notificaties-list",
            kwargs={"version": BASE_REST_FRAMEWORK["DEFAULT_VERSION"]},
        )

        msg = {
            "kanaal": "zaken",
            "hoofdObject": "https://example.com/zrc/api/v1/zaken/d7a22",
            "resource": "status",
            "resourceUrl": "https://example.com/zrc/api/v1/statussen/d7a22/721c9",
            "actie": "create",
            "aanmaakdatum": "2025-01-01T12:00:00Z",
            "kenmerken": {
                "bron": "082096752011",
                "zaaktype": "example.com/api/v1/zaaktypen/5aa5c",
                "vertrouwelijkheidaanduiding": "openbaar",
            },
        }

        with requests_mock.mock() as m:
            m.post(abon.callback_url, status_code=204)

            with self.subTest("no cloudevent sub"):
                with capture_logs() as cap_logs:
                    response = self.client.post(notificatie_url, msg)
                    execute_notifications.run()

                self.assertFalse(any(log["event"] == "no_source" for log in cap_logs))

                self.assertEqual(
                    response.status_code, status.HTTP_201_CREATED, response.data
                )
                self.assertEqual(Notificatie.objects.count(), 1)

                self.assertEqual(m.last_request.url, abon.callback_url)

            with self.subTest("with cloudevent sub"):
                abon.send_cloudevents = True
                abon.save()

                with capture_logs() as cap_logs:
                    response = self.client.post(notificatie_url, msg)
                    execute_notifications.run()

                no_notification_source = next(
                    log for log in cap_logs if log["event"] == "no_notification_source"
                )

                self.assertEqual(
                    no_notification_source,
                    {
                        **no_notification_source,
                        **{
                            "action": "create",
                            "channel_name": "zaken",
                            "event": "no_notification_source",
                            "log_level": "error",
                            "resource": "status",
                            "resource_url": "https://example.com/zrc/api/v1/statussen/d7a22/721c9",
                            "user_id": None,
                        },
                    },
                )

                self.assertEqual(
                    response.status_code, status.HTTP_400_BAD_REQUEST, response.data
                )


@patch("nrc.api.tasks.get_exponential_backoff_interval")
@patch("nrc.api.tasks.NotificationsConfig.get_solo")
@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
class NotificatieRetryTests(TestCase):
    def test_notificatie_retry_use_global_config(
        self, mock_config, mock_get_exponential_backoff
    ):
        """
        Verify that retry variables configured on `NotificationsConfig` override the
        variables from the settings
        """
        mock_config.return_value = NotificationsConfig(
            notification_delivery_max_retries=4,
            notification_delivery_retry_backoff=4,
            notification_delivery_retry_backoff_max=28,
        )

        mock_get_exponential_backoff.return_value = 0

        kanaal = KanaalFactory.create(
            naam="zaken", filters=["bron", "zaaktype", "vertrouwelijkheidaanduiding"]
        )
        abon = AbonnementFactory.create(callback_url="https://example.com/callback")
        filter_group = FilterGroupFactory.create(kanaal=kanaal, abonnement=abon)
        FilterFactory.create(
            filter_group=filter_group, key="bron", value="082096752011"
        )
        msg = {
            "kanaal": "zaken",
            "source": "zaken.maykin.nl",
            "hoofdObject": "https://ref.tst.vng.cloud/zrc/api/v1/zaken/d7a22",
            "resource": "status",
            "resourceUrl": "https://ref.tst.vng.cloud/zrc/api/v1/statussen/d7a22/721c9",
            "actie": "create",
            "aanmaakdatum": now(),
            "kenmerken": {
                "bron": "082096752011",
                "zaaktype": "example.com/api/v1/zaaktypen/5aa5c",
                "vertrouwelijkheidaanduiding": "openbaar",
            },
        }
        scheduled_notif = ScheduledNotification.objects.create(
            type=NotificationTypes.notification,
            task_args=msg,
            execute_after=timezone.now(),
            attempt=1,
        )
        scheduled_notif.subs.add(abon)

        with requests_mock.Mocker() as m:
            m.post(abon.callback_url, status_code=404)
            execute_notifications.run()

        mock_get_exponential_backoff.assert_called_once_with(
            factor=4,
            retries=1,
            maximum=28,
            base=4,
            full_jitter=False,
        )
        self.assertEqual(scheduled_notif.attempt, 1)

    def test_notificatie_retry_loop(self, mock_config, mock_get_exponential_backoff):
        mock_config.return_value = NotificationsConfig(
            notification_delivery_max_retries=4,
            notification_delivery_retry_backoff=4,
            notification_delivery_retry_backoff_max=28,
        )

        mock_get_exponential_backoff.return_value = 0

        kanaal = KanaalFactory.create(
            naam="zaken", filters=["bron", "zaaktype", "vertrouwelijkheidaanduiding"]
        )
        abon1 = AbonnementFactory.create(callback_url="https://example.com/callback")
        abon2 = AbonnementFactory.create(callback_url="https://example2.com/callback")
        filter_group1 = FilterGroupFactory.create(kanaal=kanaal, abonnement=abon1)
        filter_group2 = FilterGroupFactory.create(kanaal=kanaal, abonnement=abon2)
        FilterFactory.create(
            filter_group=filter_group1, key="bron", value="082096752011"
        )
        FilterFactory.create(
            filter_group=filter_group2, key="bron", value="082096752011"
        )
        msg = {
            "kanaal": "zaken",
            "source": "zaken.maykin.nl",
            "hoofdObject": "https://ref.tst.vng.cloud/zrc/api/v1/zaken/d7a22",
            "resource": "status",
            "resourceUrl": "https://ref.tst.vng.cloud/zrc/api/v1/statussen/d7a22/721c9",
            "actie": "create",
            "aanmaakdatum": now(),
            "kenmerken": {
                "bron": "082096752011",
                "zaaktype": "example.com/api/v1/zaaktypen/5aa5c",
                "vertrouwelijkheidaanduiding": "openbaar",
            },
        }
        scheduled_notif = ScheduledNotification.objects.create(
            type=NotificationTypes.notification,
            task_args=msg,
            execute_after=timezone.now(),
            attempt=1,
        )
        scheduled_notif.subs.set([abon1, abon2])

        with requests_mock.Mocker() as m:
            m.post(abon1.callback_url, status_code=404)
            m.post(abon2.callback_url, status_code=200)

            for i in range(1, 4):
                execute_notifications.run()

                mock_get_exponential_backoff.assert_any_call(
                    factor=4,
                    retries=i,
                    maximum=28,
                    base=4,
                    full_jitter=False,
                )
                scheduled_notif.refresh_from_db()
                self.assertEqual(scheduled_notif.attempt, i + 1)
                self.assertEqual(scheduled_notif.subs.count(), 1)

            execute_notifications.run()
            self.assertEqual(ScheduledNotification.objects.count(), 0)
