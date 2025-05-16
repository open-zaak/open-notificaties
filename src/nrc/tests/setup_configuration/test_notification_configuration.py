from django.test import TestCase

from django_setup_configuration.test_utils import execute_single_step
from notifications_api_common.models import NotificationsConfig
from zgw_consumers.models import Service

from nrc.setup_configuration.steps import NotificationConfigurationStep


class NotificationConfigurationTest(TestCase):
    def test_notifications_api_service_identifier_is_optional(self):
        config_file_path = (
            "src/nrc/tests/setup_configuration/files/"
            "notifications_config_without_service_identifier.yaml"
        )
        execute_single_step(NotificationConfigurationStep, yaml_source=config_file_path)
        config = NotificationsConfig.get_solo()
        assert config.notification_delivery_max_retries == 5
        assert config.notification_delivery_retry_backoff == 2
        assert config.notification_delivery_retry_backoff_max == 20

        assert config.notifications_api_service is None

    def test_notifications_api_service_identifier_is_saved(self):
        Service.objects.create(
            label="Notificaties API",
            api_root="https://example.com/api/v1/",
            slug="notificaties-api",
        )

        config_file_path = "src/nrc/tests/setup_configuration/files/notifications_config_with_service_identifier.yaml"
        execute_single_step(NotificationConfigurationStep, yaml_source=config_file_path)
        config = NotificationsConfig.get_solo()
        assert config.notification_delivery_max_retries == 4
        assert config.notification_delivery_retry_backoff == 1
        assert config.notification_delivery_retry_backoff_max == 10
        assert config.notifications_api_service.slug == "notificaties-api"
