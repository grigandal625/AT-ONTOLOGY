import uuid
from django.core.serializers.json import DjangoJSONEncoder
from django.core.exceptions import ValidationError

from django.db import models
from jsonschema import Draft7Validator
from jsonschema import exceptions


# Create your models here.






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
        related_name="vertex_types"
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
        related_name="relationship_types"
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


    vertex_type: "VertexType" = models.ForeignKey(
        "VertexType",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="vertex_type_artifact_definitions"
    )

    class Meta:
        verbose_name = 'интенсионал типа вершины'
        verbose_name_plural = 'интенсионалы типов вершин'


class RelationshipTypeArtifactDefinition(ArtifactDefinition):
    relationship_type: "RelationshipType" = models.ForeignKey(
        "RelationshipType",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="relation_type_artifact_definitions"
    )
    class Meta:
        verbose_name = 'интенсионал типа связи'
        verbose_name_plural = 'интенсионалы типов связей'
class ArtifactAssignment(OntologyBase):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4(),
        editable=False
    )


    path = models.CharField(max_length=255, blank=True, null=True)

    content = models.BinaryField(
        null=True,
        blank=True
    )
    class Meta:
        verbose_name = 'артефакт'
        verbose_name_plural = 'артефакты'
        abstract = True






# ------- PropertytDefinitions and PropertyAssignments ------------

class PropertyDefinition(Definition):

    # Не написан DataType

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


    type: "DataType" = models.ForeignKey(
        'DataType',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='vertex_types_property_definitions',
    )

    vertex_type: "VertexType" = models.ForeignKey(
        "VertexType",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="vertex_type_property_definitions"
    )
    class Meta:
        verbose_name = "vertex type property definition"
        verbose_name_plural = "vertex type property definitions"

class RelationshipTypePropertyDefinition(PropertyDefinition):



    type: "DataType" = models.ForeignKey(
        'DataType',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='relationship_types_property_definitions',
    )

    relationship_type: "RelationshipType" = models.ForeignKey(
        "RelationshipType",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="relation_type_property_definitions"
    )

    class Meta:
        verbose_name = "relationship type property definition"  # руский аналог не придуман
        verbose_name_plural = "relationship type property definitions" # руский аналог не придуман



# ------- ImportDefinition ------------


class DataType(Derivable):
    ontology_model: "OntologyModel" = models.ForeignKey(
        "OntologyModel",
        on_delete=models.CASCADE,
        related_name="data_types",
        blank=True,
        null=True
    )

    object_schema = models.JSONField(
        null=True,
        blank=True,
        help_text="Raw schema as JSON string"
    )
    class Meta:
        verbose_name = 'тип данных'
        verbose_name_plural = 'типы данных'

class OntologyModel(OntologyEntity):
    imports = models.ManyToManyField(
        "OntologyModel",
        related_name="import_definitions",
        blank=True,
        verbose_name="Импорты"
    )


    class Meta:
        verbose_name = "модель онтологии"
        verbose_name_plural = "модели онтологии"