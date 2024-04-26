from django.urls import include, path, re_path

from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView
from vng_api_common import routers

from .viewsets import AbonnementViewSet, KanaalViewSet, NotificatieAPIView

router = routers.DefaultRouter()
router.register("abonnement", AbonnementViewSet)
router.register("kanaal", KanaalViewSet)


urlpatterns = [
    re_path(
        # Keep this as a regex path
        r"^v(?P<version>\d+)/",
        include(
            [
                # API documentation
                path(
                    "schema/openapi.yaml", SpectacularAPIView.as_view(), name="schema"
                ),
                path(
                    "schema/",
                    SpectacularRedocView.as_view(url_name="schema"),
                    name="schema-redoc",
                ),
                # actual API
                path(
                    "notificaties",
                    NotificatieAPIView.as_view(),
                    name="notificaties-list",
                ),
                path("", include(router.urls)),
                path("", include("vng_api_common.notifications.api.urls")),
            ]
        ),
    )
]
