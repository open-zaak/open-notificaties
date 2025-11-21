from django.test import override_settings

import requests_mock
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.tests import JWTAuthMixin, get_operation_url, get_validation_errors

from nrc.datamodel.models import (
    Abonnement,
    CloudEventFilterGroup,
    Filter,
    FilterGroup,
    Kanaal,
)
from nrc.datamodel.tests.factories import AbonnementFactory, KanaalFactory


@override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
class AbonnementenTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def setUp(self):
        super().setUp()

        self.m = requests_mock.Mocker()
        self.m.start()
        self.addCleanup(self.m.stop)

    def test_abonnementen_create(self):
        """
        test /abonnementen POST:
        create abonnement with nested kanalen and nested filters via POST request
        check if data were parsed to models correctly
        """
        KanaalFactory.create(
            naam="zaken", filters=["bron", "zaaktype", "vertrouwelijkheidaanduiding"]
        )
        KanaalFactory.create(naam="informatieobjecten", filters=[])
        abonnement_create_url = get_operation_url("abonnement_create")

        data = {
            "callbackUrl": "https://example.com/zrc/api/v1/callbacks",
            "auth": "Bearer YWRtaW46YWRtaW4K",
            "kanalen": [
                {
                    "naam": "zaken",
                    "filters": {
                        "bron": "082096752011",
                        "zaaktype": "example.com/api/v1/zaaktypen/5aa5c",
                        "vertrouwelijkheidaanduiding": "*",
                    },
                },
                {"naam": "informatieobjecten", "filters": {"bron": "082096752011"}},
            ],
        }

        with requests_mock.mock() as m:
            m.register_uri(
                "POST",
                "https://example.com/zrc/api/v1/callbacks",
                status_code=204,
            )
            response = self.client.post(abonnement_create_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        # check parsing to models
        data = response.json()
        abon = Abonnement.objects.get()
        filter_group = abon.filter_groups.all().order_by("id")[0]
        filters = filter_group.filters.all().order_by("id")
        filters_str = [str(f) for f in filters]

        self.assertEqual(Abonnement.objects.count(), 1)
        self.assertEqual(Kanaal.objects.count(), 2)
        self.assertEqual(FilterGroup.objects.count(), 2)
        self.assertEqual(Filter.objects.count(), 4)
        self.assertEqual(abon.callback_url, "https://example.com/zrc/api/v1/callbacks")
        self.assertEqual(filter_group.kanaal.naam, "zaken")
        self.assertEqual(
            filters_str,
            [
                "bron: 082096752011",
                "zaaktype: example.com/api/v1/zaaktypen/5aa5c",
                "vertrouwelijkheidaanduiding: *",
            ],
        )

    def test_abonnementen_create_nonexistent_kanaal(self):
        """
        test /abonnementen POST:
        attempt to create abonnement with nested nonexistent kanalen
        check if response contents status 400
        """
        self.m.post("https://example.com/zrc/api/v1/callbacks", status_code=204)
        abonnement_create_url = get_operation_url("abonnement_create")
        data = {
            "callbackUrl": "https://example.com/zrc/api/v1/callbacks",
            "auth": "Bearer YWRtaW46YWRtaW4K",
            "kanalen": [
                {
                    "naam": "zaken",
                    "filters": {
                        "bron": "082096752011",
                        "zaaktype": "example.com/api/v1/zaaktypen/5aa5c",
                        "vertrouwelijkheidaanduiding": "*",
                    },
                },
                {"naam": "informatieobjecten", "filters": {"bron": "082096752011"}},
            ],
        }

        response = self.client.post(abonnement_create_url, data)

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

    def test_abonnementen_create_cloudevent(self):
        """
        test /abonnementen POST:
        create abonnement with cloudevent filters via POST request
        check if data were parsed to models correctly
        """
        abonnement_create_url = get_operation_url("abonnement_create")

        data = {
            "callbackUrl": "https://example.com/zrc/api/v1/callbacks",
            "auth": "Bearer YWRtaW46YWRtaW4K",
            "send_cloudevents": True,
            "cloudevent_filters": [{"type_substring": "nl.overheid"}],
        }

        with requests_mock.mock() as m:
            m.register_uri(
                "POST",
                "https://example.com/zrc/api/v1/callbacks",
                status_code=204,
            )
            response = self.client.post(abonnement_create_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        # check parsing to models
        abon = Abonnement.objects.get()

        self.assertEqual(Abonnement.objects.count(), 1)
        self.assertEqual(CloudEventFilterGroup.objects.count(), 1)
        self.assertEqual(abon.callback_url, "https://example.com/zrc/api/v1/callbacks")
        self.assertTrue(abon.send_cloudevents)
        self.assertEqual(
            CloudEventFilterGroup.objects.get().type_substring, "nl.overheid"
        )

    def test_abonnement_update_kanalen(self):
        """
        test /abonnementen PUT:
        update existent abonnement which has its kanaal via request which contains another kanaal
        check if relation between abonnement and previous kanalen was removed
        check if relation between abonnement and new kanaal was created
        """
        abonnement = AbonnementFactory.create(client_id="testsuite")
        kanaal_foo = KanaalFactory.create(
            naam="foo", filters=["bron", "zaaktype", "vertrouwelijkheidaanduiding"]
        )
        KanaalFactory.create(
            naam="zaken", filters=["bron", "zaaktype", "vertrouwelijkheidaanduiding"]
        )
        abonnement.kanalen.add(kanaal_foo)
        data = {
            "callbackUrl": "https://other.url/callbacks",
            "auth": "Bearer YWRtaW46YWRtaW4K",
            "kanalen": [
                {
                    "naam": "zaken",
                    "filters": {
                        "bron": "082096752011",
                        "zaaktype": "example.com/api/v1/zaaktypen/5aa5c",
                        "vertrouwelijkheidaanduiding": "*",
                    },
                }
            ],
        }
        abonnement_update_url = get_operation_url(
            "abonnement_update", uuid=abonnement.uuid
        )

        with requests_mock.mock() as m:
            m.register_uri("POST", "https://other.url/callbacks", status_code=204)
            response = self.client.put(abonnement_update_url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        data = response.json()
        kanalen = abonnement.kanalen

        self.assertEqual(len(kanalen), 1)
        self.assertEqual(kanalen.pop().naam, "zaken")

    def test_abonnement_update_cloudevent_filters(self):
        """
        test /abonnementen PUT:
        update existent abonnement
        check if relation between abonnement and previous filter was removed
        check if relation between abonnement and new filter was created
        """
        abonnement = AbonnementFactory.create(client_id="testsuite")
        CloudEventFilterGroup.objects.create(
            abonnement=abonnement, type_substring="nl.overheid"
        )
        data = {
            "callbackUrl": "https://other.url/callbacks",
            "auth": "Bearer YWRtaW46YWRtaW4K",
            "send_cloudevents": True,
            "cloudevent_filters": [{"type_substring": "nl.overheid.test"}],
        }
        abonnement_update_url = get_operation_url(
            "abonnement_update", uuid=abonnement.uuid
        )

        with requests_mock.mock() as m:
            m.register_uri("POST", "https://other.url/callbacks", status_code=204)
            response = self.client.put(abonnement_update_url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        self.assertEqual(abonnement.cloudevent_filtergroups.count(), 1)
        self.assertEqual(
            abonnement.cloudevent_filtergroups.get().type_substring, "nl.overheid.test"
        )

    def test_abonnementen_create_inconsistent_filters(self):
        """
        test /abonnementen POST:
        create abonnement with filters inconsistent with kanaal filters
        check if response contains status 400
        """

        KanaalFactory.create(naam="zaken")
        abonnement_create_url = get_operation_url("abonnement_create")

        data = {
            "callbackUrl": "https://example.com/zrc/api/v1/callbacks",
            "auth": "Bearer YWRtaW46YWRtaW4K",
            "kanalen": [
                {
                    "naam": "zaken",
                    "filters": {
                        "bron": "082096752011",
                        "zaaktype": "example.com/api/v1/zaaktypen/5aa5c",
                        "vertrouwelijkheidaanduiding": "*",
                    },
                }
            ],
        }

        with requests_mock.mock() as m:
            m.register_uri(
                "POST",
                "https://example.com/zrc/api/v1/callbacks",
                status_code=204,
            )
            response = self.client.post(abonnement_create_url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        validation_error = get_validation_errors(response, "filters")
        self.assertEqual(validation_error["code"], "inconsistent-abonnement-filters")

    def test_abonnement_destroy(self):
        """
        test /abonnementen DELETE:
        check if destroy action is supported
        """
        abonnement = AbonnementFactory.create(client_id="testsuite")
        abonnement_url = get_operation_url("abonnement_read", uuid=abonnement.uuid)

        response = self.client.delete(abonnement_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_abonnement_list_different_clientid(self):
        """
        test /abonnementen LIST:
        check if LIST action is allowed for other client-id
        """
        abonnement1 = AbonnementFactory.create()
        abonnement2 = AbonnementFactory.create()
        assert abonnement1.client_id != "testsuite"
        assert abonnement2.client_id != "testsuite"
        url = get_operation_url("abonnement_list")

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        data = response.json()

        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]["callbackUrl"], abonnement1.callback_url)
        self.assertEqual(data[1]["callbackUrl"], abonnement2.callback_url)

    def test_abonnement_read_different_clientid(self):
        """
        test /abonnementen READ:
        check if READ action is allowed for other client-id
        """
        abonnement = AbonnementFactory.create()
        assert abonnement.client_id != "testsuite"
        abonnement_url = get_operation_url("abonnement_read", uuid=abonnement.uuid)

        response = self.client.get(abonnement_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        data = response.json()

        self.assertEqual(data["url"], f"http://testserver{abonnement_url}")
        self.assertEqual(data["callbackUrl"], abonnement.callback_url)

    def test_abonnement_update_different_client_id(self):
        """
        test /abonnementen UPDATE:
        check if READ action is allowed for other client-id
        """
        abonnement = AbonnementFactory.create()
        assert abonnement.client_id != "testsuite"
        data = {
            "callbackUrl": "https://other.url/callbacks",
            "auth": "Bearer YWRtaW46YWRtaW4K",
        }
        abonnement_url = get_operation_url("abonnement_update", uuid=abonnement.uuid)

        response = self.client.put(abonnement_url, data)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_abonnement_destroy_different_clientid(self):
        """
        test /abonnementen DELETE:
        check if destroy action is not allowed for other client-id
        """
        abonnement = AbonnementFactory.create()
        assert abonnement != "testsuite"
        abonnement_url = get_operation_url("abonnement_read", uuid=abonnement.uuid)

        response = self.client.delete(abonnement_url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @requests_mock.Mocker()
    def test_abonnementen_create_duplicate_callbacks(self, m):
        """
        test /abonnementen POST:
        create abonnement with nested kanalen and nested filters via POST request
        check if data were parsed to models correctly
        """
        m.post(
            "https://example.com/zrc/api/v1/callbacks",
            status_code=204,
        )
        KanaalFactory.create(
            naam="zaken", filters=["bron", "zaaktype", "vertrouwelijkheidaanduiding"]
        )
        KanaalFactory.create(naam="informatieobjecten", filters=["bron"])
        abonnement_create_url = get_operation_url("abonnement_create")

        data = {
            "callbackUrl": "https://example.com/zrc/api/v1/callbacks",
            "auth": "Bearer YWRtaW46YWRtaW4K",
            "kanalen": [
                {
                    "naam": "zaken",
                    "filters": {
                        "bron": "082096752011",
                        "zaaktype": "https://example.com/api/v1/zaaktypen/5aa5c",
                        "vertrouwelijkheidaanduiding": "*",
                    },
                },
                {"naam": "informatieobjecten", "filters": {"bron": "082096752011"}},
            ],
        }
        response = self.client.post(abonnement_create_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        data = {
            "callbackUrl": "https://example.com/zrc/api/v1/callbacks",
            "auth": "Bearer YWRtaW46YWRtaW4K",
            "kanalen": [
                {
                    "naam": "zaken",
                    "filters": {
                        "zaaktype": "https://example.com/api/v1/zaaktypen/deadbeaf",
                    },
                },
                {"naam": "informatieobjecten", "filters": {"bron": "082096752011"}},
            ],
        }

        response = self.client.post(abonnement_create_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
