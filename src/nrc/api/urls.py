from django.conf import settings
from django.urls import include, path, re_path

from vng_api_common import routers
from vng_api_common.schema import SchemaView

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
                re_path(
                    r"^schema/openapi(?P<format>\.json|\.yaml)$",
                    SchemaView.without_ui(cache_timeout=settings.SPEC_CACHE_TIMEOUT),
                    name="schema-json",
                ),
                path(
                    "schema/",
                    SchemaView.with_ui(
                        "redoc", cache_timeout=settings.SPEC_CACHE_TIMEOUT
                    ),
                    name="schema-redoc",
                ),
                # actual API
                path(
                    "notificaties",
                    NotificatieAPIView.as_view(),
                    name="notificaties-list",
                ),
                path("", include(router.urls)),
                # should not be picked up by drf-yasg
                path("", include("vng_api_common.api.urls")),
                path("", include("vng_api_common.notifications.api.urls")),
            ]
        ),
    )
]
