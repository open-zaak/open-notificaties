from django_setup_configuration.fields import DjangoModelRef
from django_setup_configuration.models import ConfigurationModel
from vng_api_common.authorizations.models import AuthorizationsConfig


class AuthorizationsConfigModel(ConfigurationModel):
    authorizations_api_service_identifier: str = DjangoModelRef(
        AuthorizationsConfig, "authorizations_api_service"
    )
