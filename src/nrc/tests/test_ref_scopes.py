from django.urls import reverse

from django_webtest import WebTest


class RefScopeTests(WebTest):
    def test_ref_scopes(self):
        """
        Regression test for https://github.com/open-zaak/open-notificaties/issues/80
        Check that only two scopes are shown on the page
        """
        url = reverse("vng_api_common:scopes")

        response = self.app.get(url)

        self.assertEqual(response.status_code, 200)

        scope_header_tags = response.html.find("div", class_="container").find_all("h2")
        # show only two scopes
        self.assertEqual(len(scope_header_tags), 2)
