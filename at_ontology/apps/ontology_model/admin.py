from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from at_ontology.apps.ontology_model import models


# =========================================================
# Base admin mixins
# =========================================================

class NameSearchAdmin(admin.ModelAdmin):
    search_fields = ("name", "label", "description")
    list_display = ("name", "label")
    ordering = ("name",)


class OntologyModelScopedAdmin(NameSearchAdmin):
    list_filter = ("ontology_model",)
    autocomplete_fields = ("ontology_model",)


# =========================================================
# OntologyModel
# =========================================================

@admin.register(models.OntologyModel)
class OntologyModelAdmin(NameSearchAdmin):
    list_display = ("name", "label")
    search_fields = ("name", "label", "description")
    filter_horizontal = ("imports",)


# =========================================================
# VertexType
# =========================================================

class VertexTypeArtifactInline(admin.TabularInline):
    model = models.VertexTypeArtifactDefinition
    extra = 0


class VertexTypePropertyInline(admin.TabularInline):
    model = models.VertexTypePropertyDefinition
    extra = 0


@admin.register(models.VertexType)
class VertexTypeAdmin(OntologyModelScopedAdmin):
    list_display = ("name", "ontology_model", "derived_from")
    list_filter = ("ontology_model",)
    autocomplete_fields = ("ontology_model", "derived_from")
    inlines = (
        VertexTypeArtifactInline,
        VertexTypePropertyInline,
    )


# =========================================================
# RelationshipType
# =========================================================

class RelationshipTypeArtifactInline(admin.TabularInline):
    model = models.RelationshipTypeArtifactDefinition
    extra = 0


class RelationshipTypePropertyInline(admin.TabularInline):
    model = models.RelationshipTypePropertyDefinition
    extra = 0


@admin.register(models.RelationshipType)
class RelationshipTypeAdmin(OntologyModelScopedAdmin):
    list_display = ("name", "ontology_model")
    list_filter = ("ontology_model",)
    autocomplete_fields = ("ontology_model",)
    filter_horizontal = (
        "valid_source_types",
        "valid_target_types",
    )
    inlines = (
        RelationshipTypeArtifactInline,
        RelationshipTypePropertyInline,
    )


# =========================================================
# DataType + Constraints
# =========================================================

class ConstraintInline(admin.TabularInline):
    model = models.ConstraintDefinition
    extra = 0


@admin.register(models.DataType)
class DataTypeAdmin(OntologyModelScopedAdmin):
    list_display = ("name", "ontology_model", "derived_from")
    autocomplete_fields = ("ontology_model", "derived_from")
    inlines = (ConstraintInline,)


# =========================================================
# Artifact Definitions
# =========================================================

@admin.register(models.VertexTypeArtifactDefinition)
class VertexTypeArtifactDefinitionAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "vertex_type",
        "required",
        "allows_multiple",
    )
    list_filter = ("required", "allows_multiple")
    search_fields = ("name", "label")
    autocomplete_fields = ("vertex_type",)


@admin.register(models.RelationshipTypeArtifactDefinition)
class RelationshipTypeArtifactDefinitionAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "relationship_type",
        "required",
        "allows_multiple",
    )
    list_filter = ("required", "allows_multiple")
    search_fields = ("name", "label")
    autocomplete_fields = ("relationship_type",)


# =========================================================
# Property Definitions
# =========================================================

@admin.register(models.VertexTypePropertyDefinition)
class VertexTypePropertyDefinitionAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "vertex_type",
        "type",
        "required",
        "initializable",
    )
    list_filter = ("required", "initializable", "allows_multiple")
    search_fields = ("name", "label")
    autocomplete_fields = ("vertex_type", "type")


@admin.register(models.RelationshipTypePropertyDefinition)
class RelationshipTypePropertyDefinitionAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "relationship_type",
        "type",
        "required",
        "initializable",
    )
    list_filter = ("required", "initializable", "allows_multiple")
    search_fields = ("name", "label")
    autocomplete_fields = ("relationship_type", "type")


# =========================================================
# ConstraintDefinition (standalone admin)
# =========================================================

@admin.register(models.ConstraintDefinition)
class ConstraintDefinitionAdmin(admin.ModelAdmin):
    list_display = ("data_type", "name")
    list_filter = ("name",)
    search_fields = ("data_type__name",)
    autocomplete_fields = ("data_type",)
