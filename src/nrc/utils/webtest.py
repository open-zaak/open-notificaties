from django_webtest import WebTest as DjangoWebTest
from maykin_2fa.test import disable_admin_mfa


@disable_admin_mfa()
class WebTest(DjangoWebTest):
    pass
