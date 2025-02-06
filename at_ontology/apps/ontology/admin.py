from django.contrib import admin

from at_ontology.apps.ontology.models import File
from at_ontology.apps.ontology.models import Ontology
from at_ontology.apps.ontology.models import Relationship
from at_ontology.apps.ontology.models import RelationshipPropertyAssignment
from at_ontology.apps.ontology.models import Vertex
from at_ontology.apps.ontology.models import VertexPropertyAssignment

# Register your models here.


@admin.register(Ontology)
class OntologyAdmin(admin.ModelAdmin):
    list_display = ("name", "description")
    search_fields = ("name", "description")


@admin.register(File)
class FileAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(Vertex)
class VertexAdmin(admin.ModelAdmin):
    list_display = "name", "description", "type"
    search_fields = "name", "description", "type__name", "type__description"


@admin.register(Relationship)
class RelationshipAdmin(admin.ModelAdmin):
    list_display = (
        "type",
        "source",
        "target",
        "name",
        "description",
    )
    search_fields = (
        "name",
        "description",
        "type__name",
        "type__description",
        "source__name",
        "source__description",
        "source__type__name",
        "source__type__description",
        "target__name",
        "target__description",
        "target__type__name",
        "target__type__description",
    )


@admin.register(VertexPropertyAssignment)
class VertexPropertyAssignmentsAdmin(admin.ModelAdmin):
    list_display = "object", "property", "value"
    search_fields = ("object__name", "object__description", "property__name", "property__description")


@admin.register(RelationshipPropertyAssignment)
class RelationshipPropertyAssignmentsAdmin(admin.ModelAdmin):
    list_display = "object", "property", "value"
    search_fields = ("object__name", "object__description", "property__name", "property__description")
