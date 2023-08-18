import requests
import json


from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from notifications_api_common.models import Subscription

from zds_client.auth import ClientAuth


class Command(BaseCommand):
    help = "Final configuration"

    def add_arguments(self, parser):
        parser.add_argument(
            "already_application_client_id",
            help="Specify a client ID that already has an application so that "
            "the new application can be created and the webhooks can be saved.",
        )
        parser.add_argument("already_application_client_secret")
        parser.add_argument(
            "callback_url",
            help="The Callback URL to the Notificaties Callback API",
        )

    @transaction.atomic
    def handle(self, **options):
        try:
            already_application_client_id = options["already_application_client_id"]
            already_application_client_secret = options[
                "already_application_client_secret"
            ]
            callback_url = options["callback_url"]

            auth = ClientAuth(
                client_id=already_application_client_id,
                secret=already_application_client_secret,
            )
            headers = {
                "Content-Type": "application/json",
                "Authorization": auth.credentials()["Authorization"],
            }

            data = json.dumps(
                {
                    "clientIds": ["open-notificaties"],
                    "label": "Notifications API Maykin",
                    "heeftAlleAutorisaties": False,
                    "autorisaties": [
                        {
                            "component": "nrc",
                            "scopes": [
                                "notificaties.consumeren",
                                "notificaties.publiceren",
                            ],
                        },
                        {"component": "ac", "scopes": ["autorisaties.lezen"]},
                    ],
                }
            )

            response = requests.get(
                url="https://test.openzaak.nl/autorisaties/api/v1/applicaties/consumer?clientId=open-notificaties",
                headers=headers,
            )

            if response.status_code == 200:
                requests.put(
                    url="https://test.openzaak.nl/autorisaties/api/v1/applicaties",
                    data=data,
                    headers=headers,
                )
                webhook = Subscription.objects.get(callback_url=callback_url)
                webhook.register()
            else:
                raise CommandError("You have to create an application first")

        except Exception as e:
            raise CommandError(
                f"Something went wrong while setting up configuration: {e}"
            )
