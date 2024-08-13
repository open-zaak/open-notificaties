from django.apps import apps
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import include, path
from django.views.generic import TemplateView

from maykin_2fa import monkeypatch_admin
from maykin_2fa.urls import urlpatterns, webauthn_urlpatterns
from mozilla_django_oidc_db.views import AdminLoginFailure
from vng_api_common.views import ViewConfigView

handler500 = "nrc.utils.views.server_error"

admin.site.enable_nav_sidebar = False

# Configure admin
monkeypatch_admin()

urlpatterns = [
    path("admin/login/failure/", AdminLoginFailure.as_view(), name="admin-oidc-error"),
    # 2fa
    path("admin/", include((urlpatterns, "maykin_2fa"))),
    path("admin/", include((webauthn_urlpatterns, "two_factor"))),
    path("admin/", admin.site.urls),
    path("api/", include("nrc.api.urls")),
    # Simply show the master template.
    path("", TemplateView.as_view(template_name="index.html"), name="home"),
    path("ref/", include("vng_api_common.urls")),
    path("oidc/", include("mozilla_django_oidc.urls")),
    path("view-config/", ViewConfigView.as_view(), name="view-config"),
]

# NOTE: The staticfiles_urlpatterns also discovers static files (ie. no need to run collectstatic). Both the static
# folder and the media folder are only served via Django if DEBUG = True.
urlpatterns += staticfiles_urlpatterns() + static(
    settings.MEDIA_URL, document_root=settings.MEDIA_ROOT
)

if settings.DEBUG and apps.is_installed("debug_toolbar"):
    import debug_toolbar

    urlpatterns += [path("__debug__/", include(debug_toolbar.urls))]
