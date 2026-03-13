from uuid import uuid4

from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from django_webtest import WebTest
from freezegun import freeze_time
from maykin_2fa.test import disable_admin_mfa

from nrc.accounts.tests.factories import SuperUserFactory
from nrc.datamodel.models import (
    CloudEvent,
    CloudEventResponse,
    NotificationTypes,
    ScheduledNotification,
)
from nrc.datamodel.tests.factories import (
    AbonnementFactory,
    CloudEventFactory,
    CloudEventFilterGroupFactory,
    CloudEventResponseFactory,
)


@disable_admin_mfa()
@freeze_time("2022-01-01T12:00:00")
@override_settings(
    LOG_NOTIFICATIONS_IN_DB=True,
)
class CloudEventAdminWebTest(WebTest):
    maxdiff = None

    @classmethod
    def setUpTestData(cls):
        cls.user = SuperUserFactory.create()
        cls.abonnement = AbonnementFactory.create(send_cloudevents=True)
        CloudEventFilterGroupFactory(abonnement=cls.abonnement)

        cls.event = {
            "specversion": "1.0",
            "type": "nl.overheid.zaken.zaak.created",
            "source": "oz",
            "subject": str(uuid4()),
            "id": str(uuid4()),
            "time": timezone.now(),
            "dataschema": "",
            "datacontenttype": "application/json",
            "data": "{}",
        }

    def test_create_cloudevent(self):
        """
        Verify that a cloudevent is sent when it is created via the admin
        """
        response = self.app.get(
            reverse("admin:datamodel_cloudevent_add"), user=self.user
        )

        form = response.forms["cloudevent_form"]

        form["specversion"] = self.event["specversion"]
        form["type"] = self.event["type"]
        form["source"] = self.event["source"]
        form["subject"] = self.event["subject"]
        form["id"] = self.event["id"]
        form["time_0"] = self.event["time"].strftime("%Y-%m-%d")
        form["time_1"] = self.event["time"].strftime("%H:%M:%S")
        form["datacontenttype"] = self.event["datacontenttype"]
        form["data"] = self.event["data"]

        response = form.submit()

        self.assertEqual(response.status_code, 302)

        # Verify that only one Cloudevent was created (via the admin)
        self.assertEqual(CloudEvent.objects.count(), 1)
        self.assertEqual(ScheduledNotification.objects.count(), 1)

        scheduled_notif = ScheduledNotification.objects.get()
        self.assertEqual(scheduled_notif.type, NotificationTypes.cloudevent)
        self.assertEqual(scheduled_notif.attempt, 0)
        self.assertEqual(scheduled_notif.subs.count(), 0)
        self.assertEqual(
            scheduled_notif.task_args,
            self.event
            | {
                "time": self.event["time"].strftime("%Y-%m-%dT%H:%M:%SZ"),
            },
        )

    def test_resend_cloudevent(self):
        """
        Verify that a cloudevent is scheduled when it is saved via the admin
        """
        cloudevent = CloudEventFactory.create(**self.event)
        CloudEventResponseFactory.create(
            cloudevent=cloudevent, abonnement=self.abonnement
        )

        response = self.app.get(
            reverse("admin:datamodel_cloudevent_change", args=(cloudevent.pk,)),
            user=self.user,
        )

        form = response.forms["cloudevent_form"]
        response = form.submit()

        self.assertEqual(response.status_code, 302)

        # Verify that no new Cloudevent was created
        self.assertEqual(CloudEvent.objects.count(), 1)

        self.assertEqual(ScheduledNotification.objects.count(), 1)

        # Verify that previous CloudeventResponses are not deleted
        self.assertEqual(CloudEventResponse.objects.count(), 1)

        scheduled_notif = ScheduledNotification.objects.get()
        self.assertEqual(scheduled_notif.type, NotificationTypes.cloudevent)
        self.assertEqual(scheduled_notif.attempt, 0)
        self.assertEqual(scheduled_notif.subs.count(), 0)
        self.assertEqual(
            scheduled_notif.task_args,
            self.event
            | {
                "time": self.event["time"].strftime("%Y-%m-%dT%H:%M:%SZ"),
            },
        )

    def test_resend_cloudevent_action(self):
        """
        Verify that a cloudevent is scheduled when it is saved via the admin
        """
        cloudevent1 = CloudEventFactory.create(**self.event)
        CloudEventResponseFactory.create(
            cloudevent=cloudevent1, abonnement=self.abonnement
        )
        cloudevent2 = CloudEventFactory.create(**self.event | {"id": str(uuid4())})
        CloudEventResponseFactory.create(
            cloudevent=cloudevent2, abonnement=self.abonnement
        )
        cloudevent3 = CloudEventFactory.create(**self.event | {"id": str(uuid4())})
        CloudEventResponseFactory.create(
            cloudevent=cloudevent3, abonnement=self.abonnement
        )

        response = self.app.get(
            reverse("admin:datamodel_cloudevent_changelist"),
            user=self.user,
        )

        form = response.forms["changelist-form"]
        form["action"] = "resend_cloudevents"
        form["_selected_action"] = [cloudevent1.pk, cloudevent2.pk]

        response = form.submit()

        self.assertEqual(response.status_code, 302)

        # Verify that no new Cloudevents were created
        self.assertEqual(CloudEvent.objects.count(), 3)

        self.assertEqual(ScheduledNotification.objects.count(), 2)

        # Verify that old CloudeventResponses are not deleted
        self.assertEqual(CloudEventResponse.objects.count(), 3)

        # Remaining response should belong to the Cloudevent that was not selected
        cloudevent3.refresh_from_db()
        self.assertEqual(cloudevent3.cloudeventresponse_set.count(), 1)
