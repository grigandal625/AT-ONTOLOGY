from typing import TYPE_CHECKING

from django.core.exceptions import ValidationError
from django.db import models
from jsonschema import exceptions
from jsonschema import validate
from at_ontology.apps.ontology_model.models import Instance
from at_ontology.apps.ontology_model.models import ArtifactAssignment
from at_ontology.apps.ontology_model.models import PropertyAssignment
from at_ontology.apps.ontology_model.models import OntologyEntity

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





class Vertex(Instance):

    ontology: "Ontology" = models.ForeignKey(
        'Ontology',
        on_delete=models.CASCADE,
        related_name='vertices'
    )

    type: "VertexType" = models.ForeignKey(
        'ontology_model.VertexType',
        on_delete=models.PROTECT,
        related_name='vertex_type'
    )



    class Meta:
        verbose_name = 'вершина'
        verbose_name_plural = 'вершины'


class VertexArtifactAssignment(ArtifactAssignment):
    definition: "VertexTypeArtifactDefinition" = models.ForeignKey(
        "ontology_model.VertexTypeArtifactDefinition",
        on_delete=models.CASCADE,
        related_name='vertex_artifact_assignments',
        help_text='Используемый ArtifactDefinition'
    )

    vertex: "Vertex" = models.ForeignKey(
        "Vertex",
        on_delete=models.CASCADE,
        related_name='artifact_assignments'
    )

    vertex_type: "VertexType" = models.ForeignKey(
        "ontology_model.VertexType",
        on_delete=models.CASCADE,
        related_name='vertex_type_artifact_assignments'
    )

    class Meta:
        verbose_name = 'артефакт вершины'
        verbose_name_plural = 'артефакты вершины'


class VertexPropertyAssignment(PropertyAssignment):
    definition: "VertexTypePropertyDefinition" = models.ForeignKey(
        "ontology_model.VertexTypePropertyDefinition",
        on_delete=models.CASCADE,
        related_name='vertex_property_assignments',
        help_text='Используемый ArtifactDefinition'
    )

    vertex: "Vertex" = models.ForeignKey(
        "Vertex",
        on_delete=models.CASCADE,
        related_name='property_assignments'
    )

    vertex_type: "VertexType" = models.ForeignKey(
        "ontology_model.VertexType",
        on_delete=models.CASCADE,
        related_name='vertex_type_property_assigments'
    )

    class Meta:
        verbose_name = 'свойство вершины'
        verbose_name_plural = 'свойства вершин'


class Relationship(Instance):
    ontology: "Ontology" = models.ForeignKey(
        'Ontology',
        on_delete=models.CASCADE,
        related_name='relationships'
    )

    type: "RelationshipType" = models.ForeignKey(
        'ontology_model.RelationshipType',
        on_delete=models.PROTECT,
        related_name='relationships'
    )

    source: "Vertex" = models.ForeignKey(
        'Vertex',
        on_delete=models.CASCADE,
        related_name='outgoing_relationship'
    )

    target: "Vertex" = models.ForeignKey(
        'Vertex',
        on_delete=models.CASCADE,
        related_name='incoming_relationship'
    )

    class Meta:
        verbose_name = 'связь'
        verbose_name_plural = 'связи'
        ordering = ['type']


class RelationshipArtifactAssignment(ArtifactAssignment):
    definition: "RelationshipTypeArtifactDefinition" = models.ForeignKey(
        "ontology_model.RelationshipTypeArtifactDefinition",
        on_delete=models.CASCADE,
        related_name='definition_relationship_artifact_assignments',
        help_text='Используемый ArtifactDefinition'
    )

    relationship: "Relationship" = models.ForeignKey(
        "Relationship",
        on_delete=models.CASCADE,
        related_name='relationship_artifact_assignments'
    )

    relationship_type: "RelationshipType" = models.ForeignKey(
        "ontology_model.RelationshipType",
        on_delete=models.CASCADE,
        related_name='relationship_type_artifact_assigments'
    )

    class Meta:
        verbose_name = 'артефакт связи'
        verbose_name_plural = 'артефакты связей'


class RelationshipPropertyAssignment(PropertyAssignment):
    definition: "RelationshipTypePropertyDefinition" = models.ForeignKey(
        "ontology_model.RelationshipTypePropertyDefinition",
        on_delete=models.CASCADE,
        related_name='relationship_property_assignments',
        help_text='Используемый ArtifactDefinition'
    )

    relationship: "Relationship" = models.ForeignKey(
        "Relationship",
        on_delete=models.CASCADE,
        related_name='artifact_assignments'
    )

    relationship_type: "RelationshipType" = models.ForeignKey(
        "ontology_model.RelationshipType",
        on_delete=models.CASCADE,
        related_name='relationship_type_property_assigments'
    )

    class Meta:
        verbose_name = 'свойство связи'
        verbose_name_plural = 'свойства связей'


class Ontology(OntologyEntity):

    imports = models.ManyToManyField(
        "OntologyModel",
        related_name="import_definitions",
        blank=True,
        verbose_name="Импорты"
    )
    class Meta:
        verbose_name = "онтология"
        verbose_name_plural = "онтологии"
