from django_setup_configuration.fields import DjangoModelRef
from django_setup_configuration.models import ConfigurationModel
from vng_api_common.authorizations.models import AuthorizationsConfig

from nrc.datamodel.models import Kanaal


class AuthorizationsConfigModel(ConfigurationModel):
    authorizations_api_service_identifier: str = DjangoModelRef(
        AuthorizationsConfig, "authorizations_api_service"
    )


class KanaalConfigurationItem(ConfigurationModel):
    filters: list[str] = DjangoModelRef(Kanaal, "filters")

    class Meta:
        django_model_refs = {
            Kanaal: [
                "naam",
                "documentatie_link",
            ]
        }


class KanaalConfigurationModel(ConfigurationModel):
    items: list[KanaalConfigurationItem]
