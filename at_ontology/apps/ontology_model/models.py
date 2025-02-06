from django.core.exceptions import ValidationError
from django.db import models
from jsonschema import Draft7Validator
from jsonschema import exceptions

# Create your models here.


class DerivableEntity(models.Model):
    name = models.CharField(max_length=255, verbose_name="имя")
    description = models.TextField(null=True, blank=True, verbose_name="описание")
    derived_from: "DerivableEntity" = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="отнаследован от",
        related_name="%(class)s_derivations",
    )
    abstract = models.BooleanField(default=False, verbose_name="является абстрактным")

    class Meta:
        verbose_name = "наследуемая сущность"
        verbose_name_plural = "наследуемые сущности"
        abstract = True


class InstancingDerivableEntity(DerivableEntity):
    class Meta:
        verbose_name = "инстанцируемая наследуемая сущность"
        verbose_name_plural = "инстанцируемые наследуемые сущности"
        abstract = True


class DataType(DerivableEntity):
    object_schema = models.JSONField(null=True, blank=True, verbose_name="схема объекта")

    class Meta:
        verbose_name = "тип данных"
        verbose_name_plural = "типы данных"

    def clean(self) -> None:
        if self.object_schema:
            try:
                Draft7Validator.check_schema(self.object_schema)
            except exceptions.SchemaError as e:
                raise ValidationError(
                    f'Схема объекта в типе данных "{self.name}" не соответствует JSON Schema Draft 7: {str(e)}'
                )

    def __str__(self):
        return self.name


class DataTypedEntity(models.Model):
    data_type = models.ForeignKey(
        DataType, related_name="%(class)s_typed", on_delete=models.RESTRICT, verbose_name="тип данных"
    )
    default = models.JSONField(null=True, blank=True, verbose_name="значение по умолчанию")

    class Meta:
        verbose_name = "элемент с типом данных"
        verbose_name_plural = "элементы с типами данных"
        abstract = True


class PropertyDefinition(DataTypedEntity):
    name = models.CharField(max_length=255, verbose_name="имя свойства")
    description = models.TextField(null=True, blank=True, verbose_name="описание свойства")
    object_type: InstancingDerivableEntity = models.ForeignKey(
        InstancingDerivableEntity,
        related_name="properties",
        on_delete=models.CASCADE,
        verbose_name="тип объекта",
        blank=True,
        null=True,
    )
    required = models.BooleanField(default=False, verbose_name="обязательное")
    allows_multiple = models.BooleanField(default=True, verbose_name="допускает множественное значение")

    class Meta:
        verbose_name = "свойство"
        verbose_name_plural = "свойства"
        abstract = True

    def __str__(self):
        return self.name


class VertexType(InstancingDerivableEntity):
    class Meta:
        verbose_name = "тип вершины"
        verbose_name_plural = "типы вершин"

    def __str__(self):
        return self.name


class VertexTypePropertyDefinition(PropertyDefinition):
    object_type = models.ForeignKey(
        VertexType, related_name="properties", on_delete=models.CASCADE, verbose_name="тип вершины"
    )

    class Meta:
        verbose_name = "свойство вершины"
        verbose_name_plural = "свойства вершин"

    def __str__(self):
        return f"({self.object_type}).{self.name}"


class RelationshipType(InstancingDerivableEntity):
    valid_source_vertex_types = models.ManyToManyField(
        VertexType,
        related_name="valid_relation_source_types",
        blank=True,
        verbose_name="возможне типы родительских вершин",
    )
    valid_target_vertex_types = models.ManyToManyField(
        VertexType,
        related_name="valid_relation_target_types",
        blank=True,
        verbose_name="возможне типы дочерних вершин",
    )

    class Meta:
        verbose_name = "тип связи"
        verbose_name_plural = "типы связей"

    def __str__(self):
        return self.name


class RelationshipTypePropertyDefinition(PropertyDefinition):
    object_type = models.ForeignKey(
        RelationshipType, related_name="properties", on_delete=models.CASCADE, verbose_name="тип связи"
    )

    class Meta:
        verbose_name = "свойство связи"
        verbose_name_plural = "свойства связей"

    def __str__(self):
        return f"({self.object_type}).{self.name}"
