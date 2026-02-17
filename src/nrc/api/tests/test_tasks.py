import json
import random
import string

from django.test import override_settings
from django.utils import timezone
from django.utils.translation import gettext as _

import requests
import requests_mock
from oauthlib.oauth2.rfc6749.errors import OAuth2Error
from privates.test import temp_private_root
from rest_framework.test import APITestCase
from structlog.testing import capture_logs
from zgw_consumers.constants import AuthTypes

from nrc.api.tasks import execute_notifications
from nrc.datamodel.models import (
    NotificatieResponse,
    NotificationTypes,
    ScheduledNotification,
)
from nrc.datamodel.tests.factories import AbonnementFactory, NotificatieFactory

from ..types import CloudEventKwargs, SendNotificationTaskKwargs


@temp_private_root()
@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
class NotifCeleryTests(APITestCase):
    def test_notificatie_invalid_response_retry(self):
        """
        Verify that a ScheduledNotification is created when the sending of the notification didn't
        succeed due to an invalid response
        """

        abon = AbonnementFactory.create()
        notif = NotificatieFactory.create()

        request_data: SendNotificationTaskKwargs = {
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

        scheduled_notif = ScheduledNotification.objects.create(
            type=NotificationTypes.notification,
            task_args=request_data,
            execute_after=timezone.now(),
            notificatie=notif,
            attempt=0,
        )
        scheduled_notif.subs.add(abon)

        error_msg = {"error": "Something went wrong"}

        with requests_mock.mock() as m:
            m.post(abon.callback_url, status_code=400, json=error_msg)

            with capture_logs() as cap_logs:
                execute_notifications.run()

                self.assertEqual(
                    cap_logs,
                    [
                        {
                            "http_status_code": 400,
                            "notification_attempt_count": 1,
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

        self.assertEqual(ScheduledNotification.objects.count(), 1)

        scheduled_notif = ScheduledNotification.objects.get()
        self.assertEqual(scheduled_notif.attempt, 1)
        self.assertEqual(list(scheduled_notif.subs.all()), [abon])

    def test_notificatie_request_exception_retry(self):
        """
        Verify that a ScheduledNotification is created when the sending of the notification didn't
        succeed due to a request exception
        """

        abon = AbonnementFactory.create()
        notif = NotificatieFactory.create()

        request_data: SendNotificationTaskKwargs = {
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

        scheduled_notif = ScheduledNotification.objects.create(
            type=NotificationTypes.notification,
            task_args=request_data,
            execute_after=timezone.now(),
            notificatie=notif,
            attempt=0,
        )
        scheduled_notif.subs.add(abon)

        exc = requests.exceptions.ConnectTimeout("Timeout exception")
        with requests_mock.mock() as m:
            m.post(
                abon.callback_url,
                exc=exc,
            )

            with capture_logs() as cap_logs:
                execute_notifications.run()

                self.assertEqual(
                    cap_logs,
                    [
                        {
                            "event": "notification_error",
                            "notification_attempt_count": 1,
                            "log_level": "error",
                            "exc_info": exc,
                        }
                    ],
                )

        self.assertEqual(NotificatieResponse.objects.count(), 1)

        notif_response = NotificatieResponse.objects.get()

        self.assertEqual(notif_response.exception, "Timeout exception")

        self.assertEqual(ScheduledNotification.objects.count(), 1)

        scheduled_notif = ScheduledNotification.objects.get()
        self.assertEqual(scheduled_notif.attempt, 1)
        self.assertEqual(list(scheduled_notif.subs.all()), [abon])

    def test_too_long_exception_message(self):
        """
        Verify that an exception is called when the response of the notification didn't
        succeed due to a too long exception message
        """
        abon = AbonnementFactory.create()
        notif = NotificatieFactory.create()

        request_data: SendNotificationTaskKwargs = {
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

        scheduled_notif = ScheduledNotification.objects.create(
            type=NotificationTypes.notification,
            task_args=request_data,
            execute_after=timezone.now(),
            notificatie=notif,
            attempt=0,
        )
        scheduled_notif.subs.add(abon)

        str = "".join(random.choice(string.ascii_lowercase) for i in range(1502))

        with requests_mock.mock() as m:
            m.post(abon.callback_url, status_code=400, json=str)

            execute_notifications.run()

        self.assertEqual(NotificatieResponse.objects.count(), 1)

        notif_response = NotificatieResponse.objects.get()

        self.assertEqual(len(notif_response.exception), 1000)

        self.assertEqual(ScheduledNotification.objects.count(), 1)

        scheduled_notif = ScheduledNotification.objects.get()
        self.assertEqual(scheduled_notif.attempt, 1)
        self.assertEqual(list(scheduled_notif.subs.all()), [abon])

    def test_notificatie_oauth2_exception_retry(self):
        """
        Verify that a ScheduledNotification is created when the sending fails due to an OAuth2 error
        """

        abon = AbonnementFactory.create()
        notif = NotificatieFactory.create()

        request_data: SendNotificationTaskKwargs = {
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

        scheduled_notif = ScheduledNotification.objects.create(
            type=NotificationTypes.notification,
            task_args=request_data,
            execute_after=timezone.now(),
            notificatie=notif,
            attempt=0,
        )
        scheduled_notif.subs.add(abon)

        exc = OAuth2Error("invalid_client")
        with requests_mock.Mocker() as m:
            m.post(abon.oauth2_token_url, exc=exc)

            with capture_logs() as cap_logs:
                execute_notifications.run()

                self.assertEqual(
                    cap_logs,
                    [
                        {
                            "event": "notification_error",
                            "notification_attempt_count": 1,
                            "log_level": "error",
                            "exc_info": exc,
                        }
                    ],
                )

        self.assertEqual(NotificatieResponse.objects.count(), 1)
        notif_response = NotificatieResponse.objects.get()
        self.assertEqual(notif_response.exception, str(exc))
        self.assertEqual(ScheduledNotification.objects.count(), 1)

        scheduled_notif = ScheduledNotification.objects.get()
        self.assertEqual(scheduled_notif.attempt, 1)
        self.assertEqual(list(scheduled_notif.subs.all()), [abon])

    def test_deliver_message_api_key_auth(self):
        abon = AbonnementFactory.create(
            auth_type=AuthTypes.api_key,
            auth="ApiKey test-key",
        )
        notif = NotificatieFactory.create()

        request_data: SendNotificationTaskKwargs = {
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

        scheduled_notif = ScheduledNotification.objects.create(
            type=NotificationTypes.notification,
            task_args=request_data,
            execute_after=timezone.now(),
            notificatie=notif,
            attempt=0,
        )
        scheduled_notif.subs.add(abon)

        with requests_mock.mock() as m:
            m.post(abon.callback_url, status_code=204)

            execute_notifications.run()

            self.assertTrue(m.called)
            self.assertEqual(m.call_count, 1)

            last_request = m.last_request
            self.assertEqual(last_request.headers.get("Authorization"), abon.auth)

    def test_deliver_message_zgw_auth(self):
        abon = AbonnementFactory.create(
            auth_type=AuthTypes.zgw,
            client_id="client-id",
            secret="super-secret",
        )
        notif = NotificatieFactory.create()

        request_data: SendNotificationTaskKwargs = {
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

        scheduled_notif = ScheduledNotification.objects.create(
            type=NotificationTypes.notification,
            task_args=request_data,
            execute_after=timezone.now(),
            notificatie=notif,
            attempt=0,
        )
        scheduled_notif.subs.add(abon)

        with requests_mock.mock() as m:
            m.post(abon.callback_url, status_code=204)

            execute_notifications.run()

            self.assertTrue(m.called)
            self.assertEqual(m.call_count, 1)

            last_request = m.last_request
            self.assertTrue(
                last_request.headers.get("Authorization", "").startswith("Bearer ")
            )

    def test_deliver_message_oauth2_auth(self):
        abon = AbonnementFactory.create(
            auth_type=AuthTypes.oauth2_client_credentials,
            client_id="client-id",
            secret="secret",
            oauth2_token_url="https://auth.example/token",
            oauth2_scope="scope",
        )
        notif = NotificatieFactory.create()

        request_data: SendNotificationTaskKwargs = {
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

        scheduled_notif = ScheduledNotification.objects.create(
            type=NotificationTypes.notification,
            task_args=request_data,
            execute_after=timezone.now(),
            notificatie=notif,
            attempt=0,
        )
        scheduled_notif.subs.add(abon)

        with requests_mock.Mocker() as m:
            token = m.post(
                abon.oauth2_token_url,
                json={"access_token": "mock-token", "expires_in": 3600},
            )
            callback = m.post(abon.callback_url, status_code=204)

            execute_notifications.run()

            self.assertTrue(token.called)
            self.assertTrue(callback.called)

            self.assertTrue(
                callback.last_request.headers["Authorization"] == "Bearer mock-token"
            )
            self.assertEqual(len(m.request_history), 2)

    def test_deliver_message_no_cert_specified(self):
        abon = AbonnementFactory.create(
            auth_type=AuthTypes.api_key,
            auth="ApiKey test-key",
        )
        notif = NotificatieFactory.create()

        request_data: SendNotificationTaskKwargs = {
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

        scheduled_notif = ScheduledNotification.objects.create(
            type=NotificationTypes.notification,
            task_args=request_data,
            execute_after=timezone.now(),
            notificatie=notif,
            attempt=0,
        )
        scheduled_notif.subs.add(abon)

        with requests_mock.mock() as m:
            m.post(abon.callback_url, status_code=204)

            execute_notifications.run()

            self.assertTrue(m.called)
            self.assertEqual(m.call_count, 1)

            last_request = m.last_request

            self.assertTrue(last_request.verify)
            self.assertIsNone(last_request.cert)

    def test_deliver_message_client_and_server_cert_specified(self):
        abon = AbonnementFactory.create(
            with_server_cert=True,
            with_client_cert=True,
            auth_type=AuthTypes.api_key,
            auth="ApiKey test-key",
        )
        notif = NotificatieFactory.create()

        request_data: SendNotificationTaskKwargs = {
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

        scheduled_notif = ScheduledNotification.objects.create(
            type=NotificationTypes.notification,
            task_args=request_data,
            execute_after=timezone.now(),
            notificatie=notif,
            attempt=0,
        )
        scheduled_notif.subs.add(abon)

        with requests_mock.mock() as m:
            m.post(abon.callback_url, status_code=204)

            execute_notifications.run()

            self.assertTrue(m.called)
            self.assertEqual(m.call_count, 1)

            last_request = m.last_request

            self.assertEqual(
                last_request.cert,
                abon.client_certificate.public_certificate.path,
            )


@temp_private_root()
@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
class CloudEventCeleryTests(APITestCase):
    def test_cloudevent_invalid_response_retry(self):
        """
        Verify that a ScheduledNotification is called when the sending of the cloudevent didn't
        succeed due to an invalid response
        """

        abon = AbonnementFactory.create(send_cloudevents=True)

        request_data: CloudEventKwargs = {
            "id": "123",
            "source": "oz",
            "specversion": "1.0",
            "type": "nl.overheid.zaken.zaak.updated",
            "subject": "123",
        }

        scheduled_notif = ScheduledNotification.objects.create(
            type=NotificationTypes.cloudevent,
            task_args=request_data,
            execute_after=timezone.now(),
            attempt=0,
        )
        scheduled_notif.subs.add(abon)

        error_msg = {"error": "Something went wrong"}

        with requests_mock.mock() as m:
            m.post(abon.callback_url, status_code=400, json=error_msg)

            with capture_logs() as cap_logs:
                execute_notifications.run()

                self.assertEqual(
                    cap_logs,
                    [
                        {
                            "http_status_code": 400,
                            "cloudevent_attempt_count": 1,
                            "event": "cloudevent_failed",
                            "log_level": "warning",
                        }
                    ],
                )

        self.assertEqual(ScheduledNotification.objects.count(), 1)

    def test_cloudevent_request_exception_retry(self):
        """
        Verify that a ScheduledNotification is called when the sending of the cloudevent didn't
        succeed due to a request exception
        """

        abon = AbonnementFactory.create(send_cloudevents=True)

        request_data: CloudEventKwargs = {
            "id": "123",
            "source": "oz",
            "specversion": "1.0",
            "type": "nl.overheid.zaken.zaak.updated",
            "subject": "123",
        }

        scheduled_notif = ScheduledNotification.objects.create(
            type=NotificationTypes.cloudevent,
            task_args=request_data,
            execute_after=timezone.now(),
            attempt=0,
        )
        scheduled_notif.subs.add(abon)

        exc = requests.exceptions.ConnectTimeout("Timeout exception")
        with requests_mock.mock() as m:
            m.post(
                abon.callback_url,
                exc=exc,
            )

            with capture_logs() as cap_logs:
                execute_notifications.run()

                self.assertEqual(
                    cap_logs,
                    [
                        {
                            "event": "cloudevent_error",
                            "cloudevent_attempt_count": 1,
                            "log_level": "error",
                            "exc_info": exc,
                        }
                    ],
                )
        self.assertEqual(ScheduledNotification.objects.count(), 1)

    def test_cloudevent_oauth2_exception_retry(self):
        """
        Verify that a ScheduledNotification is called when the sending fails due to an OAuth2 error
        """

        abon = AbonnementFactory.create(send_cloudevents=True)

        cloudevent_data: CloudEventKwargs = {
            "id": "123",
            "source": "oz",
            "specversion": "1.0",
            "type": "nl.overheid.zaken.zaak.updated",
            "subject": "123",
        }

        scheduled_notif = ScheduledNotification.objects.create(
            type=NotificationTypes.cloudevent,
            task_args=cloudevent_data,
            execute_after=timezone.now(),
            attempt=0,
        )
        scheduled_notif.subs.add(abon)

        exc = OAuth2Error("invalid_client")

        with requests_mock.Mocker() as m:
            m.post(abon.oauth2_token_url, exc=exc)

            with capture_logs() as cap_logs:
                execute_notifications.run()

                self.assertEqual(
                    cap_logs,
                    [
                        {
                            "event": "cloudevent_error",
                            "cloudevent_attempt_count": 1,
                            "log_level": "error",
                            "exc_info": exc,
                        }
                    ],
                )

    def test_deliver_cloudevent_api_key_auth(self):
        abon = AbonnementFactory.create(
            auth_type=AuthTypes.api_key,
            auth="ApiKey test-key",
            send_cloudevents=True,
        )
        cloudevent_data: CloudEventKwargs = {
            "id": "123",
            "source": "oz",
            "specversion": "1.0",
            "type": "nl.overheid.zaken.zaak.updated",
            "subject": "123",
        }

        scheduled_notif = ScheduledNotification.objects.create(
            type=NotificationTypes.cloudevent,
            task_args=cloudevent_data,
            execute_after=timezone.now(),
            attempt=0,
        )
        scheduled_notif.subs.add(abon)

        with requests_mock.Mocker() as m:
            callback = m.post(abon.callback_url, status_code=204)
            execute_notifications.run()

            self.assertTrue(callback.called)
            self.assertEqual(callback.call_count, 1)

            last_request = callback.last_request
            self.assertEqual(last_request.headers.get("Authorization"), abon.auth)
            self.assertEqual(
                last_request.headers.get("Content-Type"), "application/cloudevents+json"
            )

    def test_deliver_cloudevent_zgw_auth(self):
        abon = AbonnementFactory.create(
            auth_type=AuthTypes.zgw,
            client_id="client-id",
            secret="super-secret",
            send_cloudevents=True,
        )
        cloudevent_data: CloudEventKwargs = {
            "id": "123",
            "source": "oz",
            "specversion": "1.0",
            "type": "nl.overheid.zaken.zaak.updated",
            "subject": "123",
        }

        scheduled_notif = ScheduledNotification.objects.create(
            type=NotificationTypes.cloudevent,
            task_args=cloudevent_data,
            execute_after=timezone.now(),
            attempt=0,
        )
        scheduled_notif.subs.add(abon)

        with requests_mock.Mocker() as m:
            callback = m.post(abon.callback_url, status_code=204)
            execute_notifications.run()

            self.assertTrue(callback.called)
            self.assertEqual(callback.call_count, 1)

            last_request = callback.last_request
            self.assertTrue(
                last_request.headers.get("Authorization", "").startswith("Bearer ")
            )
            self.assertEqual(
                last_request.headers.get("Content-Type"), "application/cloudevents+json"
            )

    def test_deliver_cloudevent_oauth2_auth(self):
        abon = AbonnementFactory.create(
            auth_type=AuthTypes.oauth2_client_credentials,
            client_id="client-id",
            secret="secret",
            oauth2_token_url="https://auth.example/token",
            oauth2_scope="scope",
            send_cloudevents=True,
        )
        cloudevent_data: CloudEventKwargs = {
            "id": "123",
            "source": "oz",
            "specversion": "1.0",
            "type": "nl.overheid.zaken.zaak.updated",
            "subject": "123",
        }

        scheduled_notif = ScheduledNotification.objects.create(
            type=NotificationTypes.cloudevent,
            task_args=cloudevent_data,
            execute_after=timezone.now(),
            attempt=0,
        )
        scheduled_notif.subs.add(abon)

        with requests_mock.Mocker() as m:
            token = m.post(
                abon.oauth2_token_url,
                json={"access_token": "mock-token", "expires_in": 3600},
            )
            callback = m.post(abon.callback_url, status_code=204)
            execute_notifications.run()

            self.assertTrue(token.called)
            self.assertTrue(callback.called)

            last_request = callback.last_request
            self.assertEqual(last_request.headers["Authorization"], "Bearer mock-token")
            self.assertEqual(
                last_request.headers.get("Content-Type"), "application/cloudevents+json"
            )
            self.assertEqual(len(m.request_history), 2)

    def test_deliver_cloudevent_no_cert_specified(self):
        abon = AbonnementFactory.create(
            auth_type=AuthTypes.api_key,
            auth="ApiKey test-key",
        )
        cloudevent_data: CloudEventKwargs = {
            "id": "123",
            "source": "oz",
            "specversion": "1.0",
            "type": "nl.overheid.zaken.zaak.updated",
            "subject": "123",
        }

        scheduled_notif = ScheduledNotification.objects.create(
            type=NotificationTypes.cloudevent,
            task_args=cloudevent_data,
            execute_after=timezone.now(),
            attempt=0,
        )
        scheduled_notif.subs.add(abon)

        with requests_mock.Mocker() as m:
            callback = m.post(abon.callback_url, status_code=204)
            execute_notifications.run()

            self.assertTrue(callback.called)
            self.assertEqual(callback.call_count, 1)

            last_request = callback.last_request

            self.assertTrue(last_request.verify)
            self.assertIsNone(last_request.cert)

    def test_deliver_cloudevent_client_and_server_cert_specified(self):
        abon = AbonnementFactory.create(
            with_server_cert=True,
            with_client_cert=True,
            auth_type=AuthTypes.api_key,
            auth="ApiKey test-key",
        )
        cloudevent_data: CloudEventKwargs = {
            "id": "123",
            "source": "oz",
            "specversion": "1.0",
            "type": "nl.overheid.zaken.zaak.updated",
            "subject": "123",
        }
        scheduled_notif = ScheduledNotification.objects.create(
            type=NotificationTypes.cloudevent,
            task_args=cloudevent_data,
            execute_after=timezone.now(),
            attempt=0,
        )
        scheduled_notif.subs.add(abon)

        with requests_mock.Mocker() as m:
            callback = m.post(abon.callback_url, status_code=204)
            execute_notifications.run()

            self.assertTrue(callback.called)
            self.assertEqual(callback.call_count, 1)

            last_request = callback.last_request

            self.assertEqual(
                last_request.cert,
                abon.client_certificate.public_certificate.path,
            )
