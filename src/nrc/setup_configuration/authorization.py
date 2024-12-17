from django_setup_configuration.configuration import BaseConfigurationStep
from django_setup_configuration.exceptions import ConfigurationRunFailed
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
        raise ConfigurationRunFailed(f"{str(e)} (identifier = {slug})")


class AuthorizationStep(BaseConfigurationStep[AuthorizationsConfigModel]):
    """
    Open Notificaties uses Autorisaties API to check permissions of the clients that
    make requests to Open Notificaties.

    This step configures Open Notificaties to use the specified Autorisaties API. It is
    dependent on ``zgw_consumers.contrib.setup_configuration.steps.ServiceConfigurationStep``
    to load a ``Service`` for this Autorisaties API, which is referred to in this step by
    ``authorizations_api_service_identifier``.
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
