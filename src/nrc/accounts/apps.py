from io import StringIO

from django.apps import AppConfig, apps
from django.contrib.contenttypes.management import create_contenttypes
from django.core.management import call_command
from django.db.models.signals import post_migrate


def update_admin_index(sender, **kwargs):
    from django_admin_index.models import AppGroup

    AppGroup.objects.all().delete()

    # Make sure project models are registered.
    project_name = __name__.split(".")[0]

    for app_config in apps.get_app_configs():
        if app_config.name.startswith(project_name):
            create_contenttypes(app_config, verbosity=0)

    call_command("loaddata", "default_admin_index", verbosity=0, stdout=StringIO())


class AccountsConfig(AppConfig):
    name = "nrc.accounts"

    def ready(self):
        from . import metrics  # noqa
        from . import signals  # noqa

        # enforce some fixtures after migrating
        post_migrate.connect(update_admin_index, sender=self)
