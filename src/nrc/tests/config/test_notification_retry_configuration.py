from django.test import TestCase, override_settings

from notifications_api_common.models import NotificationsConfig

from nrc.config.notification_retry import NotificationRetryConfigurationStep


@override_settings(
    NOTIFICATION_DELIVERY_MAX_RETRIES=4,
    NOTIFICATION_DELIVERY_RETRY_BACKOFF=5,
    NOTIFICATION_DELIVERY_RETRY_BACKOFF_MAX=6,
)
class NotificationRetryConfigurationTests(TestCase):
    def test_configure(self):
        configuration = NotificationRetryConfigurationStep()
        configuration.configure()

        config = NotificationsConfig.get_solo()

        self.assertEqual(config.notification_delivery_max_retries, 4)
        self.assertEqual(config.notification_delivery_retry_backoff, 5)
        self.assertEqual(config.notification_delivery_retry_backoff_max, 6)

    def test_is_configured(self):
        configuration = NotificationRetryConfigurationStep()

        self.assertFalse(configuration.is_configured())

        configuration.configure()

        self.assertTrue(configuration.is_configured())
