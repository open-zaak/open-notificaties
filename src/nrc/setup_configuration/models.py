from django_setup_configuration.fields import DjangoModelRef
from django_setup_configuration.models import ConfigurationModel
from pydantic import UUID4, Field
from vng_api_common.authorizations.models import AuthorizationsConfig

from nrc.datamodel.models import Abonnement, Kanaal


class AuthorizationsConfigModel(ConfigurationModel):
    authorizations_api_service_identifier: str = DjangoModelRef(
        AuthorizationsConfig,
        "authorizations_api_service",
        description=(
            "The identifier of the Autorisaties API service "
            "(which could be defined in the previous `ServiceConfigurationStep`)"
        ),
        examples=["autorisaties-api"],
    )

    class Meta:
        extra_kwargs = {"authorizations_api_service_identifier": {"required": True}}


class KanaalConfigurationItem(ConfigurationModel):
    filters: list[str] = DjangoModelRef(
        Kanaal,
        "filters",
        examples=[["bronorganisatie", "zaaktype", "vertrouwelijkheidaanduiding"]],
    )

    class Meta:
        django_model_refs = {
            Kanaal: [
                "naam",
                "documentatie_link",
            ]
        }
        extra_kwargs = {
            "naam": {"examples": ["zaken"]},
            "documentatie_link": {
                "examples": ["https://openzaak.local/ref/kanalen/#zaken"]
            },
        }


class KanaalConfigurationModel(ConfigurationModel):
    items: list[KanaalConfigurationItem]


class KanalenFilterConfigurationModel(ConfigurationModel):
    filters: dict[str, str] = Field(
        description="Key value mapping based on which notifications will be filtered",
        default_factory=dict,
        examples=[
            {
                "zaaktype": "https://openzaak.local/catalogi/api/v1/zaaktypen/d109cd8a-fe7b-4eb2-8cab-766712a4a267"
            }
        ],
    )
    naam: str = Field(description="The name of the channel", examples=["zaken"])


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
        extra_kwargs = {
            "callback_url": {"examples": ["https://example.com/api/webhook/"]},
            "auth": {"examples": ["Token po4T8YpTZmeKXVWJAQCZ"]},
        }


class AbonnementConfigurationModel(ConfigurationModel):
    items: list[AbonnementConfigurationItem]
