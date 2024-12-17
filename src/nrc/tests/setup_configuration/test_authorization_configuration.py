from django.test import TestCase

from django_setup_configuration.exceptions import ConfigurationRunFailed
from django_setup_configuration.test_utils import execute_single_step
from vng_api_common.authorizations.models import AuthorizationsConfig, ComponentTypes
from zgw_consumers.test.factories import ServiceFactory

from nrc.setup_configuration.authorization import AuthorizationStep

CONFIG_FILE_PATH = (
    "src/nrc/tests/setup_configuration/files/setup_config_auth_config.yaml"
)


class AuthorizationConfigurationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.service = ServiceFactory.create(
            slug="autorisaties-api",
            api_root="http://openzaak.local/autorisaties/api/v1/",
        )

    def test_execute_configuration_step_success(self):
        execute_single_step(AuthorizationStep, yaml_source=CONFIG_FILE_PATH)

        config = AuthorizationsConfig.get_solo()

        self.assertEqual(config.component, ComponentTypes.nrc)
        self.assertEqual(config.authorizations_api_service, self.service)

    def test_execute_configuration_step_update_existing(self):
        config = AuthorizationsConfig.get_solo()
        config.component = ComponentTypes.zrc
        config.authorizations_api_service = ServiceFactory.create(slug="other-api")
        config.save()

        execute_single_step(AuthorizationStep, yaml_source=CONFIG_FILE_PATH)

        config = AuthorizationsConfig.get_solo()
        service = config.authorizations_api_service

        self.assertEqual(config.component, ComponentTypes.nrc)
        self.assertEqual(service, self.service)

    def test_execute_configuration_step_idempotent(self):
        def make_assertions():
            config = AuthorizationsConfig.get_solo()
            service = config.authorizations_api_service

            self.assertEqual(config.component, ComponentTypes.nrc)
            self.assertEqual(service, self.service)

        execute_single_step(AuthorizationStep, yaml_source=CONFIG_FILE_PATH)

        make_assertions()

        execute_single_step(AuthorizationStep, yaml_source=CONFIG_FILE_PATH)

        make_assertions()

    def test_execute_configuration_service_does_not_exist(self):
        self.service.delete()
        config = AuthorizationsConfig.get_solo()
        config.authorizations_api_service = None
        config.save()

        with self.assertRaises(ConfigurationRunFailed) as exc:
            execute_single_step(AuthorizationStep, yaml_source=CONFIG_FILE_PATH)
        self.assertEqual(
            str(exc.exception),
            "Service matching query does not exist. (identifier = autorisaties-api)",
        )

        config = AuthorizationsConfig.get_solo()

        self.assertIsNone(config.authorizations_api_service)
