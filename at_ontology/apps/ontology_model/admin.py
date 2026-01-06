from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
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
    # autocomplete_fields = ("ontology_model",)


class DataTypeInline(admin.TabularInline):
    model = models.DataType
    extra = 0
    fields = ("name", "derived_from")
    # autocomplete_fields = ("derived_from",)
    show_change_link = True


class VertexTypeInline(admin.TabularInline):
    model = models.VertexType
    extra = 0
    fields = ("name", "derived_from")
    # autocomplete_fields = ("derived_from",)
    show_change_link = True


class RelationshipTypeInline(admin.TabularInline):
    model = models.RelationshipType
    extra = 0
    fields = ("name",)
    show_change_link = True


# =========================================================
# OntologyModel
# =========================================================


@admin.register(models.OntologyModel)
class OntologyModelAdmin(NameSearchAdmin):
    list_display = ("name", "label")
    search_fields = ("name", "label", "description")
    filter_horizontal = ("imports",)

    inlines = (
        DataTypeInline,
        VertexTypeInline,
        RelationshipTypeInline,
    )


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
    # autocomplete_fields = ("ontology_model", "derived_from")
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

    def has_change_permission(self, request, obj=None):
        return False  # запрет редактирования существующих

    def has_add_permission(self, request, obj=None):
        return True


class UnlistedModelAdmin(admin.ModelAdmin):
    def get_model_perms(self, request):
        """
        Return empty perms dict to hide the model from admin index.
        """
        return {}


# Register Child with the hidden admin
admin.site.register(models.RelationshipTypePropertyDefinition, UnlistedModelAdmin)


class RelationshipTypePropertyInline(admin.TabularInline):
    model = models.RelationshipTypePropertyDefinition
    extra = 0

    fields = ("name", "label", "type", "edit_link")

    readonly_fields = ("edit_link",)

    def edit_link(self, obj: models.RelationshipTypePropertyDefinition):
        if obj.pk:  # Only show link if object exists
            url = reverse("admin:ontology_model_relationshiptypepropertydefinition_change", args=[obj.pk])
            label = _("Change")
            res = format_html(
                '<a style="cursor:pointer;" onclick="window._showPopup(\'{url}?_popup=1\');">{label}</a>',
                url=url,
                label=label,
            )
            return res
        return ""

    edit_link.short_description = _("Change")

    def has_change_permission(self, request, obj=None):
        return False  # запрет редактирования существующих

    def has_add_permission(self, request, obj=None):
        return True


@admin.register(models.RelationshipType)
class RelationshipTypeAdmin(OntologyModelScopedAdmin):
    list_display = ("name", "ontology_model")
    list_filter = ("ontology_model",)
    # autocomplete_fields = ("ontology_model",)
    filter_horizontal = (
        "valid_source_types",
        "valid_target_types",
    )
    inlines = (
        RelationshipTypePropertyInline,
        RelationshipTypeArtifactInline,
    )

    class Media:
        js = ("ontology_model/admin/showPopup.js",)


# =========================================================
# DataType + Constraints
# =========================================================


class ConstraintInline(admin.TabularInline):
    model = models.ConstraintDefinition
    extra = 0


@admin.register(models.DataType)
class DataTypeAdmin(OntologyModelScopedAdmin):
    list_display = ("name", "ontology_model", "derived_from")
    # autocomplete_fields = ("ontology_model", "derived_from")
    inlines = (ConstraintInline,)


# =========================================================
# Artifact Definitions
# =========================================================

# @admin.register(models.VertexTypeArtifactDefinition)
# class VertexTypeArtifactDefinitionAdmin(admin.ModelAdmin):
#     list_display = (
#         "name",
#         "vertex_type",
#         "required",
#         "allows_multiple",
#     )
#     list_filter = ("required", "allows_multiple")
#     search_fields = ("name", "label")
#     # autocomplete_fields = ("vertex_type",)


# @admin.register(models.RelationshipTypeArtifactDefinition)
# class RelationshipTypeArtifactDefinitionAdmin(admin.ModelAdmin):
#     list_display = (
#         "name",
#         "relationship_type",
#         "required",
#         "allows_multiple",
#     )
#     list_filter = ("required", "allows_multiple")
#     search_fields = ("name", "label")
#     # autocomplete_fields = ("relationship_type",)


# # =========================================================
# # Property Definitions
# # =========================================================

# @admin.register(models.VertexTypePropertyDefinition)
# class VertexTypePropertyDefinitionAdmin(admin.ModelAdmin):
#     list_display = (
#         "name",
#         "vertex_type",
#         "type",
#         "required",
#         "initializable",
#     )
#     list_filter = ("required", "initializable", "allows_multiple")
#     search_fields = ("name", "label")
#     # autocomplete_fields = ("vertex_type", "type")


# @admin.register(models.RelationshipTypePropertyDefinition)
# class RelationshipTypePropertyDefinitionAdmin(admin.ModelAdmin):
#     list_display = (
#         "name",
#         "relationship_type",
#         "type",
#         "required",
#         "initializable",
#     )
#     list_filter = ("required", "initializable", "allows_multiple")
#     search_fields = ("name", "label")
#     # autocomplete_fields = ("relationship_type", "type")


# # =========================================================
# # ConstraintDefinition (standalone admin)
# # =========================================================

# @admin.register(models.ConstraintDefinition)
# class ConstraintDefinitionAdmin(admin.ModelAdmin):
#     list_display = ("data_type", "name")
#     list_filter = ("name",)
#     search_fields = ("data_type__name",)
#     # autocomplete_fields = ("data_type",)
