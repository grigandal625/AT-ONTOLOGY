from io import BytesIO
from io import IOBase
from pathlib import Path
from typing import Callable, Iterable

from at_ontology_parser.ontology.assignments import ArtifactAssignment
from at_ontology_parser.ontology.assignments import PropertyAssignment
from at_ontology_parser.ontology.handler import Ontology
from at_ontology_parser.ontology.instances import Relationship
from at_ontology_parser.ontology.instances import Vertex
from at_ontology_parser.parsing.parser import OntologyModule
from at_ontology_parser.parsing.parser import Parser, ModelModule
from at_ontology_parser.reference import OntologyReference
from django.core import exceptions
from django.db import IntegrityError, connection
from django.db.transaction import atomic
from django.db.models import Q
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
    def vertices_source_from_db(vertices: Iterable[models.Vertex], with_id: bool = True) -> dict:
        return {vertex.name: OntologyService.vertex_source_from_db(vertex, with_id=with_id) for vertex in vertices}

    @staticmethod
    def vertex_source_from_db(vertex: models.Vertex, with_id: bool = True) -> dict:
        result = {
            "label": vertex.label,
            "description": vertex.description,
            "type": vertex.type.name,
            "metadata": vertex.metadata,
            "properties": OntologyService.properties_source_from_db(vertex.properties.all()),
            "artifacts": OntologyService.artifacts_source_from_db(vertex.artifacts.all()),
        }

        if with_id:
            result["_uuid"] = str(vertex.id)
        return result

    @staticmethod
    def properties_source_from_db(
        properties: Iterable[models.VertexPropertyAssignment | models.RelationshipPropertyAssignment],
        with_id: bool = True,
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
        with_id: bool = True,
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
    def relationships_source_from_db(relationships: Iterable[models.Relationship], with_id: bool = True) -> dict:
        return {
            relationship.name: OntologyService.relationship_source_from_db(relationship, with_id=with_id)
            for relationship in relationships
        }

    @staticmethod
    def relationship_source_from_db(relationship: models.Relationship, with_id: bool = True) -> dict:
        result = {
            "label": relationship.label,
            "description": relationship.description,
            "type": relationship.type.name,
            "source": relationship.source.name,
            "target": relationship.target.name,
            "metadata": relationship.metadata,
            "properties": OntologyService.properties_source_from_db(relationship.properties.all()),
            "artifacts": OntologyService.artifacts_source_from_db(relationship.artifacts.all()),
        }
        if with_id:
            result["_uuid"] = str(relationship.id)
        return result

    @staticmethod
    def ontology_source_from_db(
        ontology: models.Ontology, 
        with_id: bool = True,
        vertex_query: Q = None,
        vertex_query_exclude: Q = None,
        relationship_query: Q = None,
        relationship_query_exclude: Q = None,

    ) -> dict:
        
        vertices = ontology.vertices.all()
        if vertex_query:
            vertices = vertices.filter(vertex_query)
        if vertex_query_exclude:
            vertices = vertices.exclude(vertex_query_exclude)
        
        relationships = ontology.relationships.all()
        if relationship_query:
            relationships = relationships.filter(relationship_query)
        if relationship_query_exclude:
            relationships = relationships.exclude(relationship_query_exclude)

        return {
            "name": ontology.name,
            "description": ontology.description,
            "label": ontology.label,
            "imports": [f"<{imp.name}>" for imp in ontology.imports.all()],
            "vertices": OntologyService.vertices_source_from_db(vertices, with_id=with_id),
            "relationships": OntologyService.relationships_source_from_db(relationships, with_id=with_id),
        }

    
    @staticmethod
    @atomic
    def vertices_to_db_bulk(
        vertices: Iterable[Vertex], 
        ontology: models.Ontology,
        content_getter: Callable[[str], bytes | None],
    ) -> list[models.Vertex]:

        def get_vertex_source(vertex: Vertex) -> dict:
            if not vertex.type.fulfilled:
                raise CreateOntologyException(_("type_not_fulfilled{alias}{entity}{name}").format(
                    alias=vertex.type.alias,
                    entity=vertex.__class__.__name__,
                    name=vertex.name,
                ))
            
            return {
                "id": vertex._uuid,
                "name": vertex.name,
                "label": vertex.label,
                "description": vertex.description,
                "type_id": vertex.type.value._uuid,
                "metadata": vertex.metadata,
                "ontology_id": ontology.id,
            }

        source = [get_vertex_source(vertex) for vertex in vertices]
        result = models.Vertex.objects.bulk_create([models.Vertex(**vertex) for vertex in source])

        properties = []
        artifacts = []

        for vertex in vertices:
            if vertex.properties:
                properties.extend(vertex.properties)
            if vertex.artifacts:
                artifacts.extend(vertex.artifacts)

        OntologyService.vertex_properties_to_db_bulk(properties)
        OntologyService.vertex_artifacts_to_db_bulk(artifacts, content_getter=content_getter)

        try:
            connection.check_constraints()
        except IntegrityError as e:
            raise CreateOntologyException(str(e))

        return result
    
    @staticmethod
    @atomic
    def vertex_properties_to_db_bulk(properties: Iterable[PropertyAssignment]) -> list[models.VertexPropertyAssignment]:
        
        def get_property_source(property: PropertyAssignment) -> dict:
            if not isinstance(property.owner, Vertex):
                raise CreateOntologyException(_("owner_wrong_type{entity}{name}{expected}").format(
                    entity=property.__class__.__name__, 
                    name=property.definition.alias,
                    expected=Vertex.__name__
                ))

            if not property.definition.fulfilled:
                raise CreateOntologyException(_("definition_not_fulfilled{alias}{entity}{owner}{owner_entity}").format(
                    alias=property.definition.alias,
                    entity=property.__class__.__name__,
                    name=property.definition.alias,
                    owner=property.owner.name,
                    owner_entity=property.owner.__class__.__name__,
                ))
            
            return {
                "id": property._uuid,
                "vertex_id": property.owner._uuid,
                "definition_id": property.definition.value._uuid,
                "value": property.value,
            }

        source = [get_property_source(property) for property in properties]
        result = models.VertexPropertyAssignment.objects.bulk_create([models.VertexPropertyAssignment(**property) for property in source])

        try:
            connection.check_constraints()
        except IntegrityError as e:
            raise CreateOntologyException(str(e))

        return result
    
    @staticmethod
    @atomic
    def vertex_artifacts_to_db_bulk(
        artifacts: Iterable[ArtifactAssignment],
        content_getter: Callable[[str], bytes | None],
    ) -> list[models.VertexArtifactAssignment]:
        
        def get_artifact_source(artifact: ArtifactAssignment) -> dict:
            if not isinstance(artifact.owner, Vertex):
                raise CreateOntologyException(_("owner_wrong_type{entity}{name}{expected}").format(
                    entity=artifact.__class__.__name__, 
                    name=artifact.definition.alias,
                    expected=Vertex.__name__,
                ))

            if not artifact.definition.fulfilled:
                raise CreateOntologyException(_("definition_not_fulfilled{alias}{entity}{owner}{owner_entity}").format(
                    alias=artifact.definition.alias,
                    entity=artifact.__class__.__name__,
                    name=artifact.definition.alias,
                    owner=artifact.owner.name,
                    owner_entity=artifact.owner.__class__.__name__,
                ))
            
            return {
                "id": artifact._uuid,
                "vertex_id": artifact.owner._uuid,
                "definition_id": artifact.definition.value._uuid,
                "content": content_getter(artifact.path) if artifact.path else None,
                "path": artifact.path,
            }
        
        source = [get_artifact_source(artifact) for artifact in artifacts]
        result = models.VertexArtifactAssignment.objects.bulk_create([models.VertexArtifactAssignment(**artifact) for artifact in source])

        try:
            connection.check_constraints()
        except IntegrityError as e:
            raise CreateOntologyException(str(e))

        return result
    
    @staticmethod
    @atomic
    def relationships_to_db_bulk(
        relationships: Iterable[Relationship], 
        ontology: models.Ontology,
        content_getter: Callable[[str], bytes | None],

    ) -> list[models.Relationship]:
        
        def get_relationship_source(relationship: Relationship) -> dict:
            if not relationship.type.fulfilled:
                raise CreateOntologyException(_("type_not_fulfilled{alias}{entity}{name}").format(
                    alias=relationship.type.alias,
                    entity=relationship.__class__.__name__,
                    name=relationship.name
                ))
            
            if not relationship.source.fulfilled:
                raise CreateOntologyException(_("source_not_fulfilled{alias}{entity}{name}").format(
                    alias=relationship.type.alias,
                    entity=relationship.__class__.__name__,
                    name=relationship.name
                ))
            
            if not relationship.target.fulfilled:
                raise CreateOntologyException(_("target_not_fulfilled{alias}{entity}{name}").format(
                    alias=relationship.type.alias,
                    entity=relationship.__class__.__name__,
                    name=relationship.name
                ))
            
            return {
                "id": relationship._uuid,
                "name": relationship.name,
                "label": relationship.label,
                "description": relationship.description,
                "type_id": relationship.type.value._uuid,
                "source_id": relationship.source.value._uuid,
                "target_id": relationship.target.value._uuid,
                "metadata": relationship.metadata,
                "ontology_id": ontology.id,
            }
        
        source = [get_relationship_source(relationship) for relationship in relationships]
        result = models.Relationship.objects.bulk_create([models.Relationship(**relationship) for relationship in source])

        properties = []
        artifacts = []

        for relationship in relationships:
            if relationship.properties:
                properties.extend(relationship.properties)
            if relationship.artifacts:
                artifacts.extend(relationship.artifacts)

        OntologyService.relationship_properties_to_db_bulk(properties)
        OntologyService.relationship_artifacts_to_db_bulk(artifacts, content_getter=content_getter)

        try:
            connection.check_constraints()
        except IntegrityError as e:
            raise CreateOntologyException(str(e))

        return result
    
    @staticmethod
    @atomic
    def relationship_properties_to_db_bulk(properties: Iterable[PropertyAssignment]) -> list[models.RelationshipPropertyAssignment]:
        
        def get_property_source(property: PropertyAssignment) -> dict:
           
            if not isinstance(property.owner, Relationship):
                raise CreateOntologyException(_("owner_wrong_type{entity}{name}{expected}").format(
                    entity=property.__class__.__name__, 
                    name=property.definition.alias,
                    expected=Relationship.__name__,
                ))

            if not property.definition.fulfilled:
                raise CreateOntologyException(_("definition_not_fulfilled{alias}{entity}{owner}{owner_entity}").format(
                    alias=property.definition.alias,
                    entity=property.__class__.__name__,
                    owner=property.owner.name,
                    owner_entity=property.owner.__class__.__name__,
                ))
            
            return {
                "id": property._uuid,
                "relationship_id": property.owner._uuid,
                "definition_id": property.definition.value._uuid,
                "value": property.value,
            }
        
        source = [get_property_source(property) for property in properties]
        result = models.RelationshipPropertyAssignment.objects.bulk_create([models.RelationshipPropertyAssignment(**property) for property in source])

        try:
            connection.check_constraints()
        except IntegrityError as e:
            raise CreateOntologyException(str(e))

        return result
    
    @staticmethod
    @atomic
    def relationship_artifacts_to_db_bulk(
        artifacts: Iterable[ArtifactAssignment],
        content_getter: Callable[[str], bytes | None],
    ) -> list[models.RelationshipArtifactAssignment]:
        
        def get_artifact_source(artifact: ArtifactAssignment) -> dict:
            if not isinstance(artifact.owner, Relationship):
                raise CreateOntologyException(_("owner_wrong_type{entity}{name}{expected}").format(
                    entity=artifact.__class__.__name__, 
                    name=artifact.definition.alias,
                    expected=Relationship.__name__,
                ))

            if not artifact.definition.fulfilled:
                raise CreateOntologyException(_("definition_not_fulfilled{alias}{entity}{owner}{owner_entity}").format(
                    alias=artifact.definition.alias,
                    entity=artifact.__class__.__name__,
                    name=artifact.definition.alias,
                    owner=artifact.owner.name,
                    owner_entity=artifact.owner.__class__.__name__,
                ))
            
            return {
                "id": artifact._uuid,
                "relationship_id": artifact.owner._uuid,
                "definition_id": artifact.definition.value._uuid,
                "content": content_getter(artifact.path) if artifact.path else None,
                "path": artifact.path,
            }
        
        source = [get_artifact_source(artifact) for artifact in artifacts]
        result = models.RelationshipArtifactAssignment.objects.bulk_create([models.RelationshipArtifactAssignment(**artifact) for artifact in source])

        try:
            connection.check_constraints()
        except IntegrityError as e:
            raise CreateOntologyException(str(e))

        return result

    @staticmethod
    @atomic
    def ontology_to_db(ontology: Ontology) -> models.Ontology:
        result = models.Ontology.objects.create(
            name=ontology.name,
            label=ontology.label,
            description=ontology.description,
        )

        for resolved in ontology._resolved_imports:
            imported_module = resolved[2]
            try:
                imported: models.OntologyModel = imported_module._meta["ontology_model"]
            except KeyError:
                raise CreateOntologyException(_("recursive_module_load_unsupported{name}").format(name=imported_module.orig_name))
            
            if not isinstance(imported, models.OntologyModel):
                raise CreateOntologyException(_("unexpected_import_type{name}").format(name=imported_module.orig_name))

            result.imports.add(imported)

        content_getter = OntologyService.get_content_getter(ontology)
        OntologyService.vertices_to_db_bulk(ontology.vertices.values(), result, content_getter=content_getter)
        OntologyService.relationships_to_db_bulk(ontology.relationships.values(), result, content_getter=content_getter)

        return result

    @staticmethod
    def get_content_getter(ontology: Ontology) -> Callable[[str], bytes | None]:
        def default_content_getter(path: str) -> bytes | None:
            if not isinstance(ontology.owner, ModelModule):
                raise CreateOntologyException(_("owner_wrong_type{entity}{name}{expected}").format(
                    entity=ontology.owner.__class__.__name__, 
                    name=ontology.owner, 
                    expected=ModelModule.__name__
                ))
            
            data = ontology.owner.artifacts.get(path).read()

            if isinstance(data, str):
                data = data.encode('utf-8')

            if not isinstance(data, bytes):
                raise CreateOntologyException(_("artifact_not_binary{path}").format(
                    path=path
                ))
            return data
        
        return default_content_getter

