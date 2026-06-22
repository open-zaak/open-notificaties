from django.contrib.admin.sites import AdminSite
from django.test import RequestFactory, TestCase

from ..admin import NotificatieAdmin
from ..admin_filters import ResultFilter
from ..models import Notificatie
from .factories import (
    AbonnementFactory,
    NotificatieFactory,
    NotificatieResponseFactory,
)


class NotificatieFilterTests(TestCase):
    def setUp(self):
        self.site = AdminSite()
        self.admin = NotificatieAdmin(Notificatie, self.site)
        self.factory = RequestFactory()

    def test_get_queryset_notification_without_failures(self):
        notificatie = NotificatieFactory.create()
        abonnement = AbonnementFactory.create()

        NotificatieResponseFactory.create(
            notificatie=notificatie,
            abonnement=abonnement,
            attempt=1,
            response_status=201,
        )

        request = self.factory.get("/")
        obj = self.admin.get_queryset(request).get(pk=notificatie.pk)

        self.assertFalse(obj.has_failure)
        self.assertTrue(self.admin.result(obj))

    def test_get_queryset_notification_with_failures(self):
        notificatie = NotificatieFactory.create()
        abonnement = AbonnementFactory.create()

        NotificatieResponseFactory.create(
            notificatie=notificatie,
            abonnement=abonnement,
            attempt=1,
            response_status=500,
        )

        request = self.factory.get("/")
        obj = self.admin.get_queryset(request).get(pk=notificatie.pk)

        self.assertTrue(obj.has_failure)
        self.assertFalse(self.admin.result(obj))

    def test_has_failure_annotation(self):
        success = NotificatieFactory.create()
        failure = NotificatieFactory.create()

        abonnement = AbonnementFactory.create()

        NotificatieResponseFactory.create(
            notificatie=success,
            abonnement=abonnement,
            response_status=201,
        )
        NotificatieResponseFactory.create(
            notificatie=failure,
            abonnement=abonnement,
            response_status=500,
        )

        request = self.factory.get("/", {"result": "failure"})
        request.GET = request.GET.copy()

        qs = self.admin.get_queryset(request)

        filtered = ResultFilter(
            request,
            request.GET,
            Notificatie,
            self.admin,
        ).queryset(request, qs)

        self.assertIn(failure, filtered)
        self.assertNotIn(success, filtered)

    def test_has_succes_annotation(self):
        success = NotificatieFactory.create()
        failure = NotificatieFactory.create()

        abonnement = AbonnementFactory.create()

        NotificatieResponseFactory.create(
            notificatie=success,
            abonnement=abonnement,
            response_status=201,
        )
        NotificatieResponseFactory.create(
            notificatie=failure,
            abonnement=abonnement,
            response_status=500,
        )

        request = self.factory.get("/", {"result": "success"})
        request.GET = request.GET.copy()

        qs = self.admin.get_queryset(request)

        filtered = ResultFilter(
            request,
            request.GET,
            Notificatie,
            self.admin,
        ).queryset(request, qs)

        self.assertIn(success, filtered)
        self.assertNotIn(failure, filtered)
