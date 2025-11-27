from opentelemetry import metrics

meter = metrics.get_meter("opennotificaties.api")

notificaties_publish_counter = meter.create_counter(
    "opennotificaties.notificatie.publishes",
    description="Amount of notificaties created (via the API).",
    unit="1",
)

abonnement_create_counter = meter.create_counter(
    "opennotificaties.abonnement.creates",
    description="Amount of abonnementen created (via the API).",
    unit="1",
)

kanaal_create_counter = meter.create_counter(
    "opennotificaties.kanaal.creates",
    description="Amount of kanalen created (via the API).",
    unit="1",
)
