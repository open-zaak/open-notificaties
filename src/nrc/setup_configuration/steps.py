from notifications_api_common.contrib.setup_configuration.steps import (
    NotificationConfigurationStep as _NotificationConfigurationStep,
)

from nrc.setup_configuration.models import NotificationConfigurationModel


class NotificationConfigurationStep(_NotificationConfigurationStep):
    config_model = NotificationConfigurationModel
