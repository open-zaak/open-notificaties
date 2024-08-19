from django.test import override_settings
from django.urls import reverse

from django_webtest import WebTest
from freezegun import freeze_time
from maykin_2fa.test import disable_admin_mfa

from nrc.accounts.tests.factories import SuperUserFactory
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

    def setUp(self):
        self.user = SuperUserFactory.create()
        self.kanaal = KanaalFactory.create(filters=["object_type"])
        self.abonnement = AbonnementFactory.create()
        FilterGroupFactory.create(abonnement=self.abonnement, kanaal=self.kanaal)
        NotificatieResponseFactory.create_batch(
            100, abonnement=self.abonnement, notificatie__kanaal=self.kanaal
        )

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
        summary_text = response.html.find("div", {"class": "content"}).find("ul").text

        self.assertIn("Notificatie responses: 100", summary_text)

        deleted_objects = response.html.find("ul", {"id": "deleted-objects"}).text

        self.assertNotIn("Notificatie response", deleted_objects)

    def test_bulk_delete_abonnement_hide_notificatie_responses(self):
        """
        Regression test for https://github.com/open-zaak/open-notificaties/issues/157
        """
        response = self.app.get(
            reverse("admin:datamodel_abonnement_changelist"),
            user=self.user,
        )

        form = response.forms["changelist-form"]
        form["action"] = "delete_selected"
        form["_selected_action"] = [self.abonnement.pk]

        response = form.submit()

        summary_text = response.html.find("div", {"class": "content"}).find("ul").text

        self.assertIn("Notificatie responses: 100", summary_text)

        # Deleted objects list has no ID in bulk delete view
        deleted_objects = (
            response.html.find("div", {"class": "content"}).find_all("ul")[1].text
        )

        self.assertNotIn("Notificatie response", deleted_objects)
