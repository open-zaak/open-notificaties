import json
from unittest.mock import patch

from django.test import override_settings

from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase
from vng_api_common.conf.api import BASE_REST_FRAMEWORK
from vng_api_common.tests import JWTAuthMixin

from nrc.cloudevents.models import CloudEventConfig
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
    ZDS_CLIENT_CLASS="vng_api_common.mocks.MockClient",
    LOG_NOTIFICATIONS_IN_DB=True,
)
class NotificatieTests(JWTAuthMixin, APITestCase):

    heeft_alle_autorisaties = True

    def test_notificatie_cloudevent_send_success(self, mock_task):
        """
        test /notificatie POST:
        check if message was send to subscribers callbackUrls

        """
        cloud_event_config = CloudEventConfig.get_solo()
        cloud_event_config.oin = "00000001823288444000"
        cloud_event_config.save()

        kanaal = KanaalFactory.create(
            naam="zaken",
            filters=["bronorganisatie", "zaaktype", "vertrouwelijkheidaanduiding"],
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
            "hoofdObject": "https://ref.tst.vng.cloud/zrc/api/v1/zaken/d7a22",
            "resource": "status",
            "resourceUrl": "https://ref.tst.vng.cloud/zrc/api/v1/statussen/d7a22/721c9",
            "actie": "create",
            "aanmaakdatum": "2021-08-16T15:29:30.833664Z",
            "kenmerken": {
                "bronorganisatie": "082096752011",
                "zaaktype": "https://testserver/api/v1/zaaktypen/5aa5c",
                "vertrouwelijkheidaanduiding": "openbaar",
            },
        }

        response = self.client.post(notificatie_url, msg)

        notifications = Notificatie.objects.all()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(notifications.count(), 1)
        notification = notifications.get()

        expected_cloud_event = {
            "id": notification.id,
            "type": "nl.vng.zgw.zaken.status.create",
            "time": "2021-08-16T15:29:30.833664Z",
            "source": "urn:nld:oin:00000001823288444000:systeem:testserver",
            "data": json.dumps(
                {
                    "actie": "create",
                    "kanaal": "zaken",
                    "resource": "zaakinformatieobject",
                    "kenmerken": {
                        "bronorganisatie": "082096752011",
                        "zaaktype": "https://testserver/api/v1/zaaktypen/5aa5c",
                        "vertrouwelijkheidaanduiding": "openbaar",
                    },
                    "hoofdObject": "https://testserver/zaken/v1/zaken/{UUID}",
                    "resourceUrl": "https://testserver/zaken/v1/statussen/{UUID}",
                    "aanmaakdatum": "2021-08-16T15:29:30.833664Z",
                }
            ),
            "specversion": "1.0",
            "datacontenttype": "application/json",
            "nl.vng.zgw.bronorganisatie": "082096752011",
            "nl.vng.zgw.zaaktype": "https://testserver/api/v1/zaaktypen/5aa5c",
            "nl.vng.zgw.vertrouwelijkheidaanduiding": "openbaar",
        }

        mock_task.assert_called_once()
        self.assertEqual(mock_task.call_args[0][0], abon.id)

        content_args = mock_task.call_args[0][1]
        for key, value in expected_cloud_event.items():
            if key == "data":
                continue

            self.assertEqual(content_args[key], value)

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

        response = self.client.post(notificatie_url, request_data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        validation_error = response.data["kenmerken"][0]
        self.assertEqual(validation_error.code, "kenmerken_inconsistent")
        mock_task.assert_not_called()
