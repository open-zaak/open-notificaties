import logging

from django_setup_configuration.configuration import BaseConfigurationStep
from django_setup_configuration.exceptions import ConfigurationRunFailed

from nrc.datamodel.models import Kanaal

from .models import KanaalConfigurationModel

logger = logging.getLogger(__name__)


class KanaalConfigurationStep(BaseConfigurationStep[KanaalConfigurationModel]):
    """
    Configure Kanalen for Notificaties API
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
