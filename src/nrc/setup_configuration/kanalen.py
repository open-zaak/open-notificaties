import logging

from django_setup_configuration.configuration import BaseConfigurationStep
from django_setup_configuration.exceptions import ConfigurationRunFailed

from nrc.datamodel.models import Kanaal

from .models import KanaalConfigurationModel

logger = logging.getLogger(__name__)


class KanaalConfigurationStep(BaseConfigurationStep[KanaalConfigurationModel]):
    """
    Configure Kanalen for Notificaties API

    If Open Notificaties is being configured together with Open Zaak, this step can be
    used as a replacement for the ``register_kanalen`` command in Open Zaak, because that
    command requires Open Zaak to be able to make requests to Open Notificaties, which can
    cause issues when deploying multiple application at once.

    To use this step as a replacement for ``register_kanalen``, make sure to configure
    the Kanalen defined in the
    `Open Zaak repository <https://github.com/open-zaak/open-zaak/blob/main/src/notificaties.md>`_.
    """

    verbose_name = "Configuration for Notificaties API Kanalen"
    config_model = KanaalConfigurationModel
    namespace = "notifications_kanalen_config"
    enable_setting = "notifications_kanalen_config_enable"

    def execute(self, model: KanaalConfigurationModel):
        if len(model.items) == 0:
            raise ConfigurationRunFailed("You must configure at least one Kanaal")

        for item in model.items:
            kanaal, created = Kanaal.objects.update_or_create(
                naam=item.naam,
                defaults={
                    "documentatie_link": item.documentatie_link,
                    "filters": item.filters,
                },
            )

            logger.debug(
                "%s Kanaal with naam='%s' and pk='%s'",
                "Created" if created else "Updated",
                kanaal.naam,
                kanaal.pk,
            )
