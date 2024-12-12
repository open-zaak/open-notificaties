from django.test import TestCase

from django_setup_configuration.test_utils import execute_single_step

from nrc.datamodel.models import Kanaal
from nrc.setup_configuration.kanalen import KanaalConfigurationStep

CONFIG_FILE_PATH = (
    "src/nrc/tests/setup_configuration/files/setup_config_kanalen_config.yaml"
)


class KanalenConfigurationTests(TestCase):
    def test_execute_configuration_step_success(self):
        execute_single_step(KanaalConfigurationStep, yaml_source=CONFIG_FILE_PATH)

        self.assertEqual(Kanaal.objects.count(), 7)

        (
            kanaal_autorisaties,
            kanaal_besluittypen,
            kanaal_iotypen,
            kanaal_zaaktypen,
            kanaal_zaken,
            kanaal_documenten,
            kanaal_besluiten,
        ) = Kanaal.objects.order_by("pk")

        self.assertEqual(kanaal_autorisaties.naam, "autorisaties")
        self.assertEqual(
            kanaal_autorisaties.documentatie_link,
            "http://localhost:8000/ref/kanalen/#/autorisaties",
        )
        self.assertEqual(kanaal_autorisaties.filters, [])

        self.assertEqual(kanaal_besluittypen.naam, "besluittypen")
        self.assertEqual(
            kanaal_besluittypen.documentatie_link,
            "http://localhost:8000/ref/kanalen/#/besluittypen",
        )
        self.assertEqual(kanaal_besluittypen.filters, ["catalogus"])

        self.assertEqual(kanaal_iotypen.naam, "informatieobjecttypen")
        self.assertEqual(
            kanaal_iotypen.documentatie_link,
            "http://localhost:8000/ref/kanalen/#/informatieobjecttypen",
        )
        self.assertEqual(kanaal_iotypen.filters, ["catalogus"])

        self.assertEqual(kanaal_zaaktypen.naam, "zaaktypen")
        self.assertEqual(
            kanaal_zaaktypen.documentatie_link,
            "http://localhost:8000/ref/kanalen/#/zaaktypen",
        )
        self.assertEqual(kanaal_zaaktypen.filters, ["catalogus"])

        self.assertEqual(kanaal_zaken.naam, "zaken")
        self.assertEqual(
            kanaal_zaken.documentatie_link, "http://localhost:8000/ref/kanalen/#/zaken"
        )
        self.assertEqual(
            kanaal_zaken.filters,
            ["bronorganisatie", "zaaktype", "vertrouwelijkheidaanduiding"],
        )

        self.assertEqual(kanaal_documenten.naam, "documenten")
        self.assertEqual(
            kanaal_documenten.documentatie_link,
            "http://localhost:8000/ref/kanalen/#/documenten",
        )
        self.assertEqual(
            kanaal_documenten.filters,
            ["bronorganisatie", "informatieobjecttype", "vertrouwelijkheidaanduiding"],
        )

        self.assertEqual(kanaal_besluiten.naam, "besluiten")
        self.assertEqual(
            kanaal_besluiten.documentatie_link,
            "http://localhost:8000/ref/kanalen/#/besluiten",
        )
        self.assertEqual(
            kanaal_besluiten.filters, ["verantwoordelijke_organisatie", "besluittype"]
        )

    def test_execute_configuration_step_update_existing(self):
        kanaal_zaken = Kanaal.objects.create(
            naam="zaken",
            documentatie_link="http://localhost:8000/old-documentation/zaken",
            filters=["foo", "bar"],
        )

        execute_single_step(KanaalConfigurationStep, yaml_source=CONFIG_FILE_PATH)

        self.assertEqual(Kanaal.objects.count(), 7)

        kanaal_zaken.refresh_from_db()

        self.assertEqual(kanaal_zaken.naam, "zaken")
        self.assertEqual(
            kanaal_zaken.documentatie_link, "http://localhost:8000/ref/kanalen/#/zaken"
        )
        self.assertEqual(
            kanaal_zaken.filters,
            ["bronorganisatie", "zaaktype", "vertrouwelijkheidaanduiding"],
        )

    def test_execute_configuration_step_idempotent(self):
        execute_single_step(KanaalConfigurationStep, yaml_source=CONFIG_FILE_PATH)

        self.assertEqual(Kanaal.objects.count(), 7)

        execute_single_step(KanaalConfigurationStep, yaml_source=CONFIG_FILE_PATH)

        self.assertEqual(Kanaal.objects.count(), 7)
