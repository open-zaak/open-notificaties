import json
from unittest.mock import patch

from django.test import override_settings
from django.urls import reverse

from django_webtest import WebTest

from nrc.accounts.tests.factories import SuperUserFactory
from nrc.datamodel.models import Notificatie, NotificatieResponse
from nrc.datamodel.tests.factories import (
    AbonnementFactory,
    FilterGroupFactory,
    KanaalFactory,
    NotificatieFactory,
    NotificatieResponseFactory,
)


@override_settings(LOG_NOTIFICATIONS_IN_DB=True)
@patch("nrc.api.serializers.deliver_message.delay")
class NotificationAdminWebTest(WebTest):
    @classmethod
    def setUpTestData(cls):
        cls.user = SuperUserFactory.create()
        cls.kanaal = KanaalFactory.create(filters=["object_type"])
        cls.abonnement = AbonnementFactory.create()
        FilterGroupFactory.create(abonnement=cls.abonnement, kanaal=cls.kanaal)

        cls.forwarded_msg = {
            "actie": "CREATE",
            "kanaal": cls.kanaal.naam,
            "resource": "demo",
            "kenmerken": {"objectType": "https://example.com"},
            "hoofdObject": "https://example.com",
            "resourceUrl": "https://example.com",
            "aanmaakdatum": "2022-04-02T09:00:00Z",
        }

    def test_create_notification(self, mock_deliver_message):
        """
        Verify that a notification is sent when it is created via the admin
        """
        response = self.app.get(
            reverse("admin:datamodel_notificatie_add"), user=self.user
        )

        form = response.form

        form["forwarded_msg"] = json.dumps(self.forwarded_msg)
        form["kanaal"] = self.kanaal.pk

        response = form.submit()

        self.assertEqual(response.status_code, 302)

        # Notification should be sent
        mock_deliver_message.assert_called_once()
        # Verify that only one Notificatie was created (via the admin)
        self.assertEqual(Notificatie.objects.count(), 1)

    def test_resend_notification(self, mock_deliver_message):
        """
        Verify that a notification is resent when it is saved via the admin
        """
        notificatie = NotificatieFactory.create(forwarded_msg=self.forwarded_msg)
        NotificatieResponseFactory.create(
            notificatie=notificatie, abonnement=self.abonnement
        )

        response = self.app.get(
            reverse("admin:datamodel_notificatie_change", args=(notificatie.pk,)),
            user=self.user,
        )

        form = response.form
        response = form.submit()

        self.assertEqual(response.status_code, 302)

        # Notification should be resent
        mock_deliver_message.assert_called_once()
        # Verify that no new Notificatie was created
        self.assertEqual(Notificatie.objects.count(), 1)
        # Verify that previous NotificatieResponses were deleted
        self.assertEqual(NotificatieResponse.objects.count(), 0)

    def test_resend_notification_action(self, mock_deliver_message):
        """
        Verify that a notification is resent when it is saved via the admin
        """
        notificatie1 = NotificatieFactory.create(forwarded_msg=self.forwarded_msg)
        NotificatieResponseFactory.create(
            notificatie=notificatie1, abonnement=self.abonnement
        )
        notificatie2 = NotificatieFactory.create(forwarded_msg=self.forwarded_msg)
        NotificatieResponseFactory.create(
            notificatie=notificatie2, abonnement=self.abonnement
        )
        notificatie3 = NotificatieFactory.create(forwarded_msg=self.forwarded_msg)
        NotificatieResponseFactory.create(
            notificatie=notificatie3, abonnement=self.abonnement
        )

        response = self.app.get(
            reverse("admin:datamodel_notificatie_changelist"),
            user=self.user,
        )

        form = response.forms["changelist-form"]
        form["action"] = "resend_notifications"
        form["_selected_action"] = [notificatie1.pk, notificatie2.pk]

        response = form.submit()

        self.assertEqual(response.status_code, 302)

        # Two notifications should be resent
        self.assertEqual(mock_deliver_message.call_count, 2)
        # Verify that no new Notificaties were created
        self.assertEqual(Notificatie.objects.count(), 3)
        # Verify that previous two NotificatieResponses were deleted
        self.assertEqual(NotificatieResponse.objects.count(), 1)

        # Remaining response should belong to the Notification that was not selected
        notificatie3.refresh_from_db()
        self.assertEqual(notificatie3.notificatieresponse_set.count(), 1)
