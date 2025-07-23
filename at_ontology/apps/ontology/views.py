from adrf.viewsets import ModelViewSet

from at_ontology.apps.ontology import models
from at_ontology.apps.ontology import serializers


class VertexViewSet(ModelViewSet):
    queryset = models.Vertex.objects.all()
    serializer_class = serializers.VertexSerializer
