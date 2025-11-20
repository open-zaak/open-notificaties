import json
from collections import OrderedDict
from unittest.mock import patch

from django.test import override_settings
from django.urls import reverse
from django.utils.timezone import now

from django_webtest import WebTest
from freezegun import freeze_time
from maykin_2fa.test import disable_admin_mfa

from nrc.accounts.tests.factories import SuperUserFactory
from nrc.datamodel.models import Notificatie, NotificatieResponse
from nrc.datamodel.tests.factories import (
    AbonnementFactory,
    FilterGroupFactory,
    KanaalFactory,
    NotificatieFactory,
    NotificatieResponseFactory,
)


@disable_admin_mfa()
@freeze_time("2022-01-01T12:00:00")
@override_settings(
    LOG_NOTIFICATIONS_IN_DB=True,
)
@patch("nrc.api.serializers.deliver_message.delay")
@patch("nrc.api.serializers.deliver_cloudevent.delay")
class NotificationAdminWebTest(WebTest):
    maxdiff = None

    @classmethod
    def setUpTestData(cls):
        cls.user = SuperUserFactory.create()
        cls.kanaal = KanaalFactory.create(filters=["object_type"])
        cls.abonnement = AbonnementFactory.create()
        FilterGroupFactory.create(abonnement=cls.abonnement, kanaal=cls.kanaal)

        cls.cloudevent_abonnement = AbonnementFactory.create(send_cloudevents=True)
        FilterGroupFactory.create(
            abonnement=cls.cloudevent_abonnement, kanaal=cls.kanaal
        )

        cls.forwarded_msg = {
            "actie": "create",
            "kanaal": cls.kanaal.naam,
            "source": "demo.maykin.nl",
            "resource": "demo",
            "kenmerken": OrderedDict({"objectType": "https://example.com"}),
            "hoofdObject": "https://example.com",
            "resourceUrl": "https://example.com",
            "aanmaakdatum": now(),
        }

        cls.expected_cloudevent = {
            "source": "demo.maykin.nl",
            "type": f"nl.overheid.{cls.kanaal.naam}.demo.create",
            "specversion": "1.0",
            "time": cls.forwarded_msg["aanmaakdatum"].strftime("%Y-%m-%dT%H:%M:%SZ"),
            "subject": "https://example.com",
            "datacontenttype": "application/json",
            "data": {
                "objectType": "https://example.com",
                "hoofdObject": "https://example.com",
            },
        }

    def test_create_notification(self, _, mock_deliver_message):
        """
        Verify that a notification is sent when it is created via the admin
        """
        response = self.app.get(
            reverse("admin:datamodel_notificatie_add"), user=self.user
        )

        form = response.forms["notificatie_form"]

        form["forwarded_msg"] = json.dumps(self.forwarded_msg, default=str)
        form["kanaal"] = self.kanaal.pk

        response = form.submit()

        self.assertEqual(response.status_code, 302)

        # Notification should be sent
        mock_deliver_message.assert_called_once_with(
            self.abonnement.id,
            self.forwarded_msg,
            notificatie_id=Notificatie.objects.get().id,
            attempt=1,
        )
        # Verify that only one Notificatie was created (via the admin)
        self.assertEqual(Notificatie.objects.count(), 1)

    def test_resend_notification(self, _, mock_deliver_message):
        """
        Verify that a notification is scheduled when it is saved via the admin
        """
        notificatie = NotificatieFactory.create(forwarded_msg=self.forwarded_msg)
        NotificatieResponseFactory.create(
            notificatie=notificatie, abonnement=self.abonnement
        )

        response = self.app.get(
            reverse("admin:datamodel_notificatie_change", args=(notificatie.pk,)),
            user=self.user,
        )

        form = response.forms["notificatie_form"]
        response = form.submit()

        self.assertEqual(response.status_code, 302)

        # Notification should be scheduled
        mock_deliver_message.assert_called_once_with(
            self.abonnement.id,
            self.forwarded_msg,
            notificatie_id=notificatie.id,
            attempt=2,
        )
        # Verify that no new Notificatie was created
        self.assertEqual(Notificatie.objects.count(), 1)
        # Verify that previous NotificatieResponses are not deleted
        self.assertEqual(NotificatieResponse.objects.count(), 1)

    def test_resend_notification_action(self, _, mock_deliver_message):
        """
        Verify that a notification is scheduled when it is saved via the admin
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

        # Two notifications should be scheduled
        self.assertEqual(mock_deliver_message.call_count, 2)
        # Verify that no new Notificaties were created
        self.assertEqual(Notificatie.objects.count(), 3)
        # Verify that old NotificatieResponses are not deleted
        self.assertEqual(NotificatieResponse.objects.count(), 3)

        # Remaining response should belong to the Notification that was not selected
        notificatie3.refresh_from_db()
        self.assertEqual(notificatie3.notificatieresponse_set.count(), 1)

    def test_create_notification_as_cloudevent(self, mock_deliver_cloudevent, _):
        response = self.app.get(
            reverse("admin:datamodel_notificatie_add"), user=self.user
        )

        form = response.forms["notificatie_form"]

        form["forwarded_msg"] = json.dumps(self.forwarded_msg, default=str)
        form["kanaal"] = self.kanaal.pk

        response = form.submit()

        self.assertEqual(response.status_code, 302)

        # Cloudevent should be sent
        mock_deliver_cloudevent.assert_called_once_with(
            self.cloudevent_abonnement.id,
            self.expected_cloudevent
            | {"id": mock_deliver_cloudevent.call_args[0][1]["id"]},
            notificatie_id=Notificatie.objects.get().id,
            attempt=1,
        )

        # Verify that only one Notificatie was created (via the admin)
        self.assertEqual(Notificatie.objects.count(), 1)

    def test_resend_notification_as_cloudevent(self, mock_deliver_cloudevent, _):
        notificatie = NotificatieFactory.create(forwarded_msg=self.forwarded_msg)
        NotificatieResponseFactory.create(
            notificatie=notificatie, abonnement=self.abonnement
        )

        response = self.app.get(
            reverse("admin:datamodel_notificatie_change", args=(notificatie.pk,)),
            user=self.user,
        )

        form = response.forms["notificatie_form"]
        response = form.submit()

        self.assertEqual(response.status_code, 302)

        # Cloudevent should be sent
        mock_deliver_cloudevent.assert_called_once_with(
            self.cloudevent_abonnement.id,
            self.expected_cloudevent
            | {"id": mock_deliver_cloudevent.call_args[0][1]["id"]},
            notificatie_id=Notificatie.objects.get().id,
            attempt=2,
        )
        # Verify that no new Notificatie was created
        self.assertEqual(Notificatie.objects.count(), 1)

        self.assertEqual(NotificatieResponse.objects.count(), 1)

    def test_resend_notification_action_as_cloudevent(self, mock_deliver_cloudevent, _):
        notificatie1 = NotificatieFactory.create(forwarded_msg=self.forwarded_msg)
        NotificatieResponseFactory.create(
            notificatie=notificatie1, abonnement=self.cloudevent_abonnement
        )
        notificatie2 = NotificatieFactory.create(forwarded_msg=self.forwarded_msg)
        NotificatieResponseFactory.create(
            notificatie=notificatie2, abonnement=self.cloudevent_abonnement
        )
        notificatie3 = NotificatieFactory.create(forwarded_msg=self.forwarded_msg)
        NotificatieResponseFactory.create(
            notificatie=notificatie3, abonnement=self.cloudevent_abonnement
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

        # Two notifications should be scheduled
        self.assertEqual(mock_deliver_cloudevent.call_count, 2)
        # Verify that no new Notificaties were created
        self.assertEqual(Notificatie.objects.count(), 3)
        # Verify that old NotificatieResponses are not deleted
        self.assertEqual(NotificatieResponse.objects.count(), 3)

        # Remaining response should belong to the Notification that was not selected
        notificatie3.refresh_from_db()
        self.assertEqual(notificatie3.notificatieresponse_set.count(), 1)
