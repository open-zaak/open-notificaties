from unittest.mock import patch
from urllib.parse import urlparse

from django.urls import reverse

from django_webtest import WebTest
from maykin_2fa.test import disable_admin_mfa
from mozilla_django_oidc_db.models import OpenIDConnectConfig

from nrc.accounts.tests.factories import SuperUserFactory


@disable_admin_mfa()
class AdminSessionRefreshMiddlewareTests(WebTest):
    @patch(
        "mozilla_django_oidc_db.mixins.OpenIDConnectConfig.get_solo",
        return_value=OpenIDConnectConfig(
            enabled=True,
            oidc_op_authorization_endpoint="https://example.com/auth/",
        ),
    )
    @patch(
        "mozilla_django_oidc.middleware.SessionRefresh.is_refreshable_url",
        return_value=True,
    )
    def test_session_refresh_no_crash(self, *mocks):
        """
        Regression test for crash on admin login because of session refresh.
        """
        user = SuperUserFactory.create()
        admin_url = reverse("admin:index")

        response = self.app.get(admin_url, user=user)

        # we are being redirected to OIDC
        self.assertEqual(response.status_code, 302)
        redirect_url = urlparse(response["Location"])
        self.assertEqual(redirect_url.scheme, "https")
        self.assertEqual(redirect_url.netloc, "example.com")
        self.assertEqual(redirect_url.path, "/auth/")
