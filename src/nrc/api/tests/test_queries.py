from datetime import datetime

from django.test import TestCase, override_settings

from nrc.datamodel.models import Abonnement
from nrc.datamodel.tests.factories import (
    AbonnementFactory,
    CloudEventFilterFactory,
    CloudEventFilterGroupFactory,
    FilterFactory,
    FilterGroupFactory,
    KanaalFactory,
)

from ..serializers import CloudEventSerializer, MessageSerializer


@override_settings(LOG_NOTIFICATIONS_IN_DB=False)
class MessageSerializerQueryTests(TestCase):
    def test_create_queries(self):
        """
        Verify that the number of queries performed when running `MessageSerializer.create`
        is constant, regardless of the number of subscriptions in the database
        """
        msg = {
            "kanaal": "zaken",
            "source": "zaken.maykin.nl",
            "hoofdObject": "https://example.com/zrc/api/v1/zaken/d7a22",
            "resource": "status",
            "resourceUrl": "https://example.com/zrc/api/v1/statussen/d7a22/721c9",
            "actie": "create",
            "aanmaakdatum": datetime(2025, 1, 1, 12, 0, 0),
            "kenmerken": {
                "bron": "082096752011",
                "zaaktype": "example.com/api/v1/zaaktypen/5aa5c",
                "vertrouwelijkheidaanduiding": "zeer_geheim",
            },
        }
        serializer = MessageSerializer()
        kanaal = KanaalFactory.create(
            naam="zaken", filters=["bron", "zaaktype", "vertrouwelijkheidaanduiding"]
        )

        for num_subscriptions in (1, 10, 100):
            with self.subTest(num_subscriptions=num_subscriptions):
                Abonnement.objects.all().delete()

                AbonnementFactory.create_batch(num_subscriptions)
                # Should receive the event
                FilterGroupFactory.create_batch(10, kanaal=kanaal)
                # Should not receive the event
                FilterGroupFactory.create_batch(30)

                # Should receive the event
                matching_sub = AbonnementFactory.create()
                filter_group = FilterGroupFactory.create(
                    abonnement=matching_sub, kanaal=kanaal
                )
                FilterFactory.create(
                    filter_group=filter_group,
                    key="vertrouwelijkheidaanduiding",
                    value="zeer_geheim",
                )

                with self.assertNumQueries(3):
                    """
                    Expected three queries:
                    (1) SELECT datamodel_filtergroup based on kanaal
                    (2) SELECT datamodel_filter for the results from query 1
                    (3) INSERT INTO datamodel_schedulednotification
                    """
                    serializer.create(msg)


@override_settings(LOG_NOTIFICATIONS_IN_DB=False)
class CloudEventSerializerQueryTests(TestCase):
    def test_create_queries(self):
        """
        Verify that the number of queries performed when running `CloudEventSerializer.create`
        is constant, regardless of the number of subscriptions in the database
        """
        event = {
            "specversion": "1.0",
            "type": "nl.overheid.zaken.zaak.created",
            "source": "oz",
            "subject": "1234",
            "id": "1234",
            "time": datetime(2025, 1, 1, 12, 0, 0),
            "datacontenttype": "application/json",
            "data": {
                "vertrouwelijkheidaanduiding": "zeer_geheim",
                "zaaktype": "http://openzaak.local/catalogi/api/v1/zaaktypen/1234",
            },
        }
        serializer = CloudEventSerializer()

        for num_subscriptions in (1, 10, 100):
            with self.subTest(num_subscriptions=num_subscriptions):
                Abonnement.objects.all().delete()

                AbonnementFactory.create_batch(num_subscriptions, send_cloudevents=True)
                # Should receive the event
                CloudEventFilterGroupFactory.create_batch(
                    10,
                    type_substring="nl.overheid.zaken",
                    abonnement__send_cloudevents=True,
                )
                # Should not receive the event
                CloudEventFilterGroupFactory.create_batch(
                    30, type_substring="foo", abonnement__send_cloudevents=True
                )

                # Should receive the event
                matching_sub = AbonnementFactory.create(send_cloudevents=True)
                filter_group = CloudEventFilterGroupFactory.create(
                    abonnement=matching_sub, type_substring="nl.overheid.zaken"
                )
                CloudEventFilterFactory.create(
                    cloud_event_filter_group=filter_group,
                    key="vertrouwelijkheidaanduiding",
                    value="zeer_geheim",
                )

                with self.assertNumQueries(1):
                    """
                    Expected one query:

                    (1) INSERT INTO datamodel_schedulednotification
                    """
                    serializer.create(event)
