from django.contrib import admin
from ontology_model.models import ElementType, RelationType

# Register your models here.


@admin.register(ElementType)
class ElementTypeAdmin(admin.ModelAdmin):
    list_display = 'name', 'description'
    search_fields = 'name', 'description'


@admin.register(RelationType)
class RelationTypeAdmin(admin.ModelAdmin):
    list_display = 'name', 'description', 'default_reflexivity', 'default_symmetry', 'default_transitivity'
    list_filter = 'default_reflexivity', 'default_symmetry', 'default_transitivity'
    search_fields = 'name', 'description'
