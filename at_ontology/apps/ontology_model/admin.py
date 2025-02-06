from django.contrib import admin

from at_ontology.apps.ontology_model.models import DataType
from at_ontology.apps.ontology_model.models import RelationshipType
from at_ontology.apps.ontology_model.models import RelationshipTypePropertyDefinition
from at_ontology.apps.ontology_model.models import VertexType
from at_ontology.apps.ontology_model.models import VertexTypePropertyDefinition

# Register your models here.


@admin.register(DataType)
class DataTypeAdmin(admin.ModelAdmin):
    list_display = "name", "description", "derived_from"
    search_fields = "name", "description"


@admin.register(VertexType)
class VertexTypeAdmin(admin.ModelAdmin):
    list_display = "name", "description", "derived_from"
    search_fields = "name", "description"


@admin.register(RelationshipType)
class RelationshipTypeAdmin(admin.ModelAdmin):
    list_display = "name", "description", "derived_from"
    search_fields = "name", "description"


@admin.register(VertexTypePropertyDefinition)
class VertexTypePropertyDefinitionAdmin(admin.ModelAdmin):
    list_display = "name", "description", "data_type", "object_type", "required", "allows_multiple"
    search_fields = "name", "description", "object_type__name", "object_type__description"
    list_filter = "required", "allows_multiple"


@admin.register(RelationshipTypePropertyDefinition)
class RelationshipTypePropertyDefinitionAdmin(admin.ModelAdmin):
    list_display = "name", "description", "data_type", "object_type", "required", "allows_multiple"
    search_fields = (
        "name",
        "description",
        "data_type__name",
        "object_type__name",
        "object_type__description",
    )
    list_filter = "required", "allows_multiple"
