import factory
import factory.fuzzy


class AbonnementFactory(factory.django.DjangoModelFactory):
    callback_url = factory.Faker("url")
    auth = (
        "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiIsImNsaWVudF9pZG"
        "VudGlmaWVyIjoienJjIn0.eyJpc3MiOiJ6cmMiLCJpYXQiOjE1NTI5OTM"
        "4MjcsInpkcyI6eyJzY29wZXMiOlsiemRzLnNjb3Blcy56YWtlbi5hYW5t"
        "YWtlbiJdLCJ6YWFrdHlwZXMiOlsiaHR0cDovL3p0Yy5ubC9hcGkvdjEve"
        "mFha3R5cGUvMTIzNCJdfX0.NHcWwoRYMuZ5IoUAWUs2lZFxLVLGhIDnU_"
        "LWTjyGCD4"
    )
    client_id = factory.Faker("word")

    class Meta:
        model = "datamodel.Abonnement"


class KanaalFactory(factory.django.DjangoModelFactory):
    naam = factory.Sequence(lambda n: f"kanaal_{n}")
    documentatie_link = factory.Faker("url")
    filters = factory.List(factory.Faker("word") for i in range(3))

    class Meta:
        model = "datamodel.Kanaal"


class FilterGroupFactory(factory.django.DjangoModelFactory):
    abonnement = factory.SubFactory(AbonnementFactory)
    kanaal = factory.SubFactory(KanaalFactory)

    class Meta:
        model = "datamodel.FilterGroup"


class FilterFactory(factory.django.DjangoModelFactory):
    key = factory.Faker("word")
    value = factory.Faker("word")
    filter_group = factory.SubFactory(FilterGroupFactory)

    class Meta:
        model = "datamodel.Filter"


class NotificatieFactory(factory.django.DjangoModelFactory):
    forwarded_msg = factory.Faker("text", max_nb_chars=1000)
    kanaal = factory.SubFactory(KanaalFactory)

    class Meta:
        model = "datamodel.Notificatie"


class NotificatieResponseFactory(factory.django.DjangoModelFactory):
    notificatie = factory.SubFactory(NotificatieFactory)
    abonnement = factory.SubFactory(AbonnementFactory)
    response_status = 204

    class Meta:
        model = "datamodel.NotificatieResponse"
