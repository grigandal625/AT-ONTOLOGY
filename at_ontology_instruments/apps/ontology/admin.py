from django.contrib import admin

from at_ontology_instruments.apps.ontology.models import File
from at_ontology_instruments.apps.ontology.models import Relationship
from at_ontology_instruments.apps.ontology.models import RelationshipPropertyAssignments
from at_ontology_instruments.apps.ontology.models import Vertex
from at_ontology_instruments.apps.ontology.models import VertexPropertyAssignments

# Register your models here.


@admin.register(File)
class FileAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(Vertex)
class VertexAdmin(admin.ModelAdmin):
    list_display = "name", "description", "type"
    search_fields = "name", "description", "type__name", "type__description"


@admin.register(Relationship)
class RelationAdmin(admin.ModelAdmin):
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


@admin.register(VertexPropertyAssignments)
class VertexPropertyAssignmentsAdmin(admin.ModelAdmin):
    list_display = "vertex", "property", "value"
    search_fields = ("vertex__name", "vertex__description", "property__name", "property__description")


@admin.register(RelationshipPropertyAssignments)
class RelationshipPropertyAssignmentsAdmin(admin.ModelAdmin):
    list_display = "relationship", "property", "value"
    search_fields = ("relationship__name", "relationship__description", "property__name", "property__description")
