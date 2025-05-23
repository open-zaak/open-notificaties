from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils.timezone import now

import requests_mock
from celery.exceptions import Retry
from notifications_api_common.models import NotificationsConfig
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase
from vng_api_common.conf.api import BASE_REST_FRAMEWORK
from vng_api_common.tests import JWTAuthMixin

from nrc.api.tasks import deliver_message
from nrc.datamodel.models import Notificatie
from nrc.datamodel.tests.factories import (
    AbonnementFactory,
    FilterFactory,
    FilterGroupFactory,
    KanaalFactory,
)


@patch("nrc.api.serializers.deliver_message.delay")
@override_settings(
    LINK_FETCHER="vng_api_common.mocks.link_fetcher_200",
    LOG_NOTIFICATIONS_IN_DB=True,
)
class NotificatieTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_notificatie_send_success(self, mock_task):
        """
        test /notificatie POST:
        check if message was send to subscribers callbackUrls

        """
        kanaal = KanaalFactory.create(
            naam="zaken", filters=["bron", "zaaktype", "vertrouwelijkheidaanduiding"]
        )
        abon = AbonnementFactory.create(callback_url="https://example.com/callback")
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
            "hoofdObject": "https://example.com/zrc/api/v1/zaken/d7a22",
            "resource": "status",
            "resourceUrl": "https://example.com/zrc/api/v1/statussen/d7a22/721c9",
            "actie": "create",
            "aanmaakdatum": now(),
            "kenmerken": {
                "bron": "082096752011",
                "zaaktype": "example.com/api/v1/zaaktypen/5aa5c",
                "vertrouwelijkheidaanduiding": "openbaar",
            },
        }

        response = self.client.post(notificatie_url, msg)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(Notificatie.objects.count(), 1)
        mock_task.assert_called_once_with(
            abon.id, msg, notificatie_id=Notificatie.objects.get().id, attempt=1
        )

    def test_notificatie_for_abonnement_without_filter_group_does_not_work(
        self, mock_task
    ):
        """
        test /notificatie POST:
        verify that having an Abonnement without filtergroup results in no notificaties
        being sent to that subscriber

        """
        KanaalFactory.create(
            naam="zaken", filters=["bron", "zaaktype", "vertrouwelijkheidaanduiding"]
        )
        AbonnementFactory.create(callback_url="https://example.com/callback")

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
            "aanmaakdatum": now(),
            "kenmerken": {
                "bron": "082096752011",
                "zaaktype": "example.com/api/v1/zaaktypen/5aa5c",
                "vertrouwelijkheidaanduiding": "openbaar",
            },
        }

        response = self.client.post(notificatie_url, msg)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(Notificatie.objects.count(), 1)
        mock_task.assert_not_called()

    def test_notificatie_send_inconsistent_kenmerken(self, mock_task):
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

        response = self.client.post(notificatie_url, request_data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        validation_error = response.data["kenmerken"][0]
        self.assertEqual(validation_error.code, "kenmerken_inconsistent")
        mock_task.assert_not_called()

    def test_notificatie_send_empty_kenmerk_value(self, mock_task):
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
            "hoofdObject": "https://example.com/zrc/api/v1/zaken/d7a22",
            "resource": "status",
            "resourceUrl": "https://example.com/zrc/api/v1/statussen/d7a22/721c9",
            "actie": "create",
            "aanmaakdatum": now(),
            "kenmerken": {
                "bron": "",
                "zaaktype": "example.com/api/v1/zaaktypen/5aa5c",
                "vertrouwelijkheidaanduiding": "openbaar",
            },
        }

        response = self.client.post(notificatie_url, msg)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(Notificatie.objects.count(), 1)
        mock_task.assert_called_once_with(
            abon.id, msg, notificatie_id=Notificatie.objects.get().id, attempt=1
        )

    def test_objects_api_sent_notification(self, mock_task):
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
            "hoofdObject": "http://example.com/objects/api/v2/objects/4523c63b-daaf-4fd1-8ae4-bf9239d05769",
            "resource": "object",
            "resourceUrl": "http://example.com/objects/api/v2/objects/4523c63b-daaf-4fd1-8ae4-bf9239d05769",
            "actie": "create",
            "aanmaakdatum": now(),
            "kenmerken": {
                "objectType": "https://example.com/objecttypes/api/v2/objecttypes/0686234f-776f-42f5-b1b9-6e1aecbebab0"
            },
        }

        response = self.client.post(notificatie_url, msg)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(Notificatie.objects.count(), 1)
        mock_task.assert_called_once_with(
            abon1.id, msg, notificatie_id=Notificatie.objects.get().id, attempt=1
        )


@patch("notifications_api_common.autoretry.get_exponential_backoff_interval")
@patch("notifications_api_common.autoretry.NotificationsConfig.get_solo")
@patch("nrc.api.serializers.deliver_message.retry")
class NotificatieRetryTests(TestCase):
    def test_notificatie_retry_use_global_config(
        self, mock_retry, mock_config, mock_get_exponential_backoff
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

        mock_retry.side_effect = Retry()
        with requests_mock.Mocker() as m:
            m.post(abon.callback_url, status_code=404)
            with self.assertRaises(Retry):
                deliver_message(abon.id, msg)

        mock_get_exponential_backoff.assert_called_once_with(
            factor=4,
            retries=0,
            maximum=28,
            full_jitter=False,
        )
        self.assertEqual(deliver_message.max_retries, 4)
