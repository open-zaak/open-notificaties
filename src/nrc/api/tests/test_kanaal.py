from django.test import override_settings

from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.tests import JWTAuthMixin, get_operation_url

from nrc.datamodel.models import Kanaal
from nrc.datamodel.tests.factories import KanaalFactory


@override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
class KanalenTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_kanaal_create(self):
        """
        test /kanaal POST:
        create kanaal via POST request
        check if data were parsed to models correctly
        """
        kanaal_create_url = get_operation_url("kanaal_create")
        data = {"naam": "zaken", "documentatie_link": "https://example.com/doc"}

        response = self.client.post(kanaal_create_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        # check parsing to model
        data = response.json()
        kanaal = Kanaal.objects.get()
        self.assertEqual(kanaal.naam, "zaken")

    def test_kanaal_create_nonunique(self):
        """
        test /kanaal POST:
        attempt to create kanaal with the same name as an existent kanaal
        check if response contents status 400
        """
        Kanaal.objects.create(naam="zaken")
        kanaal_create_url = get_operation_url("kanaal_create")
        data = {"naam": "zaken", "documentatie_link": "https://example.com/doc"}

        response = self.client.post(kanaal_create_url, data)

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

    def test_kanaal_update_delete(self):
        """
        test /kanaal PUT, DELETE:
        attempt to update and destroy kanaal via request
        check if response contents status 405
        """
        kanaal = Kanaal.objects.create(naam="zaken")
        kanaal_url = get_operation_url("kanaal_read", uuid=kanaal.uuid)
        data = {"documentatie_link": "https://example.com/doc"}

        response_put = self.client.put(kanaal_url, data)

        self.assertEqual(
            response_put.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
            response_put.data,
        )

        response_delete = self.client.delete(kanaal_url, data)

        self.assertEqual(
            response_delete.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
            response_delete.data,
        )

    def test_kanaal_filter_naam(self):
        """
        test /kanaal GET with query param (naam):
        check if filtering via query params is correct
        """
        kanaal1, kanaal2 = KanaalFactory.create_batch(2)
        assert kanaal1.naam != kanaal2.naam
        kanaal1_url = get_operation_url("kanaal_read", uuid=kanaal1.uuid)
        kanaal2_url = get_operation_url("kanaal_read", uuid=kanaal2.uuid)
        list_url = get_operation_url("kanaal_list")

        response = self.client.get(list_url, {"naam": kanaal1.naam})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        self.assertEqual(len(data), 1)
        self.assertEqual(response.data[0]["url"], f"http://testserver{kanaal1_url}")
        self.assertNotEqual(response.data[0]["url"], f"http://testserver{kanaal2_url}")
