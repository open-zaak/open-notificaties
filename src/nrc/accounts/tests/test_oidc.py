from django.urls import reverse
from django.utils.translation import gettext as _

from mozilla_django_oidc_db.models import OpenIDConnectConfig

from nrc.utils.webtest import WebTest


class OIDCLoginButtonTestCase(WebTest):
    def test_oidc_button_disabled(self):
        config = OpenIDConnectConfig.get_solo()
        config.enabled = False
        config.save()

        response = self.app.get(reverse("admin:login"))

        oidc_login_link = response.html.find(
            "a", string=_("Login with organization account")
        )

        # Verify that the login button is not visible
        self.assertIsNone(oidc_login_link)

    def test_oidc_button_enabled(self):
        config = OpenIDConnectConfig.get_solo()
        config.enabled = True
        config.oidc_op_token_endpoint = "https://some.endpoint.nl/"
        config.oidc_op_user_endpoint = "https://some.endpoint.nl/"
        config.oidc_rp_client_id = "id"
        config.oidc_rp_client_secret = "secret"
        config.save()

        response = self.app.get(reverse("admin:login"))

        oidc_login_link = response.html.find(
            "a", string=_("Login with organization account")
        )

        # Verify that the login button is visible
        self.assertIsNotNone(oidc_login_link)
        self.assertEqual(
            oidc_login_link.attrs["href"], reverse("oidc_authentication_init")
        )
