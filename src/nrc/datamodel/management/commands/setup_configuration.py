from argparse import RawTextHelpFormatter

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from vng_api_common.authorizations.models import AuthorizationsConfig
from vng_api_common.constants import ComponentTypes
from vng_api_common.models import APICredential, JWTSecret


class Command(BaseCommand):
    help = "Setup the initial necessary configuration"

    def create_parser(self, *args, **kwargs):
        parser = super().create_parser(*args, **kwargs)
        parser.formatter_class = RawTextHelpFormatter
        return parser

    def add_arguments(self, parser):
        parser.add_argument(
            "authorizations_api_root",
            help="Specifies the API root for the Authorizations API\n"
            "Used to create credentials to connect Open Notificaties to Authorizations API\n\n"
            "Example: https://open-zaak.utrecht.nl/autorisaties/api/v1/",
        )
        parser.add_argument(
            "municipality",
            help="Municipality to which this installation belongs\n"
            "Used in client IDs for API credentials\n\n"
            "Example: Utrecht",
        )
        parser.add_argument(
            "openzaak_to_notif_secret",
            help="Secret used for the Application that allows Open Zaak to retrieve notifications\n\n"
            "Example: cuohyKZ3lM2R",
        )
        parser.add_argument(
            "notif_to_openzaak_secret",
            help="Secret used for the Application that allows Notifications API to retrieve authorizations\n\n"
            "Example: FP6oB8N6cMkr",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        # For the steps below, see:
        # https://open-zaak.readthedocs.io/en/latest/installation/configuration.html#open-notificaties

        try:
            authorizations_api_root = options["authorizations_api_root"]
            municipality = options["municipality"]
            openzaak_to_notif_secret = options["openzaak_to_notif_secret"]
            notif_to_openzaak_secret = options["notif_to_openzaak_secret"]

            # Step 1
            auth_config = AuthorizationsConfig.get_solo()
            auth_config.api_root = authorizations_api_root
            auth_config.component = ComponentTypes.nrc
            auth_config.save()

            # Step 2
            if not APICredential.objects.filter(
                api_root=authorizations_api_root
            ).exists():
                APICredential.objects.create(
                    api_root=authorizations_api_root,
                    label=f"Open Zaak {municipality}",
                    client_id=f"open-notificaties-{municipality.lower()}",
                    secret=notif_to_openzaak_secret,
                    user_id=f"open-notificaties-{municipality.lower()}",
                    user_representation=f"Open Notificaties {municipality}",
                )

            # Step 3
            JWTSecret.objects.create(
                identifier=f"open-zaak-backend-{municipality.lower()}",
                secret=openzaak_to_notif_secret,
            )

            self.stdout.write(
                self.style.SUCCESS(
                    "Initial configuration for Open Notificaties was setup successfully"
                )
            )
        except Exception as e:
            raise CommandError(
                f"Something went wrong while setting up initial configuration: {e}"
            )
