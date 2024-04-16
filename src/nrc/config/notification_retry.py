from django.conf import settings

from django_setup_configuration.configuration import BaseConfigurationStep
from notifications_api_common.models import NotificationsConfig


class NotificationRetryConfigurationStep(BaseConfigurationStep):
    """
    Configure the notifications retry behaviour.
    """

    verbose_name = "Notification retry configuration"
    required_settings = []
    optional_settings = [
        "NOTIFICATION_DELIVERY_MAX_RETRIES",
        "NOTIFICATION_DELIVERY_RETRY_BACKOFF",
        "NOTIFICATION_DELIVERY_RETRY_BACKOFF_MAX",
    ]
    enable_setting = "NOTIFICATION_RETRY_CONFIG_ENABLE"

    def is_configured(self) -> bool:
        config = NotificationsConfig.get_solo()
        for setting_name in self.optional_settings:
            # It is considered configured if one or more fields have non-default values
            model_field = getattr(NotificationsConfig, setting_name.lower()).field
            if getattr(config, setting_name.lower()) != model_field.default:
                return True
        return False

    def configure(self):
        config = NotificationsConfig.get_solo()
        for setting_name in self.optional_settings:
            if (setting_value := getattr(settings, setting_name)) is not None:
                setattr(config, setting_name.lower(), setting_value)
        config.save()

    def test_configuration(self): ...
