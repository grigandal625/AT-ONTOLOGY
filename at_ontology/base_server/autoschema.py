import uritemplate
from drf_spectacular.openapi import AutoSchema as DRFSAutoSchema
from drf_spectacular.plumbing import is_basic_type
from drf_spectacular.plumbing import is_list_serializer
from rest_framework.generics import GenericAPIView
from rest_framework.mixins import ListModelMixin


class AutoSchema(DRFSAutoSchema):
    def _is_list_view(self, serializer=None):
        if serializer is None:
            serializer = self.get_response_serializers()

        if isinstance(serializer, dict) and serializer:
            # extract likely main serializer from @extend_schema override
            serializer = {str(code): s for code, s in serializer.items()}
            serializer = serializer[min(serializer)]

        if is_list_serializer(serializer):
            return True
        if is_basic_type(serializer):
            return False
        if hasattr(self.view, "action"):
            return self.view.action == "list" or self.view.action == "alist"
        # list responses are "usually" only returned by GET
        if self.method != "GET":
            return False
        if isinstance(self.view, ListModelMixin):
            return True
        # primary key/lookup variable in path is a strong indicator for retrieve
        if isinstance(self.view, GenericAPIView):
            lookup_url_kwarg = self.view.lookup_url_kwarg or self.view.lookup_field
            if lookup_url_kwarg in uritemplate.variables(self.path):
                return False

        return False

    def get_filter_backends(self):
        filter_backends = getattr(self.view, "filter_backends", [])
        if not self._is_list_view():
            return [f for f in filter_backends if self.filter_is_required_for_detail(f)]
        return filter_backends

    def filter_is_required_for_detail(self, f):
        return getattr(f, "required_for_detail", False)
