import uuid
from io import StringIO

from django.contrib.sites.models import Site
from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings
from django.urls import reverse

import requests
import requests_mock
from jwt import decode
from rest_framework import status
from vng_api_common.authorizations.models import AuthorizationsConfig
from zds_client.auth import ClientAuth
from zgw_consumers.constants import APITypes
from zgw_consumers.test import mock_service_oas_get

from nrc.config.authorization import AuthorizationStep, OpenZaakAuthStep
from nrc.config.notification_retry import NotificationRetryConfigurationStep
from nrc.config.site import SiteConfigurationStep


@override_settings(
    OPENNOTIFICATIES_DOMAIN="open-notificaties.example.com",
    OPENNOTIFICATIES_ORGANIZATION="ACME",
    AUTORISATIES_API_ROOT="https://oz.example.com/autorisaties/api/v1/",
    NOTIF_OPENZAAK_CLIENT_ID="notif-client-id",
    NOTIF_OPENZAAK_SECRET="notif-secret",
    OPENZAAK_NOTIF_CLIENT_ID="oz-client-id",
    OPENZAAK_NOTIF_SECRET="oz-secret",
)
class SetupConfigurationTests(TestCase):
    maxDiff = None

    def setUp(self):
        super().setUp()

        self.addCleanup(Site.objects.clear_cache)

    @requests_mock.Mocker()
    def test_setup_configuration(self, m):
        stdout = StringIO()
        # mocks
        _uuid = uuid.uuid4()
        m.get("http://open-notificaties.example.com/", status_code=200)
        m.get("http://open-notificaties.example.com/api/v1/kanaal", json=[])
        mock_service_oas_get(
            m, "https://oz.example.com/autorisaties/api/v1/", APITypes.ac
        )
        m.get(
            "https://oz.example.com/autorisaties/api/v1/applicaties",
            json={
                "count": 1,
                "results": [
                    {
                        "url": f"https://oz.example.com/autorisaties/api/v1/applicaties/{_uuid}",
                        "clientIds": ["oz-client-id"],
                        "label": "OZ for ON",
                        "heeftAlleAutorisaties": True,
                        "autorisaties": [],
                    }
                ],
            },
        )

        call_command("setup_configuration", stdout=stdout, no_color=True)

        with self.subTest("Command output"):
            command_output = stdout.getvalue().splitlines()
            expected_output = [
                f"Configuration will be set up with following steps: [{SiteConfigurationStep()}, "
                f"{AuthorizationStep()}, {OpenZaakAuthStep()}, {NotificationRetryConfigurationStep()}]",
                f"Configuring {SiteConfigurationStep()}...",
                f"{SiteConfigurationStep()} is successfully configured",
                f"Configuring {AuthorizationStep()}...",
                f"{AuthorizationStep()} is successfully configured",
                f"Configuring {OpenZaakAuthStep()}...",
                f"{OpenZaakAuthStep()} is successfully configured",
                f"Configuring {NotificationRetryConfigurationStep()}...",
                f"{NotificationRetryConfigurationStep()} is successfully configured",
                "Instance configuration completed.",
            ]

            self.assertEqual(command_output, expected_output)

        with self.subTest("Site configured correctly"):
            site = Site.objects.get_current()
            self.assertEqual(site.domain, "open-notificaties.example.com")
            self.assertEqual(site.name, "Open Notificaties ACME")

        with self.subTest("Authorization API client configured correctly"):
            ac_client = AuthorizationsConfig.get_client()
            self.assertIsNotNone(ac_client)

            ac_client.list("applicatie")

            create_call = m.last_request
            self.assertEqual(
                create_call.url,
                "https://oz.example.com/autorisaties/api/v1/applicaties",
            )
            self.assertIn("Authorization", create_call.headers)
            header_jwt = create_call.headers["Authorization"].split(" ")[1]
            decoded_jwt = decode(header_jwt, options={"verify_signature": False})
            self.assertEqual(decoded_jwt["client_id"], "notif-client-id")

        with self.subTest("Open Zaak can query Notification API"):
            auth = ClientAuth("oz-client-id", "oz-secret")

            response = self.client.get(
                reverse("kanaal-list", kwargs={"version": 1}),
                HTTP_AUTHORIZATION=auth.credentials()["Authorization"],
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)

    @requests_mock.Mocker()
    def test_setup_configuration_selftest_fails(self, m):
        m.get("http://open-notificaties.example.com/", exc=requests.ConnectionError)
        m.get("http://open-notificaties.example.com/api/v1/kanaal", json=[])
        mock_service_oas_get(
            m, "https://oz.example.com/autorisaties/api/v1/", APITypes.ac
        )
        m.get("https://oz.example.com/autorisaties/api/v1/applicaties", json=[])

        with self.assertRaisesMessage(
            CommandError,
            "Could not access home page at 'http://open-notificaties.example.com/'",
        ):
            call_command("setup_configuration")

    @requests_mock.Mocker()
    def test_setup_configuration_without_selftest(self, m):
        stdout = StringIO()

        call_command("setup_configuration", no_selftest=True, stdout=stdout)
        command_output = stdout.getvalue()

        self.assertEqual(len(m.request_history), 0)
        self.assertTrue("Selftest is skipped" in command_output)
