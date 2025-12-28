from typing import Any
import uuid

from django.db import models
from at_ontology_parser.model.definitions.constraint_definition import ONTOLOGY_CONSTRAINTS
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


class OntologyBase(models.Model):
    class Meta:
        abstract = True


class OntologyEntity(OntologyBase):
    name = models.CharField(max_length=255, verbose_name=_("name"))
    label = models.CharField(max_length=255, null=True, blank=True, verbose_name=_("label"))
    description = models.TextField(null=True, blank=True, verbose_name=_("description"))

    class Meta:
        abstract = True


class Derivable(OntologyEntity):
    derived_from: "Derivable" = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="derivations",
        verbose_name=_("derived_from"),
    )

    class Meta:
        abstract = True


class Instancable(Derivable):
    metadata = models.JSONField(null=True, blank=True, verbose_name=_("metadata"))

    class Meta:
        abstract = True
        verbose_name = _("instantiable_entity")
        verbose_name_plural = _("instantiable_entities")


class Definition(OntologyEntity):
    class Meta:
        verbose_name = _("definition")
        verbose_name_plural = _("definitions")
        abstract = True


class VertexType(Instancable):
    ontology_model: "OntologyModel" = models.ForeignKey(
        "OntologyModel",
        on_delete=models.CASCADE,
        related_name="vertex_types",
        verbose_name=_("ontology_model"),
    )

    class Meta:
        verbose_name = _("vertex_type")
        verbose_name_plural = _("vertex_types")


class RelationshipType(Instancable):
    valid_source_types = models.ManyToManyField(
        "VertexType",
        related_name="as_source_types",
        blank=True,
        verbose_name=_("valid_source_types"),
    )
    valid_target_types = models.ManyToManyField(
        "VertexType",
        related_name="as_target_types",
        blank=True,
        verbose_name=_("valid_target_types"),
    )

    ontology_model: "OntologyModel" = models.ForeignKey(
        "OntologyModel",
        on_delete=models.CASCADE,
        related_name="relationship_types",
        verbose_name=_("ontology_model"),
    )

    class Meta:
        verbose_name = _("relationship_type")
        verbose_name_plural = _("relationship_types")

    def __str__(self):
        return self.name


class Instance(OntologyEntity):
    type: "Instancable" = models.ForeignKey(
        "Instancable",
        on_delete=models.PROTECT,
        related_name="instances",
        help_text=_("instance_type"),
    )
    metadata = models.JSONField(null=True, blank=True, verbose_name=_("metadata"))

    class Meta:
        verbose_name = _("instance")
        verbose_name_plural = _("instances")
        abstract = True


# ------- Artifact Definitions and Assignments ------------

class ArtifactDefinition(Definition):
    default_path = models.CharField(
        max_length=255, null=True, blank=True, verbose_name=_("default_path")
    )
    default_content = models.BinaryField(null=True, blank=True, verbose_name=_("default_content"), default=None)
    mime_type = models.CharField(
        max_length=255,
        default="application/octet-stream",
        verbose_name=_("mime_type"),
    )
    required = models.BooleanField(default=False, verbose_name=_("required"))
    allows_multiple = models.BooleanField(default=True, verbose_name=_("allows_multiple"))
    min_assignments = models.IntegerField(null=True, blank=True, verbose_name=_("min_assignments"))
    max_assignments = models.IntegerField(null=True, blank=True, verbose_name=_("max_assignments"))

    class Meta:
        verbose_name = _("artifact_definition")
        verbose_name_plural = _("artifact_definitions")
        abstract = True


class VertexTypeArtifactDefinition(ArtifactDefinition):
    vertex_type: "VertexType" = models.ForeignKey(
        "VertexType",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="artifacts",
        verbose_name=_("vertex_type"),
    )

    class Meta:
        verbose_name = _("vertex_type_artifact_definition")
        verbose_name_plural = _("vertex_type_artifact_definitions")


class RelationshipTypeArtifactDefinition(ArtifactDefinition):
    relationship_type: "RelationshipType" = models.ForeignKey(
        "RelationshipType",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="artifacts",
        verbose_name=_("relationship_type"),
    )

    class Meta:
        verbose_name = _("relationship_type_artifact_definition")
        verbose_name_plural = _("relationship_type_artifact_definitions")


class ArtifactAssignment(OntologyBase):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_("id"),
    )
    path = models.CharField(max_length=255, blank=True, null=True, verbose_name=_("path"))
    content = models.BinaryField(null=True, blank=True, verbose_name=_("content"))

    class Meta:
        verbose_name = _("artifact")
        verbose_name_plural = _("artifacts")
        abstract = True


# ------- Property Definitions and Assignments ------------

class PropertyDefinition(Definition):
    required = models.BooleanField(default=False, verbose_name=_("required"))
    default = models.JSONField(null=True, blank=True, verbose_name=_("default_value"))
    initializable = models.BooleanField(default=True, verbose_name=_("initializable"))
    allows_multiple = models.BooleanField(default=True, verbose_name=_("allows_multiple"))
    min_assignments = models.IntegerField(null=True, blank=True, verbose_name=_("min_assignments"))
    max_assignments = models.IntegerField(null=True, blank=True, verbose_name=_("max_assignments"))

    class Meta:
        abstract = True
        verbose_name = _("property_definition")
        verbose_name_plural = _("property_definitions")


class PropertyAssignment(OntologyBase):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_("id"),
    )
    value = models.JSONField(verbose_name=_("value"))

    class Meta:
        verbose_name = _("property_assignment")
        verbose_name_plural = _("property_assignments")
        abstract = True


class VertexTypePropertyDefinition(PropertyDefinition):
    type: "DataType" = models.ForeignKey(
        "DataType",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="vertices_properties",
        verbose_name=_("data_type"),
    )

    vertex_type: "VertexType" = models.ForeignKey(
        "VertexType",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="properties",
        verbose_name=_("vertex_type"),
    )

    class Meta:
        verbose_name = _("vertex_type_property_definition")
        verbose_name_plural = _("vertex_type_property_definitions")


class RelationshipTypePropertyDefinition(PropertyDefinition):
    type: "DataType" = models.ForeignKey(
        "DataType",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="relationships_properties",
        verbose_name=_("data_type"),
    )

    relationship_type: "RelationshipType" = models.ForeignKey(
        "RelationshipType",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="properties",
        verbose_name=_("relationship_type"),
    )

    class Meta:
        verbose_name = _("relationship_type_property_definition")
        verbose_name_plural = _("relationship_type_property_definitions")


# ------- DataType ------------

class DataType(Derivable):
    ontology_model: "OntologyModel" = models.ForeignKey(
        "OntologyModel",
        on_delete=models.CASCADE,
        related_name="data_types",
        blank=True,
        null=True,
        verbose_name=_("ontology_model"),
    )

    object_schema = models.JSONField(
        null=True,
        blank=True,
        help_text=_("object_schema"),
    )

    class Meta:
        verbose_name = _("data_type")
        verbose_name_plural = _("data_types")


class OntologyModel(OntologyEntity):
    imports = models.ManyToManyField(
        "self",
        related_name="ontology_model_importers",
        blank=True,
        verbose_name=_("imports"),
    )

    class Meta:
        verbose_name = _("ontology_model")
        verbose_name_plural = _("ontology_models")


def validate_constraint_data(data: dict) -> None:
    if not isinstance(data, dict):
        raise ValidationError(_("constraint_invalid_data"))
    if len(data.keys()) != 1:
        raise ValidationError(_("constraint_single_key_required"))
    key=next(iter(data.keys()))
    if key not in ONTOLOGY_CONSTRAINTS.mapping():
        raise ValidationError(_("constraint_invalid_key{key}".format(key=key)))


class ConstraintDefinition(OntologyBase):
    data_type = models.ForeignKey(
        "DataType",
        on_delete=models.CASCADE,
        related_name="constraints",
        verbose_name=_("data_type"),
    )
    name = models.CharField(
        verbose_name=_("constraint_type"),
        choices=[(k, _(k)) for k in ONTOLOGY_CONSTRAINTS.mapping()],
    )
    data: dict = models.JSONField(
        verbose_name=_("constraint_data"),
        validators=[validate_constraint_data],
    )

    class Meta:
        verbose_name = _("constraint_definition")
        verbose_name_plural = _("constraint_definitions")
