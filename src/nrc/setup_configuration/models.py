from typing import Optional

from django_setup_configuration.fields import DjangoModelRef
from django_setup_configuration.models import ConfigurationModel
from notifications_api_common.contrib.setup_configuration.models import (
    NotificationConfigurationModel as _NotificationConfigurationModel,
)
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


class CloudEventFilterConfigurationModel(ConfigurationModel):
    filters: dict[str, str] = Field(
        description="Key value mapping based on which cloud events will be filtered",
        default_factory=dict,
        examples=[
            {
                "zaaktype": "https://openzaak.local/catalogi/api/v1/zaaktypen/d109cd8a-fe7b-4eb2-8cab-766712a4a267"
            }
        ],
    )
    type_substring: str = Field(
        description="cloudevent type substrings that the subscription will watch for",
        examples=["nl.overheid.zaken"],
    )


class AbonnementConfigurationItem(ConfigurationModel):
    uuid: UUID4 = Field(description="The UUID for this Abonnement.")
    kanalen: Optional[list[KanalenFilterConfigurationModel]] = Field(
        default=[], description="A list of channels which are subscribed to"
    )
    # XXX: deprecate list of strings option in next major version
    cloudevent_filters: Optional[
        list[CloudEventFilterConfigurationModel] | list[str]
    ] = Field(
        default=[],
        description=(
            "A list of cloudevent filters that the subscription will watch for. "
            "This supports either a list of cloud event type substrings, or a list of "
            "type substrings with additional filters."
        ),
    )

    class Meta:
        django_model_refs = {
            Abonnement: [
                "callback_url",
                "auth_type",
                "auth",
                "auth_client_id",
                "secret",
                "oauth2_token_url",
                "oauth2_scope",
                "send_cloudevents",
            ]
        }
        extra_kwargs = {
            "callback_url": {"examples": ["https://example.com/api/webhook/"]},
            "auth_type": {"examples": ["api_key"]},
            "auth": {"examples": ["Token po4T8YpTZmeKXVWJAQCZ"]},
            "auth_client_id": {"examples": ["client-id"]},
            "secret": {"examples": ["my-secret"]},
            "oauth2_token_url": {"examples": ["https://auth.example.com/token"]},
            "oauth2_scope": {"examples": ["read write"]},
        }


class AbonnementConfigurationModel(ConfigurationModel):
    items: list[AbonnementConfigurationItem]


class NotificationConfigurationModel(_NotificationConfigurationModel):
    notifications_api_service_identifier: Optional[str] = Field(
        default=None, examples=["notificaties-api"]
    )

    class Meta(_NotificationConfigurationModel.Meta):
        pass
