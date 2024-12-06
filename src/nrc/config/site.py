from django.contrib.sites.models import Site

from django_setup_configuration.configuration import BaseConfigurationStep

from .models import SiteConfigModel


class SiteConfigurationStep(BaseConfigurationStep[SiteConfigModel]):
    """
    Configure the application site/domain.

    **NOTE:** Site configuration will be depreciated
    """

    verbose_name = "Site Configuration"
    config_model = SiteConfigModel
    namespace = "site_config"
    enable_setting = "site_config_enable"

    def execute(self, model: SiteConfigModel) -> None:
        site = Site.objects.get_current()
        site.domain = model.domain
        site.name = f"Open Notificaties {model.organization}".strip()
        site.save()
