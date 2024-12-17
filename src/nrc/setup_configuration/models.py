from django_setup_configuration.fields import DjangoModelRef
from django_setup_configuration.models import ConfigurationModel
from pydantic import UUID4, Field
from vng_api_common.authorizations.models import AuthorizationsConfig

from nrc.datamodel.models import Abonnement, Kanaal


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


class KanalenFilterConfigurationModel(ConfigurationModel):
    filters: dict[str, str] = Field(
        description="Key value mapping based on which notifications will be filtered",
        default_factory=dict,
    )
    naam: str = Field(description="The name of the channel")


class AbonnementConfigurationItem(ConfigurationModel):
    uuid: UUID4 = Field(description="The UUID for this Abonnement.")
    kanalen: list[KanalenFilterConfigurationModel] = Field(
        description="A list of channels which are subscribed to"
    )

    class Meta:
        django_model_refs = {
            Abonnement: [
                "callback_url",
                "auth",
            ]
        }


class AbonnementConfigurationModel(ConfigurationModel):
    items: list[AbonnementConfigurationItem]
