# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
from django_setup_configuration.configuration import BaseConfigurationStep
from vng_api_common.authorizations.models import AuthorizationsConfig, ComponentTypes
from zgw_consumers.models import Service

from .models import AuthorizationsConfigModel


def get_service(slug: str) -> Service:
    """
    Try to find a Service and re-raise DoesNotExist with the identifier to make debugging
    easier
    """
    try:
        return Service.objects.get(slug=slug)
    except Service.DoesNotExist as e:
        raise Service.DoesNotExist(f"{str(e)} (identifier = {slug})")


class AuthorizationStep(BaseConfigurationStep[AuthorizationsConfigModel]):
    """
    Open Notificaties uses Autorisaties API to check permissions of the clients.

    1. Set up authorization to point to the API
    2. Add credentials for Open Notifications to request Open Zaak

    Normal mode doesn't change the credentials after its initial creation.
    If the client_id or secret is changed, run this command with 'overwrite' flag
    """

    verbose_name = "Configuration for Autorisaties API"
    config_model = AuthorizationsConfigModel
    namespace = "autorisaties_api"
    enable_setting = "autorisaties_api_config_enable"

    def execute(self, model: AuthorizationsConfigModel) -> None:
        auth_config = AuthorizationsConfig.get_solo()

        if auth_config.component != ComponentTypes.nrc:
            auth_config.component = ComponentTypes.nrc

        service = get_service(model.authorizations_api_service_identifier)
        auth_config.authorizations_api_service = service
        auth_config.save(update_fields=("component", "authorizations_api_service"))
