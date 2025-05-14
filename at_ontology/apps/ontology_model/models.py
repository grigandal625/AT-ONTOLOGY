import uuid

from django.core.exceptions import ValidationError
from django.db import models
from jsonschema import Draft7Validator
from jsonschema import exceptions


# Create your models here.



# class DerivableEntity(models.Model):
#     name = models.CharField(max_length=255, verbose_name="имя")
#     description = models.TextField(null=True, blank=True, verbose_name="описание")
#     derived_from: "DerivableEntity" = models.ForeignKey(
#         "self",
#         on_delete=models.SET_NULL,
#         null=True,
#         blank=True,
#         verbose_name="отнаследован от",
#         related_name="%(class)s_derivations",
#     )
#     abstract = models.BooleanField(default=False, verbose_name="является абстрактным")
#
#     class Meta:
#         verbose_name = "наследуемая сущность"
#         verbose_name_plural = "наследуемые сущности"
#         abstract = True
#
#
# class InstancingDerivableEntity(DerivableEntity):
#     class Meta:
#         verbose_name = "инстанцируемая наследуемая сущность"
#         verbose_name_plural = "инстанцируемые наследуемые сущности"
#         abstract = True
#
#
# class DataType(DerivableEntity):
#     object_schema = models.JSONField(null=True, blank=True, verbose_name="схема объекта")
#
#     class Meta:
#         verbose_name = "тип данных"
#         verbose_name_plural = "типы данных"
#
#     def clean(self) -> None:
#         if self.object_schema:
#             try:
#                 Draft7Validator.check_schema(self.object_schema)
#             except exceptions.SchemaError as e:
#                 raise ValidationError(
#                     f'Схема объекта в типе данных "{self.name}" не соответствует JSON Schema Draft 7: {str(e)}'
#                 )
#
#     def __str__(self):
#         return self.name
#
#
# class DataTypedEntity(models.Model):
#     data_type = models.ForeignKey(
#         DataType, related_name="%(class)s_typed", on_delete=models.RESTRICT, verbose_name="тип данных"
#     )
#     default = models.JSONField(null=True, blank=True, verbose_name="значение по умолчанию")
#
#     class Meta:
#         verbose_name = "элемент с типом данных"
#         verbose_name_plural = "элементы с типами данных"
#         abstract = True
#
#
# class PropertyDefinition(DataTypedEntity):
#     name = models.CharField(max_length=255, verbose_name="имя свойства")
#     description = models.TextField(null=True, blank=True, verbose_name="описание свойства")
#     object_type: InstancingDerivableEntity = models.ForeignKey(
#         InstancingDerivableEntity,
#         related_name="properties",
#         on_delete=models.CASCADE,
#         verbose_name="тип объекта",
#         blank=True,
#         null=True,
#     )
#     required = models.BooleanField(default=False, verbose_name="обязательное")
#     allows_multiple = models.BooleanField(default=True, verbose_name="допускает множественное значение")
#
#     class Meta:
#         verbose_name = "свойство"
#         verbose_name_plural = "свойства"
#         abstract = True
#
#     def __str__(self):
#         return self.name
#
#
# class VertexType(InstancingDerivableEntity):
#     class Meta:
#         verbose_name = "тип вершины"
#         verbose_name_plural = "типы вершин"
#
#     def __str__(self):
#         return self.name
#
#
# class VertexTypePropertyDefinition(PropertyDefinition):
#     object_type = models.ForeignKey(
#         "VertexType", related_name="properties", on_delete=models.CASCADE, verbose_name="тип вершины"
#     )
#
#     class Meta:
#         verbose_name = "свойство вершины"
#         verbose_name_plural = "свойства вершин"
#
#     def __str__(self):
#         return f"({self.object_type}).{self.name}"
#
#
# class RelationshipType(InstancingDerivableEntity):
#     valid_source_vertex_types = models.ManyToManyField(
#         "VertexType",
#         related_name="valid_relation_source_types",
#         blank=True,
#         verbose_name="возможне типы родительских вершин",
#     )
#     valid_target_vertex_types = models.ManyToManyField(
#         "VertexType",
#         related_name="valid_relation_target_types",
#         blank=True,
#         verbose_name="возможные типы дочерних вершин",
#     )
#
#     class Meta:
#         verbose_name = "тип связи"
#         verbose_name_plural = "типы связей"
#
#     def __str__(self):
#         return self.name
#
#
# class RelationshipTypePropertyDefinition(PropertyDefinition):
#     object_type = models.ForeignKey(
#         RelationshipType, related_name="properties", on_delete=models.CASCADE, verbose_name="тип связи"
#     )
#
#     class Meta:
#         verbose_name = "свойство связи"
#         verbose_name_plural = "свойства связей"
#
#     def __str__(self):
#         return f"({self.object_type}).{self.name}"


class OntologyBase(models.Model):
    owner = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='children'  # может надо поменять название
    )
    _built = models.BooleanField(default=False)

    class Meta:
        abstract = True

class OntologyEntity(OntologyBase):
    name = models.CharField(max_length=255)
    label = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)

    class Meta:
        abstract = True


class Derivable(OntologyEntity):
    derived_from: "Derivable" = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='derivations',
        help_text='Ссылка на сущность, из которой была получена эта'
    )

    class Meta:
        abstract = True

class Instancable(Derivable):

    metadata = models.JSONField(
        null=True,
        blank=True,
        help_text="Дополнительные данные (metadata) в виде словаря"
    )
    # Как переписать это в модель
    # properties: Optional[Dict[str, "PropertyDefinition"]] = field(default_factory=dict)
    # artifacts: Optional[Dict[str, "ArtifactDefinition"]] = field(default_factory=dict)


    class Meta:
        abstract = True



class Definition(OntologyEntity):

    class Meta:
        verbose_name = "сущность",
        verbose_name_plural = "сущности",
        abstract = True
class VertexType(Instancable):
    ontology_model: "OntologyModel" = models.ForeignKey(
        "OntologyModel",
        on_delete=models.CASCADE,
        related_name="vertex_types",
        blank=True,
        null=True
    )

    class Meta:
        verbose_name = "тип вершины"
        verbose_name_plural = "типы вершин"


class RelationshipType(Instancable):
    valid_source_vertex_types = models.ManyToManyField(
        "VertexType",
        related_name="valid_relation_source_types",
        blank=True,
        verbose_name="возможные типы родительских вершин",
    )
    valid_target_vertex_types = models.ManyToManyField(
        "VertexType",
        related_name="valid_relation_target_types",
        blank=True,
        verbose_name="возможные типы дочерних вершин",
    )

    ontology_model: "OntologyModel" = models.ForeignKey(
        "OntologyModel",
        on_delete=models.CASCADE,
        related_name="relationship_types",
        blank=True,
        null=True
    )

    class Meta:
        verbose_name = "тип связи"
        verbose_name_plural = "типы связей"

    def __str__(self):
        return self.name


class Instance(OntologyEntity):

    type: "Instancable" = models.ForeignKey(
        "Instancable",
        on_delete=models.PROTECT,
        related_name='instances',
        help_text='Тип (Instancable), к которому принадлежит этот экземпляр'

    )
    # metadata: Optional[dict] = field(default=None)
    metadata = models.JSONField(  # Хз как это правильно было написать, гпт предложил так
        null=True,
        blank=True,
        help_text='Additional metadata stored as a JSON object'
    )


    class Meta:
        verbose_name = 'сущность'
        verbose_name_plural = 'сущности'
        abstract = True




# ------- ArtifactDefinitions and ArtifactAssignments ------------
class ArtifactDefinition(Definition):
    default_path = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text='Default file path for the artifact'
    )
    mime_type = models.CharField(
        max_length=255,
        default='application/octet-stream',
        help_text='MIME type of the artifact'
    )
    required = models.BooleanField(
        default=False,
        help_text='Artifact is required'
    )
    allows_multiple = models.BooleanField(
        default=True,
        help_text='Multiple artifacts allowed'
    )
    min_assignments = models.IntegerField(
        null=True,
        blank=True,
        help_text='Minimum number of artifacts'
    )
    max_assignments = models.IntegerField(
        null=True,
        blank=True,
        help_text='Maximum number of artifacts'
    )

    class Meta:
        verbose_name = 'Artifact Definition'
        verbose_name_plural = 'Artifact Definitions'
        abstract = True

class VertexTypeArtifactDefinition(ArtifactDefinition):

    class Meta:
        verbose_name = 'интенсионал типа вершины'
        verbose_name_plural = 'интенсионалы типов вершин'


class RelationshipTypeArtifactDefinition(ArtifactDefinition):
    class Meta:
        verbose_name = 'интенсионал типа связи'
        verbose_name_plural = 'интенсионалы типов связей'
class ArtifactAssignment(OntologyBase):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4(),
        editable=False
    )

    # definition: "ArtifactDefinition" = models.ForeignKey(
    #     "ArtifactDefinition",
    #     on_delete=models.CASCADE,
    #     related_name='usable_artifact_definition',
    #     help_text='Используемый ArtifactDefinition'
    # )
    #
    # instance: "Instance" = models.ForeignKey(
    #     "Instance",
    #     on_delete=models.CASCADE,
    #     related_name='artifact_assignments'
    # )
    #
    # instancable: "Instancable" = models.ForeignKey(
    #     "Instancable",
    #     on_delete=models.CASCADE,
    #     related_name='artifact_assignments'
    # )

    path = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        verbose_name = 'артефакт'
        verbose_name_plural = 'артефакты'
        abstract = True
    # ХЗ как сделать
    # content: "IOBase" = field(repr=False, init=False)




# ------- PropertytDefinitions and PropertyAssignments ------------

class PropertyDefinition(Definition):

    # Не написан DataType
    # type: # "DataType" = models.ForeignKey(
    #     'DataType',
    #     on_delete=models.SET_NULL,
    #     null=True,
    #     blank=True,
    #     related_name='property_definitions',
    # )
    required = models.BooleanField(
        default=False,
        help_text="Обязательное ли это свойство"
    )

    default = models.JSONField(
        null=True,
        blank=True,
        help_text="Значение по умолчанию"
    )
    initializable = models.BooleanField(
        default=True,
        help_text="Можно ли инициализировать значение при создании"
    )
    allows_multiple = models.BooleanField(
        default=True,
        help_text="Разрешать несколько значений"
    )
    min_assignments = models.IntegerField(
        null=True,
        blank=True,
        help_text="Минимальное число присвоений"
    )
    max_assignments = models.IntegerField(
        null=True,
        blank=True,
        help_text="Максимальное число присвоений"
    )

    class Meta:
        abstract = True

class PropertyAssignment(OntologyBase):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Уникальный идентификатор (UUID)"
    )
    value = models.JSONField(
        help_text="Произвольное значение свойства"
    )

    class Meta:
        verbose_name = "Присвоение свойства"
        verbose_name_plural = "Присвоения свойств"
        abstract = True

class VertexTypePropertyDefinition(PropertyDefinition):

    class Meta:
        verbose_name = "vertex type property definition"  # руский аналог не придуман
        verbose_name_plural = "vertex type property definitions" # руский аналог не придуман

class RelationshipTypePropertyDefinition(PropertyDefinition):

    class Meta:
        verbose_name = "relationship type property definition"  # руский аналог не придуман
        verbose_name_plural = "relationship type property definitions" # руский аналог не придуман



# ------- ImportDefinition ------------
class ImportDefinition(OntologyBase):
    file = models.CharField(
        max_length=1024,
        help_text="Путь или имя файла для импорта"
    )
    alias = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )

    class Meta:
        verbose_name = "Определение импорта"
        verbose_name_plural = "Определения импорта"


class DataType(Derivable):
    ontology_model: "OntologyModel" = models.ForeignKey(
        "OntologyModel",
        on_delete=models.CASCADE,
        related_name="data_types",
        blank=True,
        null=True
    )
    class Meta:
        verbose_name = 'тип данных'
        verbose_name_plural = 'типы данных'

class OntologyModel(OntologyEntity):
    imports = models.ManyToManyField(
        "ImportDefinition",
        related_name="import_definitions",
        blank=True,
        verbose_name="Импорты"
    )

    #  schema_definitions: Optional[Dict[str, Any]] = field(default_factory=dict, repr=False)

    class Meta:
        verbose_name = "модель онтологии"
        verbose_name_plural = "модели онтологии"