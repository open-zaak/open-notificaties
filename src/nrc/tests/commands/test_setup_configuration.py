import uuid
from io import StringIO
from pathlib import Path

from django.contrib.sites.models import Site
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

import requests_mock
from jwt import decode
from notifications_api_common.contrib.setup_configuration.steps import (
    NotificationConfigurationStep,
)
from notifications_api_common.models import NotificationsConfig
from rest_framework import status
from vng_api_common.authorizations.models import AuthorizationsConfig
from vng_api_common.authorizations.utils import generate_jwt
from vng_api_common.contrib.setup_configuration.steps import JWTSecretsConfigurationStep
from zgw_consumers.contrib.setup_configuration.steps import ServiceConfigurationStep

from nrc.config.authorization import AuthorizationStep
from nrc.config.site import SiteConfigurationStep

CONFIG_FILE_PATH = Path("src/nrc/tests/commands/files/setup_config_full.yaml").resolve()


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
        m.get("http://opennotificaties.local:8000/", status_code=200)
        m.get("http://opennotificaties.local:8000/api/v1/kanaal", json=[])
        m.get(
            "http://localhost:8001/autorisaties/api/v1/applicaties",
            json={
                "count": 1,
                "results": [
                    {
                        "url": f"http://localhost:8001/autorisaties/api/v1/applicaties/{_uuid}",
                        "clientIds": ["oz-client-id"],
                        "label": "OZ for ON",
                        "heeftAlleAutorisaties": True,
                        "autorisaties": [],
                    }
                ],
            },
        )

        call_command(
            "setup_configuration",
            yaml_file=CONFIG_FILE_PATH,
            stdout=stdout,
            no_color=True,
        )

        with self.subTest("Command output"):
            command_output = stdout.getvalue().splitlines()
            expected_output = [
                f"Loading config settings from {CONFIG_FILE_PATH}",
                "The following steps are configured:",
                f"{ServiceConfigurationStep()}",
                f"{JWTSecretsConfigurationStep()}",
                f"{AuthorizationStep()}",
                # f"{NotificationConfigurationStep()}",
                # f"{SiteConfigurationStep()}",
                "Executing steps...",
                f"Successfully executed step: {ServiceConfigurationStep()}",
                f"Successfully executed step: {JWTSecretsConfigurationStep()}",
                f"Successfully executed step: {AuthorizationStep()}",
                # f"Successfully executed step: {NotificationConfigurationStep()}",
                # f"Successfully executed step: {SiteConfigurationStep()}",
                "Instance configuration completed.",
            ]

            self.assertEqual(command_output, expected_output)

        with self.subTest("Authorization API client configured correctly"):
            ac_client = AuthorizationsConfig.get_client()
            self.assertIsNotNone(ac_client)

            ac_client.get("applicaties")

            create_call = m.last_request
            self.assertEqual(
                create_call.url,
                "http://localhost:8001/autorisaties/api/v1/applicaties",
            )
            self.assertIn("Authorization", create_call.headers)

            header_jwt = create_call.headers["Authorization"].split(" ")[1]
            decoded_jwt = decode(header_jwt, options={"verify_signature": False})

            self.assertEqual(decoded_jwt["client_id"], "open-notificaties")

        with self.subTest("Open Zaak can query Notification API"):
            token = generate_jwt("open-zaak", "G2LIVfXal1J93puQkV3O", "", "")

            response = self.client.get(
                reverse("kanaal-list", kwargs={"version": 1}),
                HTTP_AUTHORIZATION=token,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)

        # with self.subTest("Notifications configured correctly"):
        #     config = NotificationsConfig.get_solo()
        #     self.assertEqual(config.notifications_api_service, None)
        #     self.assertEqual(config.notification_delivery_max_retries, 5)
        #     self.assertEqual(config.notification_delivery_retry_backoff, 3)
        #     self.assertEqual(config.notification_delivery_retry_backoff_max, 30)

        # with self.subTest("Site configured correctly"):
        #     site = Site.objects.get_current()
        #     self.assertEqual(site.domain, "opennotificaties.local:8000")
        #     self.assertEqual(site.name, "Open Notificaties Demodam")
