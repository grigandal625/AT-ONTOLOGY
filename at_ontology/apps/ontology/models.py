from typing import TYPE_CHECKING

from django.db import models
from django.utils.translation import gettext_lazy as _

from at_ontology.apps.ontology_model.models import ArtifactAssignment
from at_ontology.apps.ontology_model.models import Instance
from at_ontology.apps.ontology_model.models import OntologyEntity
from at_ontology.apps.ontology_model.models import OntologyModel
from at_ontology.apps.ontology_model.models import PropertyAssignment

if TYPE_CHECKING:
    from at_ontology.apps.ontology_model.models import (
        VertexType,
        RelationshipType,
        VertexTypePropertyDefinition,
        RelationshipTypePropertyDefinition,
        VertexTypeArtifactDefinition,
        RelationshipTypeArtifactDefinition,
    )


class Vertex(Instance):
    ontology: "Ontology" = models.ForeignKey(
        "Ontology",
        on_delete=models.CASCADE,
        related_name="vertices",
        verbose_name=_("ontology"),
    )

    type: "VertexType" = models.ForeignKey(
        "ontology_model.VertexType",
        on_delete=models.PROTECT,
        related_name="vertex_type",
        verbose_name=_("vertex_type"),
    )

    class Meta:
        verbose_name = _("vertex")
        verbose_name_plural = _("vertices")

        constraints = [
            models.UniqueConstraint(
                fields=["name", "ontology"],
                name="unique_vertex_in_ontology",
            )
        ]


class VertexArtifactAssignment(ArtifactAssignment):
    definition: "VertexTypeArtifactDefinition" = models.ForeignKey(
        "ontology_model.VertexTypeArtifactDefinition",
        on_delete=models.CASCADE,
        related_name="vertex_artifacts",
        verbose_name=_("artifact_definition"),
        help_text=_("artifact_definition_used"),
    )

    vertex: "Vertex" = models.ForeignKey(
        "Vertex",
        on_delete=models.CASCADE,
        related_name="artifacts",
        verbose_name=_("vertex"),
    )

    class Meta:
        verbose_name = _("vertex_artifact_assignment")
        verbose_name_plural = _("vertex_artifact_assignments")


class VertexPropertyAssignment(PropertyAssignment):
    definition: "VertexTypePropertyDefinition" = models.ForeignKey(
        "ontology_model.VertexTypePropertyDefinition",
        on_delete=models.CASCADE,
        related_name="vertex_properties",
        verbose_name=_("property_definition"),
        help_text=_("property_definition_used"),
    )

    vertex: "Vertex" = models.ForeignKey(
        "Vertex",
        on_delete=models.CASCADE,
        related_name="properties",
        verbose_name=_("vertex"),
    )

    class Meta:
        verbose_name = _("vertex_property_assignment")
        verbose_name_plural = _("vertex_property_assignments")


class Relationship(Instance):
    ontology: "Ontology" = models.ForeignKey(
        "Ontology",
        on_delete=models.CASCADE,
        related_name="relationships",
        verbose_name=_("ontology"),
    )

    type: "RelationshipType" = models.ForeignKey(
        "ontology_model.RelationshipType",
        on_delete=models.PROTECT,
        related_name="relationships",
        verbose_name=_("relationship_type"),
    )

    source: "Vertex" = models.ForeignKey(
        "Vertex",
        on_delete=models.CASCADE,
        related_name="output_relationships",
        verbose_name=_("source_vertex"),
    )

    target: "Vertex" = models.ForeignKey(
        "Vertex",
        on_delete=models.CASCADE,
        related_name="input_relationships",
        verbose_name=_("target_vertex"),
    )

    class Meta:
        verbose_name = _("relationship")
        verbose_name_plural = _("relationships")
        ordering = ["type"]

        constraints = [
            models.UniqueConstraint(
                fields=["name", "ontology"],
                name="unique_relationship_in_ontology",
            )
        ]

    def __str__(self):
        return self.name


class RelationshipArtifactAssignment(ArtifactAssignment):
    definition: "RelationshipTypeArtifactDefinition" = models.ForeignKey(
        "ontology_model.RelationshipTypeArtifactDefinition",
        on_delete=models.CASCADE,
        related_name="relationship_artifacts",
        verbose_name=_("artifact_definition"),
        help_text=_("artifact_definition_used"),
    )

    relationship: "Relationship" = models.ForeignKey(
        "Relationship",
        on_delete=models.CASCADE,
        related_name="artifacts",
        verbose_name=_("relationship"),
    )

    class Meta:
        verbose_name = _("relationship_artifact_assignment")
        verbose_name_plural = _("relationship_artifact_assignments")


class RelationshipPropertyAssignment(PropertyAssignment):
    definition: "RelationshipTypePropertyDefinition" = models.ForeignKey(
        "ontology_model.RelationshipTypePropertyDefinition",
        on_delete=models.CASCADE,
        related_name="relationship_properties",
        verbose_name=_("property_definition"),
        help_text=_("property_definition_used"),
    )

    relationship: "Relationship" = models.ForeignKey(
        "Relationship",
        on_delete=models.CASCADE,
        related_name="properties",
        verbose_name=_("relationship"),
    )

    class Meta:
        verbose_name = _("relationship_property_assignment")
        verbose_name_plural = _("relationship_property_assignments")


class Ontology(OntologyEntity):
    imports = models.ManyToManyField(
        OntologyModel,
        related_name="ontology_importers",
        blank=True,
        verbose_name=_("imports"),
    )

    class Meta:
        verbose_name = _("ontology")
        verbose_name_plural = _("ontologies")

        constraints = [
            models.UniqueConstraint(
                fields=["name"],
                name="unique_ontology",
            )
        ]
