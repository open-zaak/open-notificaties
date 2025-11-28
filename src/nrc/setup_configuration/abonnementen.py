import structlog
from django_setup_configuration.configuration import BaseConfigurationStep
from django_setup_configuration.exceptions import ConfigurationRunFailed

from nrc.datamodel.models import (
    Abonnement,
    CloudEventFilterGroup,
    Filter,
    FilterGroup,
    Kanaal,
)

from .models import AbonnementConfigurationModel

logger = structlog.stdlib.get_logger(__name__)


class AbonnementConfigurationStep(BaseConfigurationStep[AbonnementConfigurationModel]):
    """
    Configure Abonnementen for Notificaties API

    .. note::

        The configured data here must correspond with the configured data from
        the previous step ``NotificationSubscriptionConfigurationStep``
    """

    verbose_name = "Configuration for Notificaties API Abonnementen"
    config_model = AbonnementConfigurationModel
    namespace = "notifications_abonnementen_config"
    enable_setting = "notifications_abonnementen_config_enable"

    def execute(self, model: AbonnementConfigurationModel):
        if len(model.items) == 0:
            raise ConfigurationRunFailed("You must configure at least one Abonnement")

        for item in model.items:
            abonnement, created = Abonnement.objects.update_or_create(
                uuid=item.uuid,
                defaults={
                    "callback_url": item.callback_url,
                    "auth": item.auth,
                    "send_cloudevents": item.send_cloudevents,
                },
            )

            if not item.kanalen and not item.cloudevent_filters:
                raise ConfigurationRunFailed(
                    f"Abonnement {item.uuid} must either have `kanalen` or `cloudevent_filters` specified"
                )

            # TODO should we apply the same validation as in the serializer here?
            for abonnement_filter in item.kanalen:
                try:
                    kanaal = Kanaal.objects.get(naam=abonnement_filter.naam)
                except Kanaal.DoesNotExist:
                    raise ConfigurationRunFailed(
                        f"No Kanaal with name {abonnement_filter.naam} exists"
                    )

                filter_group, _ = FilterGroup.objects.update_or_create(
                    kanaal=kanaal, abonnement=abonnement
                )
                for key, value in abonnement_filter.filters.items():
                    # key is used for update_or_create, because multiple filters in the
                    # same filter_group with the same key doesn't work
                    Filter.objects.update_or_create(
                        key=key, filter_group=filter_group, defaults={"value": value}
                    )

            for type_substring in item.cloudevent_filters:
                CloudEventFilterGroup.objects.update_or_create(
                    type_substring=type_substring, abonnement=abonnement
                )

            logger.debug(
                "subscription_created" if created else "subscription_updated",
                subscription_uuid=abonnement.uuid,
                subscription_pk=abonnement.pk,
            )
