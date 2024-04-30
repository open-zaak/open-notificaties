from nrc.datamodel.models import Kanaal
from nrc.utils.filterset import FilterSet


class KanaalFilter(FilterSet):
    class Meta:
        model = Kanaal
        fields = ("naam",)
