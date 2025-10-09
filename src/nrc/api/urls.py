from django.urls import include, path, re_path

from drf_spectacular.views import (
    SpectacularRedocView,
)
from vng_api_common import routers

from ..utils.views import (
    DeprecationRedirectView,
    SpectacularJSONAPIView,
    SpectacularYAMLAPIView,
)
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
                    "schema/openapi.yaml",
                    DeprecationRedirectView.as_view(pattern_name="schema"),
                ),
                path(
                    "schema/openapi.json",
                    DeprecationRedirectView.as_view(pattern_name="schema-json"),
                ),
                path("openapi.yaml", SpectacularYAMLAPIView.as_view(), name="schema"),
                path(
                    "openapi.json",
                    SpectacularJSONAPIView.as_view(),
                    name="schema-json",
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
