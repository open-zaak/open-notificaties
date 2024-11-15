# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
from typing import Iterable
from django.conf import settings
from django.urls import reverse

import requests
from django_setup_configuration.configuration import BaseConfigurationStep
from django_setup_configuration.exceptions import SelfTestFailed
from vng_api_common.authorizations.models import AuthorizationsConfig, ComponentTypes
from vng_api_common.authorizations.utils import generate_jwt
from vng_api_common.models import JWTSecret
from zgw_consumers.models import Service

from nrc.utils import build_absolute_url


def _generate_service_slug(existing_slugs: Iterable[str]) -> str:
    default_slug = "authorization-api-service"

    if not existing_slugs or default_slug not in existing_slugs:
        return default_slug

    slug = default_slug
    count = 1

    while slug in existing_slugs:
        count += 1
        slug = f"{default_slug}-{count}"

    return slug


class AuthorizationStep(BaseConfigurationStep):
    """
    Open Notificaties uses Autorisaties API to check permissions of the clients.

    1. Set up authorization to point to the API
    2. Add credentials for Open Notifications to request Open Zaak

    Normal mode doesn't change the credentials after its initial creation.
    If the client_id or secret is changed, run this command with 'overwrite' flag
    """

    verbose_name = "Authorization Configuration"
    required_settings = [
        "AUTORISATIES_API_ROOT",
        "NOTIF_OPENZAAK_CLIENT_ID",
        "NOTIF_OPENZAAK_SECRET",
    ]
    enable_setting = "AUTHORIZATION_CONFIG_ENABLE"

    def is_configured(self) -> bool:
        auth_config = AuthorizationsConfig.get_solo()
        service = auth_config.authorizations_api_service

        if not service:
            return False

        return service.api_root == settings.AUTORISATIES_API_ROOT

    def configure(self) -> None:
        # Step 1
        auth_config = AuthorizationsConfig.get_solo()

        if auth_config.component != ComponentTypes.nrc:
            auth_config.component = ComponentTypes.nrc

        # Step 2
        organization = (
            settings.OPENNOTIFICATIES_ORGANIZATION or settings.NOTIF_OPENZAAK_CLIENT_ID
        )

        service, _ = Service.objects.update_or_create(
            api_root=settings.AUTORISATIES_API_ROOT,
            defaults=dict(
                label="Open Zaak Autorisaties API",
                client_id=settings.NOTIF_OPENZAAK_CLIENT_ID,
                secret=settings.NOTIF_OPENZAAK_SECRET,
                user_id=settings.NOTIF_OPENZAAK_CLIENT_ID,
                user_representation=f"Open Notificaties {organization}",
            ),
        )

        if not service.slug:
            slugs = Service.objects.values_list("slug", flat=True)
            service.slug = _generate_service_slug(slugs)
            service.save(update_fields=("slug",))

        auth_config.authorizations_api_service = service
        auth_config.save(update_fields=("component", "authorizations_api_service"))

    def test_configuration(self) -> None:
        """
        This check depends on the configuration  of permissions in Open Zaak
        """
        client = AuthorizationsConfig.get_client()

        if not client:
            raise SelfTestFailed("No service configured for the Autorisaties API")

        try:
            response: requests.Response = client.get("applicaties")
            response.raise_for_status()
        except requests.RequestException as exc:
            raise SelfTestFailed(
                "Could not retrieve list of applications from Autorisaties API."
            ) from exc


class OpenZaakAuthStep(BaseConfigurationStep):
    """
    Configure credentials for Open Zaak to request Open Notificaties
    This step takes care only of Open Zaak authentication. Permissions should be
    set up in the Autorisaties component of the Open Zaak itself.

    Normal mode doesn't change the secret after its initial creation.
    If the secret is changed, run this command with 'overwrite' flag
    """

    verbose_name = "Open Zaak Authentication Configuration"
    required_settings = [
        "OPENZAAK_NOTIF_CLIENT_ID",
        "OPENZAAK_NOTIF_SECRET",
    ]
    enable_setting = "OPENZAAK_NOTIF_CONFIG_ENABLE"

    def is_configured(self) -> bool:
        return JWTSecret.objects.filter(
            identifier=settings.OPENZAAK_NOTIF_CLIENT_ID
        ).exists()

    def configure(self):
        jwt_secret, created = JWTSecret.objects.get_or_create(
            identifier=settings.OPENZAAK_NOTIF_CLIENT_ID,
            defaults={"secret": settings.OPENZAAK_NOTIF_SECRET},
        )
        if jwt_secret.secret != settings.OPENZAAK_NOTIF_SECRET:
            jwt_secret.secret = settings.OPENZAAK_NOTIF_SECRET
            jwt_secret.save(update_fields=["secret"])

    def test_configuration(self):
        """
        This check depends on the configuration  of permissions in Open Zaak
        """
        endpoint = reverse("kanaal-list", kwargs={"version": "1"})
        full_url = build_absolute_url(endpoint, request=None)
        token = generate_jwt(
            settings.OPENZAAK_NOTIF_CLIENT_ID, settings.OPENZAAK_NOTIF_SECRET, "", ""
        )

        try:
            response = requests.get(
                full_url, headers={"Authorization": token, "Accept": "application/json"}
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise SelfTestFailed(
                f"Could not list kanalen for {settings.NOTIF_OPENZAAK_CLIENT_ID}"
            ) from exc
