from argparse import RawTextHelpFormatter

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from notifications_api_common.models import Subscription, NotificationsConfig

from nrc.datamodel.models import Kanaal

from vng_api_common.authorizations.models import AuthorizationsConfig
from vng_api_common.constants import ComponentTypes
from vng_api_common.models import APICredential, JWTSecret

from zgw_consumers.models.services import Service
from zgw_consumers.constants import APITypes, AuthTypes


class Command(BaseCommand):
    help = "Setup the initial necessary configuration"

    def create_parser(self, *args, **kwargs):
        parser = super(Command, self).create_parser(*args, **kwargs)
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
            "notifications_api_root", help="The URL to the Notificaties API"
        )
        parser.add_argument(
            "notifications_callback_url",
            help="The Callback URL to the Notificaties Callback API",
        )
        parser.add_argument(
            "notifications_client_id",
            help="Specify a client ID for the Autorisaties API client. If not specified, "
            "a client ID will be generated. If provided, the existing client will "
            "be looked up by this value, otherwise the label will be derived from "
            "the organization name for lookup.",
        )
        parser.add_argument(
            "authorizations_client_id",
            help="Specify a client ID for the Notifications API client. If not specified, "
            "a client ID will be generated. If provided, the existing client will "
            "be looked up by this value, otherwise the label will be derived from "
            "the organization name for lookup.",
        )
        parser.add_argument(
            "notifications_client_secret",
        )
        parser.add_argument(
            "authorizations_client_secret",
        )

    @transaction.atomic
    def handle(self, **options):
        try:
            municipality = options["municipality"]

            authorizations_api_root = options["authorizations_api_root"]
            authorizations_client_id = options["authorizations_client_id"]
            authorizations_client_secret = options["authorizations_client_secret"]

            notifications_api_root = options["notifications_api_root"]
            notifications_client_id = options["notifications_client_id"]
            notifications_client_secret = options["notifications_client_secret"]

            notifications_callback_url = options["notifications_callback_url"]

            # Step 1
            auth_config = AuthorizationsConfig.get_solo()
            auth_config.api_root = authorizations_api_root
            auth_config.component = ComponentTypes.nrc
            auth_config.save()

            # Step 2
            service, created = Service.objects.get_or_create(
                api_type=APITypes.nrc,
                api_root=notifications_api_root,
                client_id=notifications_client_id,
                secret=notifications_client_secret,
                auth_type=AuthTypes.zgw,
                user_id=notifications_client_id,
                oas=notifications_api_root + "schema/openapi.yaml",
            )
            notif_config = NotificationsConfig.get_solo()
            notif_config.notifications_api_service = service
            notif_config.save()
            Subscription.objects.get_or_create(
                callback_url=notifications_callback_url,
                client_id=notifications_client_id,
                secret=notifications_client_secret,
                channels=["autorisaties"],
            )
            Kanaal.objects.get_or_create(naam="autorisaties")

            # Step 3
            APICredential.objects.get_or_create(
                api_root=authorizations_api_root,
                label=f"Open Zaak Autorisaties API {municipality}",
                client_id=notifications_client_id,
                secret=notifications_client_secret,
                user_id=notifications_client_id,
                user_representation=f"Open Notificaties {municipality}",
            )

            # Step 4
            APICredential.objects.get_or_create(
                api_root=notifications_api_root,
                label=f"Own API {municipality}",
                client_id=notifications_client_id,
                secret=notifications_client_secret,
                user_id=notifications_client_id,
                user_representation=f"Open Notificaties {municipality}",
            )

            # Step 5
            JWTSecret.objects.get_or_create(
                identifier=authorizations_client_id,
                secret=authorizations_client_secret,
            )

            # Step 6
            JWTSecret.objects.get_or_create(
                identifier=notifications_client_id,
                secret=notifications_client_secret,
            )

        except Exception as e:
            raise CommandError(
                f"Something went wrong while setting up initial configuration: {e}"
            )
