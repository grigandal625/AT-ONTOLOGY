from django.contrib import admin
from ontology.models import Element, Relation, File

# Register your models here.


@admin.register(Element)
class ElementAdmin(admin.ModelAdmin):
    list_display = 'name', 'description', 'type'
    search_fields = 'name', 'description', 'type__name', 'type__description'


@admin.register(Relation)
class RelationAdmin(admin.ModelAdmin):
    list_display = 'type', 'parent', 'child', 'name', 'description', 'reflexivity', 'symmetry', 'transitivity'
    list_filter = 'reflexivity', 'symmetry', 'transitivity'
    search_fields = 'name', 'description', 'type__name', 'type__description', 'parent__name', 'parent__description', 'parent__type__name', 'parent__type__description', 'child__name', 'child__description', 'child__type__name', 'child__type__description'
