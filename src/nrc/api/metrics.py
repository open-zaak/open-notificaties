from opentelemetry import metrics

meter = metrics.get_meter("nrc.api")

notificaties_publish_counter = meter.create_counter(
    "nrc.api.notificaties.published",
    description="Amount of notificaties created (via the API).",
    unit="1",
)

abonnement_create_counter = meter.create_counter(
    "nrc.api.abonnement.create",
    description="Amount of abonnementen created (via the API).",
    unit="1",
)

kanaal_create_counter = meter.create_counter(
    "nrc.api.kanaal.create",
    description="Amount of kanalen created (via the API).",
    unit="1",
)
