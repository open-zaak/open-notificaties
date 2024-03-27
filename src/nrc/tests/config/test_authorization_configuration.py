from unittest.mock import patch

from django.test import TestCase, override_settings

import requests
import requests_mock
from django_setup_configuration.exceptions import SelfTestFailed
from vng_api_common.authorizations.models import AuthorizationsConfig
from vng_api_common.models import APICredential, JWTSecret
from zgw_consumers.constants import APITypes
from zgw_consumers.test import mock_service_oas_get

from nrc.config.authorization import AuthorizationStep, OpenZaakAuthStep


@override_settings(
    AUTORISATIES_API_ROOT="https://oz.example.com/autorisaties/api/v1/",
    NOTIF_OPENZAAK_CLIENT_ID="notif-client-id",
    NOTIF_OPENZAAK_SECRET="notif-secret",
)
class AuthorizationConfigurationTests(TestCase):
    def test_configure(self):
        configuration = AuthorizationStep()

        configuration.configure()

        config = AuthorizationsConfig.get_solo()
        self.assertEqual(config.api_root, "https://oz.example.com/autorisaties/api/v1/")

        api_credentials = APICredential.objects.get(
            api_root="https://oz.example.com/autorisaties/api/v1/"
        )
        self.assertEqual(api_credentials.client_id, "notif-client-id")
        self.assertEqual(api_credentials.secret, "notif-secret")

    @requests_mock.Mocker()
    def test_selftest_ok(self, m):
        configuration = AuthorizationStep()
        configuration.configure()
        mock_service_oas_get(
            m, "https://oz.example.com/autorisaties/api/v1/", APITypes.ac
        )
        m.get("https://oz.example.com/autorisaties/api/v1/applicaties", json=[])

        configuration.test_configuration()

        self.assertEqual(
            m.last_request.url, "https://oz.example.com/autorisaties/api/v1/applicaties"
        )

    @requests_mock.Mocker()
    def test_selftest_fail(self, m):
        configuration = AuthorizationStep()
        configuration.configure()
        mock_service_oas_get(
            m, "https://oz.example.com/autorisaties/api/v1/", APITypes.ac
        )
        m.get("https://oz.example.com/autorisaties/api/v1/applicaties", json=[])

        configuration.test_configuration()

        self.assertEqual(
            m.last_request.url, "https://oz.example.com/autorisaties/api/v1/applicaties"
        )

    def test_is_configured(self):
        configuration = AuthorizationStep()
        self.assertFalse(configuration.is_configured())

        configuration.configure()

        self.assertTrue(configuration.is_configured())


@override_settings(
    OPENZAAK_NOTIF_CLIENT_ID="oz-client-id",
    OPENZAAK_NOTIF_SECRET="oz-secret",
)
class OpenZaakConfigurationTests(TestCase):
    def test_configure(self):
        configuration = OpenZaakAuthStep()

        configuration.configure()

        jwt_secret = JWTSecret.objects.get(identifier="oz-client-id")
        self.assertEqual(jwt_secret.secret, "oz-secret")

    @requests_mock.Mocker()
    @patch(
        "nrc.config.authorization.build_absolute_url",
        return_value="http://testserver/kanaal",
    )
    def test_selftest_ok(self, m, *mocks):
        configuration = OpenZaakAuthStep()
        configuration.configure()
        m.get("http://testserver/kanaal", json=[])

        configuration.test_configuration()

        self.assertEqual(m.last_request.url, "http://testserver/kanaal")
        self.assertEqual(m.last_request.method, "GET")

    @requests_mock.Mocker()
    @patch(
        "nrc.config.authorization.build_absolute_url",
        return_value="http://testserver/kanaal",
    )
    def test_selftest_fail(self, m, *mocks):
        configuration = OpenZaakAuthStep()
        configuration.configure()

        mock_kwargs = (
            {"exc": requests.ConnectTimeout},
            {"exc": requests.ConnectionError},
            {"status_code": 404},
            {"status_code": 403},
            {"status_code": 500},
        )
        for mock_config in mock_kwargs:
            with self.subTest(mock=mock_config):
                m.get("http://testserver/kanaal", **mock_config)

                with self.assertRaises(SelfTestFailed):
                    configuration.test_configuration()

    def test_is_configured(self):
        configuration = OpenZaakAuthStep()
        self.assertFalse(configuration.is_configured())

        configuration.configure()

        self.assertTrue(configuration.is_configured())
