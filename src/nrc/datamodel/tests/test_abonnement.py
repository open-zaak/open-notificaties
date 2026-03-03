from django_test_migrations.contrib.unittest_case import MigratorTestCase


class MergeAbonnementClientIDFieldsTests(MigratorTestCase):
    """Test for datamigration 0023_merge_duplicate_client_id_field"""

    migrate_from = ("datamodel", "0022_cloudeventfilter")
    migrate_to = ("datamodel", "0023_merge_duplicate_client_id_field")

    def prepare(self):
        Abonnement = self.old_state.apps.get_model("datamodel", "Abonnement")
        Abonnement.objects.create(client_id="some-id", auth_client_id="some-other-id")
        Abonnement.objects.create(client_id="some-id2", auth_client_id="")
        Abonnement.objects.create(client_id="", auth_client_id="some-other-id2")

    def test_migration_0023(self):
        Abonnement = self.new_state.apps.get_model("datamodel", "Abonnement")

        assert Abonnement.objects.count() == 3
        assert Abonnement.objects.filter(client_id="some-id").count() == 1
        assert Abonnement.objects.filter(client_id="some-id2").count() == 1
        assert Abonnement.objects.filter(client_id="some-other-id2").count() == 1
