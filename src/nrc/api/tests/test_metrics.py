from unittest.mock import MagicMock, patch

import requests_mock
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.tests import (
    JWTAuthMixin,
    reverse,
)

from nrc.datamodel.tests.factories import KanaalFactory

from ..metrics import (
    abonnement_create_counter,
    kanaal_create_counter,
    notificaties_publish_counter,
)


class NotificatiesMetricsTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    @patch.object(kanaal_create_counter, "add", wraps=kanaal_create_counter.add)
    def test_kanaal_create_counter(self, mock_add: MagicMock):
        response = self.client.post(
            reverse("kanaal-list"),
            {
                "naam": "test-kanaal",
                "documentatieLink": "https://example.com",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        mock_add.assert_called_once_with(1)

    @patch.object(abonnement_create_counter, "add", wraps=abonnement_create_counter.add)
    def test_abonnement_create_counter(self, mock_add: MagicMock):
        kanaal = KanaalFactory.create(naam="zaken", filters=["bron", "zaaktype"])
        abonnement_create_url = reverse("abonnement-list")

        data = {
            "callbackUrl": "https://consumer.example.com",
            "auth": "none",
            "kanalen": [
                {
                    "naam": kanaal.naam,
                    "filters": {
                        "bron": "082096752011",
                        "zaaktype": "example.com/api/v1/zaaktypen/1234",
                    },
                }
            ],
        }

        with requests_mock.Mocker() as m:
            m.post("https://consumer.example.com", status_code=204)

            response = self.client.post(abonnement_create_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        mock_add.assert_called_once_with(1)

    @patch.object(
        notificaties_publish_counter, "add", wraps=notificaties_publish_counter.add
    )
    def test_notificatie_publish_counter(self, mock_add: MagicMock):
        kanaal = KanaalFactory.create()

        response = self.client.post(
            reverse("notificaties-list"),
            {
                "kanaal": kanaal.naam,
                "hoofdObject": "https://example.com/object/123",
                "resource": "object",
                "resourceUrl": "https://example.com/object/123",
                "actie": "create",
                "aanmaakdatum": "2024-01-01T12:00:00Z",
                "kenmerken": {},
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        mock_add.assert_called_once_with(1)
