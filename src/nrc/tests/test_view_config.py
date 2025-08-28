from django.test import override_settings
from django.urls import reverse_lazy

from django_webtest import WebTest
from maykin_common.vcr import VCRMixin


class ViewConfigTestCase(VCRMixin, WebTest):
    url = reverse_lazy("view-config")
    api_root = "http://notifications.local/api/v1/"

    def test_get_domain(self):
        """
        SITE_DOMAIN > django.contrib.sites
        """
        from django.contrib.sites.models import Site

        site = Site.objects.get_current()
        site.domain = "testserver.nl"
        site.save()

        with self.subTest("domain_from_DJANGO_SITES"):
            with override_settings(SITE_DOMAIN=""):
                response = self.app.get(self.url)
                self.assertEqual(response.status_code, 200)
                rows = response.html.findAll("tr")
                self.assertTrue("testserver.nl" in rows[1].text)

        with self.subTest("domain_from_SITE_DOMAIN"):
            with override_settings(SITE_DOMAIN="site.nl"):
                response = self.app.get(self.url)
                self.assertEqual(response.status_code, 200)
                rows = response.html.findAll("tr")
                self.assertTrue("site.nl" in rows[1].text)
