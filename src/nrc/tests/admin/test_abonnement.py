from django.test import override_settings, tag
from django.urls import reverse, reverse_lazy

import requests_mock
from django_webtest import WebTest
from freezegun import freeze_time
from maykin_2fa.test import disable_admin_mfa
from requests.exceptions import RequestException

from nrc.accounts.tests.factories import SuperUserFactory, UserFactory
from nrc.datamodel.tests.factories import (
    AbonnementFactory,
    FilterGroupFactory,
    KanaalFactory,
    NotificatieResponseFactory,
)


@disable_admin_mfa()
@freeze_time("2022-01-01T12:00:00")
@override_settings(
    LOG_NOTIFICATIONS_IN_DB=True,
)
class AbonnementAdminWebTest(WebTest):
    maxdiff = None
    changelist_url = reverse_lazy("admin:datamodel_abonnement_changelist")
    action_url = reverse_lazy("admin:check_all_callback_urls")

    def setUp(self):
        self.user = SuperUserFactory.create()
        self.kanaal = KanaalFactory.create(filters=["object_type"])
        self.abonnement = AbonnementFactory.create()
        FilterGroupFactory.create(abonnement=self.abonnement, kanaal=self.kanaal)
        NotificatieResponseFactory.create_batch(
            100, abonnement=self.abonnement, notificatie__kanaal=self.kanaal
        )

    @tag("gh-157")
    def test_delete_abonnement_hide_notificatie_responses(self):
        """
        Regression test for https://github.com/open-zaak/open-notificaties/issues/157
        """
        response = self.app.get(
            reverse(
                "admin:datamodel_abonnement_delete",
                kwargs={"object_id": self.abonnement.pk},
            ),
            user=self.user,
        )
        summary_text = response.html.find("div", {"id": "content"}).find("ul").text

        self.assertIn("Notificatie responses: 100", summary_text)

        deleted_objects = response.html.find("ul", {"id": "deleted-objects"}).text

        self.assertNotIn("Notificatie response", deleted_objects)

    @tag("gh-157")
    def test_bulk_delete_abonnement_hide_notificatie_responses(self):
        """
        Regression test for https://github.com/open-zaak/open-notificaties/issues/157
        """
        response = self.app.get(self.changelist_url, user=self.user)

        form = response.forms["changelist-form"]
        form["action"] = "delete_selected"
        form["_selected_action"] = [self.abonnement.pk]

        response = form.submit()

        summary_text = response.html.find("div", {"id": "content"}).find("ul").text

        self.assertIn("Notificatie responses: 100", summary_text)

        # Deleted objects list has no ID in bulk delete view
        deleted_objects = (
            response.html.find("div", {"id": "content"}).find_all("ul")[1].text
        )

        self.assertNotIn("Notificatie response", deleted_objects)

    @tag("gh-108")
    @requests_mock.Mocker()
    def test_abonnement_list_check_if_callback_urls_are_reachable(self, m):
        """
        Test that the callback URL statuses can be checked by using the admin action
        """
        self.abonnement.delete()

        abonnement_url_reachable = AbonnementFactory.create(
            callback_url="http://reachable.local/foo",
            auth="Token 1234",
        )
        abonnement_url_unreachable = AbonnementFactory.create(
            callback_url="http://unreachable.local/foo",
            auth="Token 1234",
        )
        abonnement_url_unreachable_duplicate = AbonnementFactory.create(
            callback_url="http://unreachable.local/foo",
            auth="Token 1234",
        )
        abonnement_url_incorrect_auth = AbonnementFactory.create(
            callback_url="http://incorrect.auth.local/foo",
            auth="Token 4321",
        )

        m.post("http://reachable.local/foo", status_code=204)
        m.post("http://unreachable.local/foo", status_code=403)
        m.post("http://incorrect.auth.local/foo", exc=RequestException)

        response = self.app.get(self.changelist_url, user=self.user)

        row_incorrect_auth, row_unreachable, row_unreachable2, row_reachable = (
            response.html.find("tbody").find_all("tr")
        )

        with self.subTest("initial callback statuses are unknown"):
            self.assertEqual(
                row_incorrect_auth.find_all("td")[1].text,
                abonnement_url_incorrect_auth.callback_url,
            )
            self.assertEqual(
                row_incorrect_auth.find_all("td")[2].find("img").attrs["alt"], "None"
            )

            self.assertEqual(
                row_unreachable.find_all("td")[1].text,
                abonnement_url_unreachable.callback_url,
            )
            self.assertEqual(
                row_unreachable.find_all("td")[2].find("img").attrs["alt"], "None"
            )

            self.assertEqual(
                row_unreachable2.find_all("td")[1].text,
                abonnement_url_unreachable_duplicate.callback_url,
            )
            self.assertEqual(
                row_unreachable2.find_all("td")[2].find("img").attrs["alt"], "None"
            )

            self.assertEqual(
                row_reachable.find_all("td")[1].text,
                abonnement_url_reachable.callback_url,
            )
            self.assertEqual(
                row_reachable.find_all("td")[2].find("img").attrs["alt"], "None"
            )

        form = response.forms[1]
        form["action"] = "check_callback_url_status"
        form["_selected_action"] = [
            abonnement_url_reachable.pk,
            abonnement_url_unreachable.pk,
            abonnement_url_incorrect_auth.pk,
        ]

        response = form.submit().follow()

        row_incorrect_auth, row_unreachable, row_unreachable2, row_reachable = (
            response.html.find("tbody").find_all("tr")
        )
        with self.subTest("callback statuses are known"):
            self.assertEqual(
                row_incorrect_auth.find_all("td")[1].text,
                abonnement_url_incorrect_auth.callback_url,
            )
            self.assertEqual(
                row_incorrect_auth.find_all("td")[2].find("img").attrs["alt"], "False"
            )

            self.assertEqual(
                row_unreachable.find_all("td")[1].text,
                abonnement_url_unreachable.callback_url,
            )
            self.assertEqual(
                row_unreachable.find_all("td")[2].find("img").attrs["alt"], "False"
            )

            # This row is marked as false despite not being selected for the action,
            # because it has the same callback URL and auth as another selected Subscription
            self.assertEqual(
                row_unreachable2.find_all("td")[1].text,
                abonnement_url_unreachable_duplicate.callback_url,
            )
            self.assertEqual(
                row_unreachable2.find_all("td")[2].find("img").attrs["alt"], "False"
            )

            self.assertEqual(
                row_reachable.find_all("td")[1].text,
                abonnement_url_reachable.callback_url,
            )
            self.assertEqual(
                row_reachable.find_all("td")[2].find("img").attrs["alt"], "True"
            )

        filtered_response = self.app.get(
            f"{self.changelist_url}?callback_url_reachable=false", user=self.user
        )

        row_incorrect_auth, row_unreachable, row_unreachable2 = (
            filtered_response.html.find("tbody").find_all("tr")
        )
        with self.subTest("callback statuses are known"):
            self.assertEqual(
                row_incorrect_auth.find_all("td")[1].text,
                abonnement_url_incorrect_auth.callback_url,
            )
            self.assertEqual(
                row_incorrect_auth.find_all("td")[2].find("img").attrs["alt"], "False"
            )

            self.assertEqual(
                row_unreachable.find_all("td")[1].text,
                abonnement_url_unreachable.callback_url,
            )
            self.assertEqual(
                row_unreachable.find_all("td")[2].find("img").attrs["alt"], "False"
            )

            self.assertEqual(
                row_unreachable2.find_all("td")[1].text,
                abonnement_url_unreachable_duplicate.callback_url,
            )
            self.assertEqual(
                row_unreachable2.find_all("td")[2].find("img").attrs["alt"], "False"
            )

    @tag("gh-108")
    @requests_mock.Mocker()
    def test_abonnement_list_check_if_callback_urls_are_reachable_with_custom_button(
        self, m
    ):
        """
        Test that the callback URL statuses can be checked by using the button that
        triggers the admin action with all Abonnementen
        """
        self.abonnement.delete()

        abonnement_url_reachable = AbonnementFactory.create(
            callback_url="http://reachable.local/foo",
            auth="Token 1234",
        )
        abonnement_url_unreachable = AbonnementFactory.create(
            callback_url="http://unreachable.local/foo",
            auth="Token 1234",
        )
        abonnement_url_unreachable_duplicate = AbonnementFactory.create(
            callback_url="http://unreachable.local/foo",
            auth="Token 1234",
        )
        abonnement_url_incorrect_auth = AbonnementFactory.create(
            callback_url="http://incorrect.auth.local/foo",
            auth="Token 4321",
        )

        m.post("http://reachable.local/foo", status_code=204)
        m.post("http://unreachable.local/foo", status_code=403)
        m.post("http://incorrect.auth.local/foo", exc=RequestException)

        response = self.app.get(self.changelist_url, user=self.user)

        row_incorrect_auth, row_unreachable, row_unreachable2, row_reachable = (
            response.html.find("tbody").find_all("tr")
        )

        with self.subTest("initial callback statuses are unknown"):
            self.assertEqual(
                row_incorrect_auth.find_all("td")[1].text,
                abonnement_url_incorrect_auth.callback_url,
            )
            self.assertEqual(
                row_incorrect_auth.find_all("td")[2].find("img").attrs["alt"], "None"
            )

            self.assertEqual(
                row_unreachable.find_all("td")[1].text,
                abonnement_url_unreachable.callback_url,
            )
            self.assertEqual(
                row_unreachable.find_all("td")[2].find("img").attrs["alt"], "None"
            )

            self.assertEqual(
                row_unreachable2.find_all("td")[1].text,
                abonnement_url_unreachable_duplicate.callback_url,
            )
            self.assertEqual(
                row_unreachable2.find_all("td")[2].find("img").attrs["alt"], "None"
            )

            self.assertEqual(
                row_reachable.find_all("td")[1].text,
                abonnement_url_reachable.callback_url,
            )
            self.assertEqual(
                row_reachable.find_all("td")[2].find("img").attrs["alt"], "None"
            )

        response = self.app.get(
            self.action_url,
            user=self.user,
            headers={"Referer": str(self.changelist_url)},
        ).follow()

        row_incorrect_auth, row_unreachable, row_unreachable2, row_reachable = (
            response.html.find("tbody").find_all("tr")
        )
        with self.subTest("callback statuses are known"):
            self.assertEqual(
                row_incorrect_auth.find_all("td")[1].text,
                abonnement_url_incorrect_auth.callback_url,
            )
            self.assertEqual(
                row_incorrect_auth.find_all("td")[2].find("img").attrs["alt"], "False"
            )

            self.assertEqual(
                row_unreachable.find_all("td")[1].text,
                abonnement_url_unreachable.callback_url,
            )
            self.assertEqual(
                row_unreachable.find_all("td")[2].find("img").attrs["alt"], "False"
            )

            # This row is marked as false despite not being selected for the action,
            # because it has the same callback URL and auth as another selected Subscription
            self.assertEqual(
                row_unreachable2.find_all("td")[1].text,
                abonnement_url_unreachable_duplicate.callback_url,
            )
            self.assertEqual(
                row_unreachable2.find_all("td")[2].find("img").attrs["alt"], "False"
            )

            self.assertEqual(
                row_reachable.find_all("td")[1].text,
                abonnement_url_reachable.callback_url,
            )
            self.assertEqual(
                row_reachable.find_all("td")[2].find("img").attrs["alt"], "True"
            )

    def test_check_all_callback_urls_not_allowed_for_non_staff_user(self):
        non_staff_user = UserFactory(is_staff=False)
        response = self.app.get(
            self.action_url,
            user=non_staff_user,
            headers={"Referer": str(self.changelist_url)},
        )

        login_url = reverse("admin:login")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.location, f"{login_url}?next={self.action_url}")
