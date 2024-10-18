# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
from django.conf import settings
from django.urls import reverse

import requests
from django_setup_configuration.configuration import BaseConfigurationStep
from django_setup_configuration.exceptions import SelfTestFailed
from furl import furl
from notifications_api_common.models import NotificationsConfig
from vng_api_common.authorizations.models import AuthorizationsConfig, ComponentTypes
from vng_api_common.models import APICredential, JWTSecret
from zds_client import ClientAuth
from zgw_consumers.constants import APITypes, AuthTypes
from zgw_consumers.models import Service

from nrc.utils import build_absolute_url


class AuthorizationStep(BaseConfigurationStep):
    """
    Open Notificaties uses Autorisaties API to check permissions of the clients.

    1. Set up authorization to point to the API
    2. Add credentials for Open Notifications to request Open Zaak
    3. Configure Open Notificaties such that it can access itself (required because
       Open Notificaties must be subscribed to changes in the `autorisaties` channel)

    Normal mode doesn't change the credentials after its initial creation.
    If the client_id or secret is changed, run this command with 'overwrite' flag
    """

    verbose_name = "Authorization Configuration"
    required_settings = [
        "OPENNOTIFICATIES_DOMAIN",
        "AUTORISATIES_API_ROOT",
        "NOTIF_OPENZAAK_CLIENT_ID",
        "NOTIF_OPENZAAK_SECRET",
    ]
    enable_setting = "AUTHORIZATION_CONFIG_ENABLE"

    def is_configured(self) -> bool:
        credential = APICredential.objects.filter(
            api_root=settings.AUTORISATIES_API_ROOT
        )
        auth_config = AuthorizationsConfig.get_solo()

        return credential.exists() and bool(
            auth_config.api_root == settings.AUTORISATIES_API_ROOT
        )

    def configure(self) -> None:
        # Step 1
        auth_config = AuthorizationsConfig.get_solo()
        if auth_config.api_root != settings.AUTORISATIES_API_ROOT:
            auth_config.api_root = settings.AUTORISATIES_API_ROOT
            auth_config.component = ComponentTypes.nrc
            auth_config.save(update_fields=["api_root", "component"])

        # Step 2
        organization = (
            settings.OPENNOTIFICATIES_ORGANIZATION or settings.NOTIF_OPENZAAK_CLIENT_ID
        )
        APICredential.objects.update_or_create(
            api_root=settings.AUTORISATIES_API_ROOT,
            defaults={
                "label": "Open Zaak Autorisaties API",
                "client_id": settings.NOTIF_OPENZAAK_CLIENT_ID,
                "secret": settings.NOTIF_OPENZAAK_SECRET,
                "user_id": settings.NOTIF_OPENZAAK_CLIENT_ID,
                "user_representation": f"Open Notificaties {organization}",
            },
        )

        # TODO remove hardcoded version?
        # Step 3 (step 8/9 in Open Zaak configuration documentation)
        api_version = settings.API_VERSION.split(".")[0]
        notifs_api_root = (
            furl(settings.OPENNOTIFICATIES_DOMAIN)
            / reverse("api-root", kwargs={"version": api_version})
        ).url
        notifs_oas_url = (
            furl(settings.OPENNOTIFICATIES_DOMAIN)
            / reverse("schema", kwargs={"version": api_version})
        ).url
        scheme = "http" if settings.DEBUG else "https"
        notification_service, _ = Service.objects.update_or_create(
            api_root=f"{scheme}://{notifs_api_root}",
            oas=f"{scheme}://{notifs_oas_url}",
            defaults={
                "label": "Open Notificaties",
                "api_type": APITypes.nrc,
                "client_id": settings.NOTIF_OPENZAAK_CLIENT_ID,
                "secret": settings.NOTIF_OPENZAAK_SECRET,
                "auth_type": AuthTypes.zgw,
                "user_id": settings.NOTIF_OPENZAAK_CLIENT_ID,
                "user_representation": f"Open Notificaties {organization}",
            },
        )
        config = NotificationsConfig.get_solo()
        config.notifications_api_service = notification_service
        config.save()

    def test_configuration(self) -> None:
        """
        This check depends on the configuration  of permissions in Open Zaak
        """
        client = AuthorizationsConfig.get_client()
        try:
            client.list("applicatie")
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
        auth = ClientAuth(
            client_id=settings.OPENZAAK_NOTIF_CLIENT_ID,
            secret=settings.OPENZAAK_NOTIF_SECRET,
        )

        try:
            response = requests.get(
                full_url, headers={**auth.credentials(), "Accept": "application/json"}
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise SelfTestFailed(
                f"Could not list kanalen for {settings.NOTIF_OPENZAAK_CLIENT_ID}"
            ) from exc
