from django.contrib.sites.models import Site

from django_setup_configuration.fields import DjangoModelRef
from django_setup_configuration.models import ConfigurationModel
from pydantic import Field
from vng_api_common.authorizations.models import AuthorizationsConfig


class AuthorizationsConfigModel(ConfigurationModel):
    authorizations_api_service_identifier: str = DjangoModelRef(
        AuthorizationsConfig, "authorizations_api_service"
    )


class SiteConfigModel(ConfigurationModel):
    organization: str = Field()
    """The name of the organization that owns this Open Notificaties instance"""

    class Meta:
        django_model_refs = {Site: ("domain",)}
