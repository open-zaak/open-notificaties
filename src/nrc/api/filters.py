from vng_api_common.filtersets import FilterSet

from nrc.datamodel.models import Kanaal


class KanaalFilter(FilterSet):
    class Meta:
        model = Kanaal
        fields = ("naam",)
