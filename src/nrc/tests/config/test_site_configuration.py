from django.contrib.sites.models import Site
from django.test import TestCase

from django_setup_configuration.test_utils import execute_single_step

from nrc.config.site import SiteConfigurationStep

CONFIG_FILE_PATH = "src/nrc/tests/config/files/setup_config_sites.yaml"


class SiteConfigurationTests(TestCase):
    def setUp(self):
        super().setUp()

        self.addCleanup(Site.objects.clear_cache)

    def test_execute_configuration_step_success(self):
        execute_single_step(SiteConfigurationStep, yaml_source=CONFIG_FILE_PATH)

        site = Site.objects.get_current()

        self.assertEqual(site.domain, "opennotificaties.local:8000")
        self.assertEqual(site.name, "Open Notificaties Demodam")

    def test_execute_configuration_step_update_existing(self):
        site = Site.objects.get_current()
        site.domain = "other-domain.local:8000"
        site.name = "some other names"
        site.save()

        execute_single_step(SiteConfigurationStep, yaml_source=CONFIG_FILE_PATH)

        site = Site.objects.get_current()

        self.assertEqual(site.domain, "opennotificaties.local:8000")
        self.assertEqual(site.name, "Open Notificaties Demodam")

    def test_execute_configuration_step_idempotent(self):
        def make_assertions():
            site = Site.objects.get_current()

            self.assertEqual(site.domain, "opennotificaties.local:8000")
            self.assertEqual(site.name, "Open Notificaties Demodam")

        execute_single_step(SiteConfigurationStep, yaml_source=CONFIG_FILE_PATH)

        make_assertions()

        execute_single_step(SiteConfigurationStep, yaml_source=CONFIG_FILE_PATH)

        make_assertions()
