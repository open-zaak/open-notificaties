from opentelemetry import metrics

meter = metrics.get_meter("openzaak.components.notificaties")

notificaties_publish_counter = meter.create_counter(
    "nrc.notificaties.published",
    description="Amount of notificaties created (via the API).",
    unit="1",
)

abonnement_create_counter = meter.create_counter(
    "nrc.notificaties.abonnement.create",
    description="Amount of abonnementen created (via the API).",
    unit="1",
)

kanaal_create_counter = meter.create_counter(
    "nrc.notificaties.kanaal.create",
    description="Amount of kanalen created (via the API).",
    unit="1",
)
