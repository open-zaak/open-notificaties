"""
Guarantee that the proper authorization machinery is in place.
"""

import requests_mock
from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APITestCase, override_settings
from vng_api_common.tests import AuthCheckMixin, JWTAuthMixin, reverse

from nrc.datamodel.tests.factories import AbonnementFactory, KanaalFactory

from ..scopes import SCOPE_NOTIFICATIES_CONSUMEREN, SCOPE_NOTIFICATIES_PUBLICEREN


class NotificationsScopeForbiddenTests(AuthCheckMixin, APITestCase):
    def test_cannot_create_without_correct_scope(self):
        urls = [
            reverse("abonnement-list"),
            reverse("kanaal-list"),
            reverse("notificaties-list"),
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertForbidden(url, method="post")

    def test_cannot_read_without_correct_scope(self):
        abonnement = AbonnementFactory.create()
        kanaal = KanaalFactory.create()

        urls = [
            reverse("abonnement-list"),
            reverse(abonnement),
            reverse("kanaal-list"),
            reverse(kanaal),
        ]

        for url in urls:
            with self.subTest(url=url):
                self.assertForbidden(url, method="get")


class AbonnementReadCorrectScopeTests(JWTAuthMixin, APITestCase):
    def test_abonnement_list(self):
        """
        Assert you can only list Abonnementen of the abonnementtypes of your authorization
        """
        AbonnementFactory.create()
        url = reverse("abonnement-list")

        for scope in [SCOPE_NOTIFICATIES_CONSUMEREN, SCOPE_NOTIFICATIES_PUBLICEREN]:
            with self.subTest(scope=scope):
                self.autorisatie.scopes = [scope]
                self.autorisatie.save()

                response = self.client.get(url)

                self.assertEqual(response.status_code, status.HTTP_200_OK)

                results = response.data

                self.assertEqual(len(results), 1)

    def test_abonnement_retreive(self):
        """
        Assert you can only read Abonnementen of the abonnementtypes of your authorization
        """
        abonnement = AbonnementFactory.create()
        url = reverse(abonnement)

        for scope in [SCOPE_NOTIFICATIES_CONSUMEREN, SCOPE_NOTIFICATIES_PUBLICEREN]:
            with self.subTest(scope=scope):
                self.autorisatie.scopes = [scope]
                self.autorisatie.save()

                response1 = self.client.get(url)

                self.assertEqual(response1.status_code, status.HTTP_200_OK)

    def test_read_superuser(self):
        """
        superuser read everything
        """
        self.applicatie.heeft_alle_autorisaties = True
        self.applicatie.save()

        AbonnementFactory.create()
        url = reverse("abonnement-list")

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json()
        self.assertEqual(len(response_data), 1)


class AbonnementWriteScopeTests(JWTAuthMixin, APITestCase):
    def test_create_scope_not_ok(self):
        self.autorisatie.scopes = [SCOPE_NOTIFICATIES_PUBLICEREN]
        self.autorisatie.save()
        url = reverse("abonnement-list")

        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_scope_ok(self):
        self.autorisatie.scopes = [SCOPE_NOTIFICATIES_CONSUMEREN]
        self.autorisatie.save()
        url = reverse("abonnement-list")

        response = self.client.post(url)

        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_scope_not_ok(self):
        abonnement = AbonnementFactory.create(client_id="testsuite")
        self.autorisatie.scopes = [SCOPE_NOTIFICATIES_PUBLICEREN]
        self.autorisatie.save()
        url = reverse(abonnement)

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_scope_ok(self):
        abonnement = AbonnementFactory.create(client_id="testsuite")
        self.autorisatie.scopes = [SCOPE_NOTIFICATIES_CONSUMEREN]
        self.autorisatie.save()
        url = reverse(abonnement)

        response = self.client.delete(url)

        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_scope_not_ok(self):
        abonnement = AbonnementFactory.create(client_id="testsuite")
        self.autorisatie.scopes = [SCOPE_NOTIFICATIES_PUBLICEREN]
        self.autorisatie.save()
        url = reverse(abonnement)

        for method in ["put", "patch"]:
            with self.subTest(method=method):
                response = getattr(self.client, method)(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_scope_ok(self):
        abonnement = AbonnementFactory.create(client_id="testsuite")
        self.autorisatie.scopes = [SCOPE_NOTIFICATIES_CONSUMEREN]
        self.autorisatie.save()
        url = reverse(abonnement)

        for method in ["put", "patch"]:
            with self.subTest(method=method):
                with requests_mock.mock() as m:
                    m.register_uri("POST", abonnement.callback_url, status_code=204)
                    response = getattr(self.client, method)(
                        url, {"callbackUrl": abonnement.callback_url}
                    )

        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class KanaalReadCorrectScopeTests(JWTAuthMixin, APITestCase):
    def test_kanaal_list(self):
        """
        Assert you can only list kanaalen of the kanaaltypes of your authorization
        """
        KanaalFactory.create()
        url = reverse("kanaal-list")

        for scope in [SCOPE_NOTIFICATIES_CONSUMEREN, SCOPE_NOTIFICATIES_PUBLICEREN]:
            with self.subTest(scope=scope):
                self.autorisatie.scopes = [scope]
                self.autorisatie.save()

                response = self.client.get(url)

                self.assertEqual(response.status_code, status.HTTP_200_OK)

                results = response.data

                self.assertEqual(len(results), 1)

    def test_kanaal_retreive(self):
        """
        Assert you can only read kanaalen of the kanaaltypes of your authorization
        """
        kanaal = KanaalFactory.create()
        url = reverse(kanaal)

        for scope in [SCOPE_NOTIFICATIES_CONSUMEREN, SCOPE_NOTIFICATIES_PUBLICEREN]:
            with self.subTest(scope=scope):
                self.autorisatie.scopes = [scope]
                self.autorisatie.save()

                response1 = self.client.get(url)

                self.assertEqual(response1.status_code, status.HTTP_200_OK)

    def test_read_superuser(self):
        """
        superuser read everything
        """
        self.applicatie.heeft_alle_autorisaties = True
        self.applicatie.save()

        KanaalFactory.create()
        url = reverse("kanaal-list")

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json()
        self.assertEqual(len(response_data), 1)


class KanaalWriteScopeTests(JWTAuthMixin, APITestCase):
    def test_create_scope_not_ok(self):
        self.autorisatie.scopes = [SCOPE_NOTIFICATIES_CONSUMEREN]
        self.autorisatie.save()
        url = reverse("kanaal-list")

        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_scope_ok(self):
        self.autorisatie.scopes = [SCOPE_NOTIFICATIES_PUBLICEREN]
        self.autorisatie.save()
        url = reverse("kanaal-list")

        response = self.client.post(url)

        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class NotificatiesWriteScopeTests(JWTAuthMixin, APITestCase):
    def test_create_scope_not_ok(self):
        self.autorisatie.scopes = [SCOPE_NOTIFICATIES_CONSUMEREN]
        self.autorisatie.save()
        url = reverse("notificaties-list")

        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_scope_ok(self):
        self.autorisatie.scopes = [SCOPE_NOTIFICATIES_PUBLICEREN]
        self.autorisatie.save()
        url = reverse("notificaties-list")

        response = self.client.post(url)

        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)


@freeze_time("2025-01-01T12:00:05Z")
class JWTIatTests(JWTAuthMixin, APITestCase):
    @freeze_time("2025-01-01T12:00:10Z")
    def test_iat_ok(self):
        self.applicatie.heeft_alle_autorisaties = True
        self.applicatie.save()
        url = reverse("kanaal-list")

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @freeze_time("2025-01-01T12:00:00Z")
    def test_iat_in_future_fails(self):
        self.applicatie.heeft_alle_autorisaties = True
        self.applicatie.save()
        url = reverse("kanaal-list")

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @override_settings(TIME_LEEWAY=5)
    @freeze_time("2025-01-01T12:00:01Z")
    def test_iat_in_future_with_leeway(self):
        self.applicatie.heeft_alle_autorisaties = True
        self.applicatie.save()
        url = reverse("kanaal-list")

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @override_settings(TIME_LEEWAY=5)
    @freeze_time("2025-01-01T11:59:54Z")
    def test_iat_in_future_later_than_leeway(self):
        self.applicatie.heeft_alle_autorisaties = True
        self.applicatie.save()
        url = reverse("kanaal-list")

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
