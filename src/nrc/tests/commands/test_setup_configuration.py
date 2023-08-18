from django.core.management import call_command
from django.test import TestCase

from notifications_api_common.models import NotificationsConfig, Subscription

from vng_api_common.authorizations.models import AuthorizationsConfig
from vng_api_common.constants import ComponentTypes
from vng_api_common.models import APICredential, JWTSecret

from zgw_consumers.models.services import Service
from zgw_consumers.constants import APITypes, AuthTypes


class SetupConfigurationTests(TestCase):
    def test_setup_configuration(self):
        ac_root = "https://test.openzaak.nl/autorisaties/api/v1/"
        notif_root = "http://127.0.0.1:8000/"
        callback_url = "http://127.0.0.1:8000/api/v1/callbacks"
        municipality = "MaykinMedia"
        notif_client_id = "open-notificaties"
        notif_secret_key = "foobar"
        openzaak_client_id = "open-zaak"
        openzaak_secret_key = "foobar"

        call_command(
            "new_setup_configuration",
            ac_root,
            municipality,
            notif_root,
            callback_url,
            notif_client_id,
            openzaak_client_id,
            notif_secret_key,
            openzaak_secret_key,
        )

        # Test Step 1
        ac_config = AuthorizationsConfig.get_solo()
        self.assertEqual(ac_config.api_root, ac_root)
        self.assertEqual(ac_config.component, ComponentTypes.nrc)

        # Test Step 2
        service = Service.objects.get()
        self.assertEqual(service.api_type, APITypes.nrc)
        self.assertEqual(service.auth_type, AuthTypes.zgw)
        self.assertEqual(service.api_root, notif_root)

        notif_config = NotificationsConfig.objects.get()
        self.assertEqual(notif_config.notifications_api_service, service)

        sub = Subscription.objects.get()
        self.assertEqual(sub.callback_url, callback_url)
        self.assertEqual(sub.client_id, notif_client_id)
        self.assertEqual(sub.channels, ["autorisaties"])

        # Test Step 3
        api_credential_notif = APICredential.objects.get(api_root=ac_root)
        self.assertEqual(api_credential_notif.api_root, ac_root)
        self.assertEqual(
            api_credential_notif.label,
            f"Open Zaak Autorisaties API {municipality}",
        )
        self.assertEqual(api_credential_notif.client_id, "open-notificaties")
        self.assertEqual(api_credential_notif.secret, notif_secret_key)
        self.assertEqual(api_credential_notif.user_id, "open-notificaties")
        self.assertEqual(
            api_credential_notif.user_representation,
            f"Open Notificaties {municipality}",
        )

        # Test Step 4
        api_credential_opencase = APICredential.objects.get(api_root=notif_root)
        self.assertEqual(api_credential_opencase.api_root, notif_root)
        self.assertEqual(
            api_credential_opencase.label,
            f"Own API {municipality}",
        )
        self.assertEqual(api_credential_opencase.client_id, "open-notificaties")
        self.assertEqual(api_credential_opencase.secret, notif_secret_key)
        self.assertEqual(api_credential_opencase.user_id, "open-notificaties")
        self.assertEqual(
            api_credential_opencase.user_representation,
            f"Open Notificaties {municipality}",
        )

        # Test Step 5
        notif_api_jwtsecret_ac = JWTSecret.objects.get(identifier=openzaak_client_id)
        self.assertEqual(
            notif_api_jwtsecret_ac.identifier,
            "open-zaak",
        )
        self.assertEqual(notif_api_jwtsecret_ac.secret, openzaak_secret_key)

        # Test Step 6
        notif_api_jwtsecret_notif = JWTSecret.objects.get(identifier=notif_client_id)
        self.assertEqual(
            notif_api_jwtsecret_notif.identifier,
            "open-notificaties",
        )
        self.assertEqual(notif_api_jwtsecret_notif.secret, notif_secret_key)
