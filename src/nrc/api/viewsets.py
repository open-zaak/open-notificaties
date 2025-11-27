import structlog
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import mixins, status, views, viewsets
from rest_framework.response import Response
from vng_api_common.permissions import AuthScopesRequired, ClientIdRequired
from vng_api_common.viewsets import CheckQueryParamsMixin

from nrc.datamodel.models import Abonnement, CloudEvent, Kanaal
from nrc.utils.help_text import mark_experimental

from .filters import KanaalFilter
from .scopes import (
    SCOPE_NOTIFICATIES_CONSUMEREN,
    SCOPE_NOTIFICATIES_PUBLICEREN,
)
from .serializers import (
    AbonnementSerializer,
    CloudEventSerializer,
    KanaalSerializer,
    MessageSerializer,
)
from .utils import CloudEventJSONParser, CloudEventJSONRenderer

logger = structlog.stdlib.get_logger(__name__)


@extend_schema_view(
    list=extend_schema(
        summary="Alle ABONNEMENTen opvragen.",
    ),
    retrieve=extend_schema(summary="Een specifieke ABONNEMENT opvragen."),
    create=extend_schema(summary="Maak een ABONNEMENT aan."),
    update=extend_schema(summary="Werk een ABONNEMENT in zijn geheel bij."),
    partial_update=extend_schema(summary="Werk een ABONNEMENT deels bij."),
    destroy=extend_schema(summary="Verwijder een ABONNEMENT."),
)
class AbonnementViewSet(CheckQueryParamsMixin, viewsets.ModelViewSet):
    """
    Opvragen en bewerken van ABONNEMENTen.

    Een consumer kan een ABONNEMENT nemen op een KANAAL om zo NOTIFICATIEs te
    ontvangen die op dat KANAAL gepubliceerd worden.
    """

    queryset = Abonnement.objects.all()
    serializer_class = AbonnementSerializer
    lookup_field = "uuid"
    permission_classes = (AuthScopesRequired, ClientIdRequired)
    required_scopes = {
        "list": SCOPE_NOTIFICATIES_CONSUMEREN | SCOPE_NOTIFICATIES_PUBLICEREN,
        "retrieve": SCOPE_NOTIFICATIES_CONSUMEREN | SCOPE_NOTIFICATIES_PUBLICEREN,
        "create": SCOPE_NOTIFICATIES_CONSUMEREN,
        "destroy": SCOPE_NOTIFICATIES_CONSUMEREN,
        "update": SCOPE_NOTIFICATIES_CONSUMEREN,
        "partial_update": SCOPE_NOTIFICATIES_CONSUMEREN,
    }

    def perform_create(self, serializer):
        client_id = self.request.jwt_auth.client_id
        serializer.save(client_id=client_id)


@extend_schema_view(
    list=extend_schema(summary="Alle KANAALen opvragen."),
    retrieve=extend_schema(summary="Een specifiek KANAAL opvragen."),
    update=extend_schema(summary=mark_experimental("Een specifiek KANAAL bewerken.")),
    partial_update=extend_schema(
        summary=mark_experimental("Een specifiek KANAAL deels bewerken.")
    ),
    create=extend_schema(summary="Maak een KANAAL aan."),
)
class KanaalViewSet(
    CheckQueryParamsMixin,
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    Opvragen, aanmaken en bewerken van KANAALen.

    Op een KANAAL publiceren componenten (bronnen) hun NOTIFICATIEs. Alleen
    componenten die NOTIFICATIEs willen publiceren dienen een KANAAL aan te
    maken. Dit KANAAL kan vervolgens aan consumers worden gegeven om zich op te
    abonneren.
    """

    queryset = Kanaal.objects.all()
    serializer_class = KanaalSerializer
    filterset_class = KanaalFilter
    lookup_field = "uuid"
    required_scopes = {
        "list": SCOPE_NOTIFICATIES_PUBLICEREN | SCOPE_NOTIFICATIES_CONSUMEREN,
        "retrieve": SCOPE_NOTIFICATIES_PUBLICEREN | SCOPE_NOTIFICATIES_CONSUMEREN,
        "create": SCOPE_NOTIFICATIES_PUBLICEREN,
        "update": SCOPE_NOTIFICATIES_PUBLICEREN,
        "partial_update": SCOPE_NOTIFICATIES_PUBLICEREN,
    }


@extend_schema(summary="Publiceer een notificatie.")
class NotificatieAPIView(views.APIView):
    """
    Publiceren van NOTIFICATIEs.

    Een NOTIFICATIE wordt gepubliceerd op een KANAAL. Alle consumers die een
    ABONNEMENT hebben op dit KANAAL ontvangen de NOTIFICATIE.
    """

    required_scopes = {"create": SCOPE_NOTIFICATIES_PUBLICEREN}
    # Exposed action of the view used by the vng_api_common
    action = "create"
    serializer_class = MessageSerializer

    def create(self, request, *args, **kwargs):
        return self.post(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data

            # post to message queue
            # send to abonnement
            serializer.save()

            return Response(data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(summary=mark_experimental("Publiceer een cloud event"))
class CloudEventViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    required_scopes = {"create": SCOPE_NOTIFICATIES_PUBLICEREN}
    serializer_class = CloudEventSerializer
    queryset = CloudEvent.objects.all()

    parser_classes = (CloudEventJSONParser,)
    renderer_classes = (CloudEventJSONRenderer,)
