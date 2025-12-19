from pathlib import Path

from django.test import TestCase

from django_setup_configuration.exceptions import ConfigurationRunFailed
from django_setup_configuration.test_utils import execute_single_step

from nrc.datamodel.models import (
    Abonnement,
    CloudEventFilterGroup,
    Filter,
    FilterGroup,
    Kanaal,
)
from nrc.setup_configuration.abonnementen import AbonnementConfigurationStep

TEST_FILES = (Path(__file__).parent / "files").resolve()
CONFIG_FILE_PATH = str(TEST_FILES / "setup_config_abonnementen_config.yaml")
CONFIG_FILE_PATH_NO_FILTERS = str(
    TEST_FILES / "setup_config_abonnementen_no_filters.yaml"
)


class AbonnementenConfigurationTests(TestCase):
    def setUp(self):
        super().setUp()

        self.kanaal_zaken = Kanaal.objects.create(
            naam="zaken",
            documentatie_link="http://localhost:8000/old-documentation/zaken",
            filters=["zaaktype", "vertrouwelijkheidaanduiding"],
        )
        self.kanaal_documenten = Kanaal.objects.create(
            naam="documenten",
            documentatie_link="http://localhost:8000/old-documentation/zaken",
            filters=["informatieobjecttype", "vertrouwelijkheidaanduiding"],
        )

    def test_execute_configuration_step_success(self):
        execute_single_step(AbonnementConfigurationStep, yaml_source=CONFIG_FILE_PATH)

        self.assertEqual(Abonnement.objects.count(), 3)
        self.assertEqual(FilterGroup.objects.count(), 2)
        self.assertEqual(Filter.objects.count(), 2)

        abonnement_zaken, abonnement_documenten, abonnement_cloudevent = (
            Abonnement.objects.order_by("pk")
        )

        self.assertEqual(
            str(abonnement_zaken.uuid), "ff5a9438-6512-4c2d-b69e-6c512c466fb8"
        )
        self.assertEqual(abonnement_zaken.auth, "Token foo")
        self.assertEqual(
            abonnement_zaken.callback_url, "http://localhost:8000/api/v1/callback"
        )

        self.assertEqual(abonnement_zaken.auth_type, "api_key")
        self.assertEqual(abonnement_zaken.auth_client_id, "client-id")
        self.assertEqual(abonnement_zaken.secret, "my-secret")
        self.assertEqual(
            abonnement_zaken.oauth2_token_url, "https://auth.example.com/token"
        )
        self.assertEqual(abonnement_zaken.oauth2_scope, "read write")

        self.assertEqual(
            str(abonnement_documenten.uuid), "03baec5a-93ef-4ba6-bb73-c548c12009a2"
        )
        self.assertEqual(abonnement_documenten.auth, "Token bar")
        self.assertEqual(
            abonnement_documenten.callback_url,
            "http://localhost:8000/api/v1/other-callback",
        )

        self.assertEqual(
            str(abonnement_cloudevent.uuid), "482a09ff-286b-4d0f-a1b8-9b99c1eac0f8"
        )
        self.assertEqual(abonnement_cloudevent.auth, "Token bar")
        self.assertEqual(abonnement_cloudevent.send_cloudevents, True)
        self.assertEqual(
            abonnement_cloudevent.callback_url,
            "http://localhost:8000/api/v1/other-callback",
        )

        cloudevent_filter_group1, cloudevent_filter_group2 = (
            CloudEventFilterGroup.objects.order_by("pk")
        )
        self.assertEqual(cloudevent_filter_group1.abonnement, abonnement_cloudevent)
        self.assertEqual(cloudevent_filter_group2.abonnement, abonnement_cloudevent)
        self.assertEqual(cloudevent_filter_group1.type_substring, "zaak.created")
        self.assertEqual(cloudevent_filter_group2.type_substring, "nl.overheid")

        filter_group1, filter_group2 = FilterGroup.objects.order_by("pk")

        self.assertEqual(filter_group1.kanaal, self.kanaal_zaken)
        self.assertEqual(filter_group1.abonnement, abonnement_zaken)
        self.assertEqual(filter_group2.kanaal, self.kanaal_documenten)
        self.assertEqual(filter_group2.abonnement, abonnement_documenten)

        filter1, filter2 = filter_group1.filters.order_by("pk")

        self.assertEqual(filter1.key, "zaaktype")
        self.assertEqual(
            filter1.value,
            "http://open-zaak.local/catalogi/api/v1/zaaktypen/d0b3a90d-7959-4699-8bdb-bf228aef5e21",
        )
        self.assertEqual(filter2.key, "vertrouwelijkheidaanduiding")
        self.assertEqual(filter2.value, "beperkt_openbaar")

    def test_execute_configuration_step_update_existing(self):
        abonnement_zaken = Abonnement.objects.create(
            uuid="ff5a9438-6512-4c2d-b69e-6c512c466fb8",
            auth="Token old",
            callback_url="http://localhost:8000/outdated",
        )
        filter_group = FilterGroup.objects.create(
            kanaal=self.kanaal_zaken,
            abonnement=abonnement_zaken,
        )
        filter = Filter.objects.create(
            key="zaaktype", value="old", filter_group=filter_group
        )

        execute_single_step(AbonnementConfigurationStep, yaml_source=CONFIG_FILE_PATH)

        self.assertEqual(Abonnement.objects.count(), 3)
        self.assertEqual(FilterGroup.objects.count(), 2)
        self.assertEqual(Filter.objects.count(), 2)

        abonnement_zaken.refresh_from_db()

        self.assertEqual(
            str(abonnement_zaken.uuid), "ff5a9438-6512-4c2d-b69e-6c512c466fb8"
        )
        self.assertEqual(abonnement_zaken.auth, "Token foo")
        self.assertEqual(
            abonnement_zaken.callback_url, "http://localhost:8000/api/v1/callback"
        )
        self.assertEqual(abonnement_zaken.auth_type, "api_key")
        self.assertEqual(abonnement_zaken.auth_client_id, "client-id")
        self.assertEqual(abonnement_zaken.secret, "my-secret")
        self.assertEqual(
            abonnement_zaken.oauth2_token_url, "https://auth.example.com/token"
        )
        self.assertEqual(abonnement_zaken.oauth2_scope, "read write")

        filter_group.refresh_from_db()

        self.assertEqual(filter_group.kanaal, self.kanaal_zaken)
        self.assertEqual(filter_group.abonnement, abonnement_zaken)

        filter.refresh_from_db()

        self.assertEqual(filter.key, "zaaktype")
        self.assertEqual(
            filter.value,
            "http://open-zaak.local/catalogi/api/v1/zaaktypen/d0b3a90d-7959-4699-8bdb-bf228aef5e21",
        )

    def test_execute_configuration_step_idempotent(self):
        execute_single_step(AbonnementConfigurationStep, yaml_source=CONFIG_FILE_PATH)

        self.assertEqual(Abonnement.objects.count(), 3)
        self.assertEqual(FilterGroup.objects.count(), 2)
        self.assertEqual(Filter.objects.count(), 2)

        execute_single_step(AbonnementConfigurationStep, yaml_source=CONFIG_FILE_PATH)

        self.assertEqual(Abonnement.objects.count(), 3)
        self.assertEqual(FilterGroup.objects.count(), 2)
        self.assertEqual(Filter.objects.count(), 2)

    def test_execute_configuration_step_fails_if_kanaal_does_not_exist(self):
        self.kanaal_zaken.delete()

        with self.assertRaises(ConfigurationRunFailed) as cm:
            execute_single_step(
                AbonnementConfigurationStep, yaml_source=CONFIG_FILE_PATH
            )
        self.assertEqual(str(cm.exception), "No Kanaal with name zaken exists")

    def test_execute_configuration_step_fails_if_no_filters_are_specified(self):
        self.kanaal_zaken.delete()

        with self.assertRaises(ConfigurationRunFailed) as cm:
            execute_single_step(
                AbonnementConfigurationStep, yaml_source=CONFIG_FILE_PATH_NO_FILTERS
            )
        self.assertEqual(
            str(cm.exception),
            "Abonnement 03baec5a-93ef-4ba6-bb73-c548c12009a2 must either have `kanalen` or `cloudevent_filters` specified",
        )
