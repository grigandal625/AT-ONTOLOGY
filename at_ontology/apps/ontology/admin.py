from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from at_ontology.apps.ontology.models import Ontology
from at_ontology.apps.ontology.models import Relationship
from at_ontology.apps.ontology.models import Vertex
from at_ontology.apps.ontology.models import VertexPropertyAssignment


class VertexInline(admin.TabularInline):
    model = Vertex
    extra = 0
    fields = ("name", "label", "type")
    show_change_link = True


class RelationshipInline(admin.TabularInline):
    model = Relationship
    extra = 0
    fields = ("name", "label", "type", "source", "target")
    show_change_link = True


# class ImportsInline(admin.TabularInline):
#     model = Ontology.imports.through
#     extra = 0
#     show_change_link = True
#     verbose_name = _("import")
#     verbose_name_plural = _("imports")

#     def get_formset(self, request, obj=None, **kwargs):
#         formset = super().get_formset(request, obj, **kwargs)
#         # Изменяем verbose_name для поля 'course' в форме
#         formset.form.base_fields['ontologymodel'].label = _("ontology_model")
#         return formset


@admin.register(Ontology)
class OntologyAdmin(admin.ModelAdmin):
    list_display = "name", "description"
    search_fields = "name", "description"
    inlines = [VertexInline, RelationshipInline]


class VertexPropertyAssignmentInline(admin.TabularInline):
    model = VertexPropertyAssignment
    extra = 0
    fields = ("vertex", "property", "value")
    show_change_link = True
    verbose_name = _("vertex_property_assignment")
    verbose_name_plural = _("vertex_property_assignments")


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
