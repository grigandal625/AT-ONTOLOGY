from io import BytesIO
from io import IOBase
from pathlib import Path
from typing import Iterable

from at_ontology_parser.ontology.assignments import ArtifactAssignment
from at_ontology_parser.ontology.assignments import PropertyAssignment
from at_ontology_parser.ontology.handler import Ontology
from at_ontology_parser.ontology.instances import Relationship
from at_ontology_parser.ontology.instances import Vertex
from at_ontology_parser.parsing.parser import OntologyModule
from at_ontology_parser.parsing.parser import Parser
from at_ontology_parser.reference import OntologyReference
from django.core import exceptions
from django.db.transaction import atomic
from django.utils.translation import gettext_lazy as _

from at_ontology.apps.ontology import models
from at_ontology.apps.ontology_model.import_loader import DBLoader
from at_ontology.apps.ontology_model.service import OntologyModelService


class OntologyException(Exception):
    pass


class CreateOntologyException(OntologyException):
    pass


class BrokenOntologyException(OntologyException):
    pass


class OntologyService(object):
    @staticmethod
    def vertices_source_from_db(vertices: Iterable[models.Vertex]) -> dict:
        return {vertex.name: OntologyService.vertex_source_from_db(vertex) for vertex in vertices}

    @staticmethod
    def vertex_source_from_db(vertex: models.Vertex) -> dict:
        return {
            "label": vertex.label,
            "description": vertex.description,
            "type": vertex.type.name,
            "metadata": vertex.metadata,
            "properties": OntologyService.properties_source_from_db(vertex.properties.all()),
            "artifacts": OntologyService.artifacts_source_from_db(vertex.artifacts.all()),
        }

    @staticmethod
    def properties_source_from_db(
        properties: Iterable[models.VertexPropertyAssignment | models.RelationshipPropertyAssignment],
    ) -> dict:
        result = {}
        for prop in properties:
            if prop.definition.allows_multiple:
                if prop.definition.name not in result:
                    result[prop.definition.name] = [prop.value]
                else:
                    result[prop.definition.name].append(prop.value)
            else:
                result[prop.definition.name] = prop.value
        return result

    @staticmethod
    def artifacts_source_from_db(
        artifacts: Iterable[models.VertexArtifactAssignment | models.RelationshipArtifactAssignment],
    ) -> dict:
        result = {}
        for artifact in artifacts:
            if artifact.definition.allows_multiple:
                if artifact.definition.name not in result:
                    result[artifact.definition.name] = [artifact.path]
                else:
                    result[artifact.definition.name].append(artifact.path)
            else:
                result[artifact.definition.name] = artifact.path
        return result

    @staticmethod
    def relationships_source_from_db(relationships: Iterable[models.Relationship]) -> dict:
        return {
            relationship.name: OntologyService.relationship_source_from_db(relationship)
            for relationship in relationships
        }

    @staticmethod
    def relationship_source_from_db(relationship: models.Relationship) -> dict:
        return {
            "label": relationship.label,
            "description": relationship.description,
            "type": relationship.type.name,
            "source": relationship.source.name,
            "target": relationship.target.name,
            "metadata": relationship.metadata,
            "properties": OntologyService.properties_source_from_db(relationship.properties.all()),
            "artifacts": OntologyService.artifacts_source_from_db(relationship.artifacts.all()),
        }

    @staticmethod
    def ontology_source_from_db(ontology: models.Ontology) -> dict:
        return {
            "name": ontology.name,
            "description": ontology.description,
            "label": ontology.label,
            "imports": [f"<{imp.name}>" for imp in ontology.imports.all()],
            "vertices": OntologyService.vertices_source_from_db(ontology.vertices.all()),
            "relationships": OntologyService.relationships_source_from_db(ontology.relationships.all()),
        }

    @staticmethod
    def artifact_assignments_from_db(ontology: models.Ontology) -> dict[Path, IOBase]:
        result = {}

        for vertex in ontology.vertices.all():
            for artifact_assignment in vertex.artifacts.all():
                artifact_assignment: models.ArtifactAssignment
                result[artifact_assignment.path] = BytesIO(artifact_assignment.content)

        for relationship in ontology.relationships.all():
            for artifact_assignment in relationship.artifacts.all():
                artifact_assignment: models.ArtifactAssignment
                result[artifact_assignment.path] = BytesIO(artifact_assignment.content)

        return result

    @staticmethod
    @atomic
    def ontology_to_db(ontology: Ontology) -> models.Ontology:
        result = models.Ontology.objects.create(
            name=ontology.name,
            description=ontology.description,
            label=ontology.label,
        )

        for imp in ontology.imports:
            try:
                imported = OntologyModelService.get_imported_model(imp)
            except exceptions.ObjectDoesNotExist:
                raise CreateOntologyException(_("ontology_model_not_exists{name}").format(name=imported.alias))
            except exceptions.MultipleObjectsReturned:
                raise BrokenOntologyException(_("ontology_model_multiple{name}").format(name=imported.alias))
            result.imports.add(imported)

        for vertex in ontology.vertices.values():
            OntologyService.vertex_to_db(vertex, result)

        for relationship in ontology.relationships.values():
            OntologyService.relationship_to_db(relationship, result)

        OntologyService.artifact_contents_to_db(ontology, result)

        return result

    @staticmethod
    @atomic
    def vertex_to_db(vertex: Vertex, ontology: models.Ontology) -> models.Vertex:
        try:
            vertex_type = OntologyModelService.get_vertex_type(vertex.type, ontology)
        except exceptions.ObjectDoesNotExist:
            raise CreateOntologyException(_("ontology_model_not_exists{name}").format(name=vertex_type.alias))
        except exceptions.MultipleObjectsReturned:
            raise BrokenOntologyException(_("ontology_model_multiple{name}").format(name=vertex_type.alias))

        result = models.Vertex.objects.create(
            ontology=ontology,
            name=vertex.name,
            label=vertex.label,
            description=vertex.description,
            type=vertex_type,
        )

        for artifact in vertex.artifacts:
            OntologyService.vertex_artifact_to_db(artifact, result)

        for property in vertex.properties:
            OntologyService.vertex_property_to_db(property, result)

        return result

    @staticmethod
    @atomic
    def vertex_artifact_to_db(artifact: ArtifactAssignment, vertex: models.Vertex) -> models.VertexArtifactAssignment:
        result = models.VertexArtifactAssignment.objects.create(
            definition=OntologyModelService.get_vertex_artifact_definition(artifact.artifact, vertex),
            vertex=vertex,
            path=artifact.path,
        )
        return result

    @staticmethod
    @atomic
    def vertex_property_to_db(property: PropertyAssignment, vertex: models.Vertex) -> models.VertexPropertyAssignment:
        result = models.VertexPropertyAssignment.objects.create(
            definition=OntologyModelService.get_vertex_property_definition(property.property, vertex),
            vertex=vertex,
            value=property.value,
        )
        return result

    @staticmethod
    @atomic
    def relationship_to_db(relationship: Relationship, ontology: models.Ontology) -> models.Relationship:
        try:
            relationship_type = OntologyModelService.get_relationship_type(relationship.type, ontology)
        except exceptions.ObjectDoesNotExist:
            raise CreateOntologyException(_("ontology_model_not_exists{name}").format(name=relationship_type.alias))
        except exceptions.MultipleObjectsReturned:
            raise BrokenOntologyException(_("ontology_model_multiple{name}").format(name=relationship_type.alias))

        result = models.Relationship.objects.create(
            ontology=ontology,
            name=relationship.name,
            label=relationship.label,
            description=relationship.description,
            type=relationship_type,
            source=OntologyService.get_vertex(relationship.source, ontology),
            target=OntologyService.get_vertex(relationship.target, ontology),
        )

        for artifact in relationship.artifacts:
            OntologyService.relationship_artifact_to_db(artifact, result)

        for property in relationship.properties:
            OntologyService.relationship_property_to_db(property, result)

        return result

    @staticmethod
    @atomic
    def relationship_artifact_to_db(
        artifact: ArtifactAssignment, relationship: models.Relationship
    ) -> models.RelationshipArtifactAssignment:
        result = models.RelationshipArtifactAssignment.objects.create(
            definition=OntologyModelService.get_relationship_artifact_definition(artifact.artifact, relationship),
            relationship=relationship,
            path=artifact.path,
        )
        return result

    @staticmethod
    @atomic
    def relationship_property_to_db(
        property: PropertyAssignment, relationship: models.Relationship
    ) -> models.RelationshipPropertyAssignment:
        result = models.RelationshipPropertyAssignment.objects.create(
            definition=OntologyModelService.get_relationship_property_definition(property.property, relationship),
            relationship=relationship,
            value=property.value,
        )
        return result

    @staticmethod
    def get_vertex(vertex: OntologyReference[Vertex], ontology: models.Ontology) -> models.Vertex:
        return models.Vertex.objects.get(
            ontology=ontology,
            name=vertex.alias,
        )

    @staticmethod
    @atomic
    def artifact_contents_to_db(ontology: Ontology, ontology_db: models.Ontology) -> None:
        module: OntologyModule = ontology.owner
        if module is None or not isinstance(module, OntologyModule):
            raise CreateOntologyException(_("unexpected_module_type"))

        for vertex in ontology_db.vertices.all():
            for artifact_assignment in vertex.artifacts.all():
                OntologyService.artifact_content_to_db(artifact_assignment, module)

        for relationship in ontology_db.relationships.all():
            for artifact_assignment in relationship.artifacts.all():
                OntologyService.artifact_content_to_db(artifact_assignment, module)

    @staticmethod
    @atomic
    def artifact_content_to_db(
        artifact_assignment: models.VertexArtifactAssignment | models.RelationshipArtifactAssignment,
        module: OntologyModule,
    ) -> models.VertexArtifactAssignment | models.RelationshipArtifactAssignment:
        artifact = module.artifacts.get(artifact_assignment.path)

        if not artifact:
            raise CreateOntologyException(_("artifact_not_found{artifact}").format(artifact=artifact_assignment.path))

        content = artifact.read()
        if isinstance(content, str):
            content = content.encode(encoding="utf-8")

        if not isinstance(content, bytes):
            raise CreateOntologyException(
                _("artifact_content_not_bytes{artifact}").format(artifact=artifact_assignment.path)
            )

        artifact_assignment.content = content
        artifact_assignment.save()
        return artifact_assignment

    @staticmethod
    def ontology_archive_from_db(ontology: models.Ontology) -> Path:
        ontology_source = OntologyService.ontology_source_from_db(ontology)
        parser = Parser()
        parser.import_loaders.append(DBLoader())

        ont = parser.load_ontology_data(ontology_source, f"<{ontology.name}>", ontology.name)

        return parser.build_archive(ont)
