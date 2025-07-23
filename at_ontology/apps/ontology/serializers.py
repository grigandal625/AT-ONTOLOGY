from adrf import serializers

from at_ontology.apps.ontology.models import Vertex


class VertexSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vertex
        fields = "__all__"
