from typing import TYPE_CHECKING

from django.core.exceptions import ValidationError
from django.db import models
from jsonschema import exceptions
from jsonschema import validate

if TYPE_CHECKING:
    from at_ontology.apps.ontology_model.models import (
        VertexType,
        RelationshipType,
        VertexTypePropertyDefinition,
        RelationshipTypePropertyDefinition,
        PropertyDefinition,
        InstancingDerivableEntity,
    )

# Create your models here.


class Ontology(models.Model):
    name = models.CharField(max_length=255, verbose_name="имя")
    description = models.TextField(null=True, blank=True, verbose_name="описание")

    class Meta:
        verbose_name = "онтология"
        verbose_name_plural = "онтологии"

    def __str__(self):
        return self.name


class ValueContainedEntity(models.Model):
    value = models.JSONField(verbose_name="значение", null=True, blank=True)

    class Meta:
        verbose_name = "значение сущности"
        verbose_name_plural = "значения сущностей"
        abstract = True


class File(models.Model):
    name = models.CharField(max_length=255, verbose_name="Имя")
    content = models.FileField(verbose_name="содержимое")

    class Meta:
        verbose_name = "файл"
        verbose_name_plural = "файлы"

    def __str__(self):
        return self.name


class Instance(models.Model):
    name = models.CharField(max_length=255, verbose_name="имя")
    description = models.TextField(null=True, blank=True, verbose_name="описание")
    type: "InstancingDerivableEntity" = models.ForeignKey(
        "ontology_model.InstancingDerivableEntity", on_delete=models.CASCADE, verbose_name="тип"
    )

    class Meta:
        verbose_name = "объект"
        verbose_name_plural = "объекты"
        abstract = True

    def __str__(self):
        return self.name

    def clean(self) -> None:
        if self.type.abstract:
            raise ValidationError(f'Тип {self._meta.verbose_name_plural} "{self.type.name}" не является инстанцируемым')


class PropertyAssignment(ValueContainedEntity):
    object: "Instance" = models.ForeignKey(Instance, on_delete=models.CASCADE, verbose_name="сущность")
    property: "PropertyDefinition" = models.ForeignKey(
        "ontology_model.PropertyDefinition", on_delete=models.CASCADE, verbose_name="исходное свойство"
    )

    def clean(self) -> None:
        if self.property.required and self.value is None and self.property.default is None:
            raise ValidationError(
                f'Значение свойства "{self.property.name}" '
                f'{self.object._meta.verbose_name_plural} "{self.object}" обязательно'
            )

        if self.value is not None and self.property.data_type.object_schema:
            try:
                validate(instance=self.value, schema=self.property.data_type.object_schema)
            except exceptions.ValidationError as e:
                raise ValidationError(
                    f'Значение свойства "{self.property.name}" '
                    f'{self.object._meta.verbose_name_plural} "{self.object}" не соответствует схеме: {str(e)}'
                )

        derivation = []
        object_type = self.object.type
        while object_type.derived_from:
            derivation.append(object_type.derived_from.pk)
            object_type = object_type.derived_from

        if self.property.object_type.pk not in derivation:
            raise ValidationError(
                f'Тип {self.object._meta.verbose_name_plural} "{self.object.type}" '
                f'не поддерживает свойство "{self.property.name}"'
            )

        if (
            not self.property.allows_multiple
            and RelationshipPropertyAssignment.objects.filter(relationship=self.object, property=self.property).exists()
        ):
            raise ValidationError(
                f'Нельзя назначить несколько значений для свойства "{self.property.name}" '
                f'для {self.object._meta.verbose_name_plural} "{self.object}"'
            )

    class Meta:
        verbose_name = "присвоенное значение свойства"
        verbose_name_plural = "присвоенные значения свойств"
        abstract = True

    def __str__(self):
        return f"{self.object}.{self.property.name}"


class Vertex(Instance):
    type: "VertexType" = models.ForeignKey(
        "ontology_model.VertexType", on_delete=models.RESTRICT, verbose_name="тип вершины"
    )
    files = models.ManyToManyField(File, verbose_name="файлы", blank=True)
    ontology: Ontology = models.ForeignKey(
        Ontology, verbose_name="онтология", on_delete=models.CASCADE, related_name="vertexes"
    )

    class Meta:
        verbose_name = "вершина"
        verbose_name_plural = "вершины"

    def __str__(self):
        return f"{self.name} ({self.type})"


class VertexPropertyAssignment(PropertyAssignment):
    object: Vertex = models.ForeignKey(
        Vertex, on_delete=models.CASCADE, verbose_name="вершина", related_name="properties"
    )
    property: "VertexTypePropertyDefinition" = models.ForeignKey(
        "ontology_model.VertexTypePropertyDefinition",
        on_delete=models.CASCADE,
        verbose_name="исходное свойство типа вершины",
    )

    class Meta:
        verbose_name = "присвоенное значение свойства вершины"
        verbose_name_plural = "присвоенные значения свойств вершин"


class Relationship(Instance):
    name = models.CharField(max_length=255, verbose_name="имя", blank=True, null=True, default=None)
    source: "Vertex" = models.ForeignKey(
        Vertex, on_delete=models.CASCADE, verbose_name="родительская вершина", related_name="output_relations"
    )
    target: "Vertex" = models.ForeignKey(
        Vertex, on_delete=models.CASCADE, verbose_name="дочерняя вершина", related_name="input_relations"
    )
    type: "RelationshipType" = models.ForeignKey(
        "ontology_model.RelationshipType",
        on_delete=models.RESTRICT,
        verbose_name="тип связи",
    )
    files = models.ManyToManyField(File, verbose_name="файлы", blank=True)

    def clean(self) -> None:
        super().clean()
        if self.source.ontology != self.target.ontology:
            raise ValidationError(f"Родительская и дочерняя вершины связи {self} должны принадлежать одной онтологии")

        if self.type.valid_source_vertex_types.exists():
            derivation = []
            source_type = self.source.type

            while source_type:
                derivation.append(source_type.pk)
                source_type = source_type.derived_from

            if not self.type.valid_source_vertex_types.filter(pk__in=derivation).exists():
                raise ValidationError(
                    f'Тип вершины "{self.source.type}" не поддерживается в качестве '
                    f'родительской вершины для типа связи "{self.type}" (связь "{self}")'
                )

        if self.type.valid_target_vertex_types.exists():
            derivation = []
            target_type = self.target.type

            while target_type:
                derivation.append(target_type.pk)
                target_type = target_type.derived_from

            if not self.type.valid_target_vertex_types.filter(pk__in=derivation).exists():
                raise ValidationError(
                    f'Тип вершины "{self.target.type}" не поддерживается в качестве '
                    f'дочерней вершины для типа связи "{self.type}" (связь "{self}")'
                )

    class Meta:
        verbose_name = "связь"
        verbose_name_plural = "связи"

    def __str__(self):
        if self.name:
            return f"{self.name} - {self.type}"
        return f"({self.pk}) {self.type}"


class RelationshipPropertyAssignment(PropertyAssignment):
    object: Relationship = models.ForeignKey(
        Relationship, on_delete=models.CASCADE, verbose_name="связь", related_name="properties"
    )
    property: "RelationshipTypePropertyDefinition" = models.ForeignKey(
        "ontology_model.RelationshipTypePropertyDefinition",
        on_delete=models.CASCADE,
        verbose_name="исходное свойство типа связи",
    )

    class Meta:
        verbose_name = "присвоенное значение свойства связи"
        verbose_name_plural = "присвоенные значения свойств связей"
