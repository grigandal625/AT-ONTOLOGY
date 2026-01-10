from io import BytesIO
from io import IOBase
from pathlib import Path
from typing import Callable, Iterable
from typing import Optional
from typing import TYPE_CHECKING
from typing import Union

from at_ontology_parser.model.definitions import ArtifactDefinition
from at_ontology_parser.model.definitions import ConstraintDefinition, ImportDefinition
from at_ontology_parser.model.definitions import PropertyDefinition
from at_ontology_parser.model.handler import OntologyModel
from at_ontology_parser.model.types import DataType
from at_ontology_parser.model.types import RelationshipType
from at_ontology_parser.model.types import VertexType
from at_ontology_parser.parsing.parser import ModelModule
from at_ontology_parser.parsing.parser import Parser
from at_ontology_parser.reference import OntologyReference
from django.core import exceptions
from django.db import IntegrityError, connection
from django.db.models import QuerySet
from django.db.transaction import atomic
from django.utils.translation import gettext_lazy as _

from at_ontology.apps.ontology_model import models

if TYPE_CHECKING:
    from at_ontology.apps.ontology import models as ontology_models


class OntologyModelException(Exception):
    pass


class CreateModelException(OntologyModelException):
    pass


class BrokenModelException(OntologyModelException):
    pass


class OntologyModelService:
    @staticmethod
    def data_type_source_from_db(data_type: models.DataType, with_id: bool = True) -> dict:
        result = {
            "description": data_type.description,
            "derived_from": data_type.derived_from.name if data_type.derived_from else None,
            "label": data_type.label,
            "constraints": [constraint.data for constraint in data_type.constraints.all()]
            if data_type.constraints.all().exists()
            else None,
            "object_schema": data_type.object_schema,
        }

        if with_id:
            result["_uuid"] = str(data_type.id)
        return result

    @staticmethod
    def data_types_source_from_db(data_types: Iterable[models.DataType], with_id: bool = True) -> dict:
        return {data_type.name: OntologyModelService.data_type_source_from_db(data_type, with_id=with_id) for data_type in data_types}

    @staticmethod
    def vertex_type_source_from_db(vertex_type: models.VertexType, with_id: bool = True) -> dict:
        result = {
            "description": vertex_type.description,
            "label": vertex_type.label,
            "derived_from": vertex_type.derived_from.name if vertex_type.derived_from else None,
            "metadata": vertex_type.metadata,
            "properties": OntologyModelService.properties_source_from_db(vertex_type.properties.all(), with_id=with_id),
            "artifacts": OntologyModelService.artifacts_source_from_db(vertex_type.artifacts.all(), with_id=with_id),
        }

        if with_id:
            result["_uuid"] = str(vertex_type.id)
        return result


    @staticmethod
    def vertex_types_source_from_db(vertex_types: Iterable[models.VertexType], with_id: bool = True) -> dict:
        return {
            vertex_type.name: OntologyModelService.vertex_type_source_from_db(vertex_type, with_id=with_id)
            for vertex_type in vertex_types
        }

    @staticmethod
    def artifact_definition_source_from_db(
        artifact: models.VertexTypeArtifactDefinition | models.RelationshipTypeArtifactDefinition,
        with_id: bool = True
    ) -> dict:
        result = {
            "description": artifact.description,
            "label": artifact.label,
            "required": artifact.required,
            "default_path": artifact.default_path,
            "mime_type": artifact.mime_type,
            "allows_multiple": artifact.allows_multiple,
            "min_assignments": artifact.min_assignments,
            "max_assignments": artifact.max_assignments,
        }

        if with_id:
            result["_uuid"] = str(artifact.id)
        return result

    @staticmethod
    def artifacts_source_from_db(artifacts: Iterable[models.ArtifactDefinition], with_id: bool = True) -> dict:
        return {
            artifact.name: OntologyModelService.artifact_definition_source_from_db(artifact, with_id=with_id) for artifact in artifacts
        }

    @staticmethod
    def property_definition_source_from_db(
        property: models.VertexTypePropertyDefinition | models.RelationshipTypePropertyDefinition,
        with_id: bool = True
    ) -> dict:
        result = {
            "description": property.description,
            "type": property.type.name,
            "label": property.label,
            "required": property.required,
            "default": property.default,
            "allows_multiple": property.allows_multiple,
            "min_assignments": property.min_assignments,
            "max_assignments": property.max_assignments,
        }

        if with_id:
            result["_uuid"] = str(property.id)
        return result

    @staticmethod
    def properties_source_from_db(properties: Iterable[models.PropertyDefinition], with_id: bool = True) -> dict:
        return {
            property.name: OntologyModelService.property_definition_source_from_db(property, with_id=with_id) for property in properties
        }

    @staticmethod
    def relationship_type_source_from_db(relationship_type: models.RelationshipType, with_id: bool = True) -> dict:
        result = {
            "description": relationship_type.description,
            "label": relationship_type.label,
            "metadata": relationship_type.metadata,
            "derived_from": relationship_type.derived_from.name if relationship_type.derived_from else None,
            "valid_source_types": [t.name for t in relationship_type.valid_source_types.all()],
            "valid_target_types": [t.name for t in relationship_type.valid_target_types.all()],
            "properties": OntologyModelService.properties_source_from_db(relationship_type.properties.all()),
            "artifacts": OntologyModelService.artifacts_source_from_db(relationship_type.artifacts.all()),
        }

        if with_id:
            result["_uuid"] = str(relationship_type.id)
        return result

    @staticmethod
    def relationship_types_source_from_db(relationship_types: Iterable[models.RelationshipType], with_id: bool = True) -> dict:
        return {
            relationship_type.name: OntologyModelService.relationship_type_source_from_db(relationship_type, with_id=with_id)
            for relationship_type in relationship_types
        }

    @staticmethod
    def ontology_model_source_from_db(ontology_model: models.OntologyModel, with_id: bool = True) -> dict:
        return {
            "name": ontology_model.name,
            "description": ontology_model.description,
            "label": ontology_model.label,
            "imports": [f"<{imported.name}>" for imported in ontology_model.imports.all()],
            "data_types": OntologyModelService.data_types_source_from_db(ontology_model.data_types.all(), with_id=with_id),
            "vertex_types": OntologyModelService.vertex_types_source_from_db(ontology_model.vertex_types.all(), with_id=with_id),
            "relationship_types": OntologyModelService.relationship_types_source_from_db(
                ontology_model.relationship_types.all()
            ),
        }

    @staticmethod
    def default_artifacts_from_db(ontology_model: models.OntologyModel) -> dict[Path, IOBase]:
        result = {}
        for vertex_type in ontology_model.vertex_types.all():
            for artifact in vertex_type.artifacts.all():
                artifact: models.ArtifactDefinition
                if artifact.default_path and artifact.default_content:
                    result[Path(artifact.default_path)] = BytesIO(artifact.default_content)
        for relationship_type in ontology_model.relationship_types.all():
            for artifact in relationship_type.artifacts.all():
                artifact: models.ArtifactDefinition
                if artifact.default_path and artifact.default_content:
                    result[Path(artifact.default_path)] = BytesIO(artifact.default_content)
        return result
    
    @staticmethod
    @atomic
    def data_types_to_db_bulk(data_types: Iterable[DataType], ontology_model: models.OntologyModel) -> list[models.DataType]:

        def get_data_type_source(data_type: DataType) -> dict:
            if data_type.derived_from and not data_type.derived_from.fulfilled:
                raise CreateModelException(
                    _("derivation_reference_not_fulfilled{alias}{entity}{name}").format(
                        alias=data_type.derived_from.alias, 
                        entity=data_type.__class__.__name__, 
                        name=data_type.name
                    ))
            return {
                'id': data_type._uuid,
                'ontology_model_id': ontology_model.id,
                'name': data_type.name,
                'description': data_type.description,
                'derived_from_id': data_type.derived_from.value._uuid if data_type.derived_from else None,
                'label': data_type.label,
                'object_schema': data_type.object_schema_resolved or data_type.object_schema,
            }

        source = [
            get_data_type_source(data_type) 
            for data_type in data_types
        ]
        result = models.DataType.objects.bulk_create(
            models.DataType(**data_type) for data_type in source
        )

        try:
            connection.check_constraints()
        except IntegrityError as e:
            raise CreateModelException(str(e))

        constraints = []
        for data_type in data_types:
            if data_type.constraints:
                constraints.extend(data_type.constraints)

        OntologyModelService.constraints_to_db_bulk(constraints)

        return result
    
    @staticmethod
    @atomic
    def constraints_to_db_bulk(constraints: Iterable[ConstraintDefinition]) -> list[models.ConstraintDefinition]:
        
        def get_constraint_source(constraint: ConstraintDefinition) -> dict:
            if not constraint.has_owner or not isinstance(constraint.owner, DataType):
                raise CreateModelException(_("owner_wrong_type{entity}{name}{expected}").format(
                    entity=constraint.__class__.__name__, 
                    name=constraint.name,
                    expected=DataType.__name__,
                ))
            
            return {
                'id': constraint._uuid,
                'data_type_id': constraint.owner._uuid,
                'name': constraint.name,
                'data': {constraint.name: constraint.args},
            }
        
        source = [
            get_constraint_source(constraint) 
            for constraint in constraints
        ]
        result = models.ConstraintDefinition.objects.bulk_create(
            models.ConstraintDefinition(**constraint) for constraint in source
        )

        try:
            connection.check_constraints()
        except IntegrityError as e:
            raise CreateModelException(str(e))

        return result
    
    @staticmethod
    @atomic
    def vertex_types_to_db_bulk(
        vertex_types: Iterable[VertexType], 
        ontology_model: models.OntologyModel, 
        default_content_getter: Callable[[str], bytes | None]
    ) -> list[models.VertexType]:
        def get_vertex_type_source(vertex_type: VertexType) -> dict:
            if vertex_type.derived_from and not vertex_type.derived_from.fulfilled:
                raise CreateModelException(_("derivation_reference_not_fulfilled{alias}{entity}{name}").format(
                    alias=vertex_type.derived_from.alias, 
                    entity=vertex_type.__class__.__name__, 
                    name=vertex_type.name
                ))
            return {
                'id': vertex_type._uuid,
                'ontology_model_id': ontology_model.id,
                'name': vertex_type.name,
                'description': vertex_type.description,
                'label': vertex_type.label,
                'derived_from_id': vertex_type.derived_from.value._uuid if vertex_type.derived_from else None,
                'metadata': vertex_type.metadata,
            }
        
        source = [
            get_vertex_type_source(vertex_type) 
            for vertex_type in vertex_types
        ]
        result = models.VertexType.objects.bulk_create(
            models.VertexType(**vertex_type) for vertex_type in source
        )

        try:
            connection.check_constraints()
        except IntegrityError as e:
            raise CreateModelException(str(e))
        
        properties = []
        artifacts = []
        for vertex_type in vertex_types:
            if vertex_type.properties:
                properties.extend(vertex_type.properties.values())
            if vertex_type.artifacts:
                artifacts.extend(vertex_type.artifacts.values())
        
        OntologyModelService.vertex_type_properties_to_db_bulk(properties)
        OntologyModelService.vertex_type_artifacts_to_db_bulk(artifacts, default_content_getter=default_content_getter)
        
        return result
    
    @staticmethod
    @atomic
    def vertex_type_properties_to_db_bulk(properties: Iterable[PropertyDefinition]) -> list[models.VertexTypePropertyDefinition]:
        def get_property_source(property: PropertyDefinition) -> dict:
            if not property.has_owner or not isinstance(property.owner, VertexType):
                raise CreateModelException(_("owner_wrong_type{entity}{name}{expected}").format(
                    entity=property.__class__.__name__, 
                    name=property.name,
                    expected=VertexType.__name__
                ))
            
            if not property.type.fulfilled:
                raise CreateModelException(_("type_reference_not_fulfilled{alias}{entity}{name}").format(
                    alias=property.type.alias, 
                    entity=property.__class__.__name__, 
                    name=property.name,
                ))
            
            return {
                'id': property._uuid,
                'vertex_type_id': property.owner._uuid,
                'type_id': property.type.value._uuid,
                'name': property.name,
                'description': property.description,
                'label': property.label,
                'required': property.required,
                'default': property.default,
                'allows_multiple': property.allows_multiple,
                'min_assignments': property.min_assignments,
                'max_assignments': property.max_assignments,
            }
        
        source = [
            get_property_source(property) 
            for property in properties
        ]
        result = models.VertexTypePropertyDefinition.objects.bulk_create(
            models.VertexTypePropertyDefinition(**property) for property in source
        )

        try:
            connection.check_constraints()
        except IntegrityError as e:
            raise CreateModelException(str(e))

        return result
    
    @staticmethod
    @atomic
    def vertex_type_artifacts_to_db_bulk(
        artifacts: Iterable[ArtifactDefinition], 
        default_content_getter: Callable[[str], bytes | None]
    ) -> list[models.VertexTypeArtifactDefinition]:
        
        def get_artifact_source(artifact: ArtifactDefinition) -> dict:
            if not artifact.has_owner or not isinstance(artifact.owner, VertexType):
                raise CreateModelException(_("owner_wrong_type{entity}{name}{expected}").format(
                    entity=artifact.__class__.__name__, 
                    name=artifact.name,
                    expected=VertexType.__name__
                ))
            
            return {
                'id': artifact._uuid,
                'vertex_type_id': artifact.owner._uuid,
                'name': artifact.name,
                'description': artifact.description,
                'label': artifact.label,
                'required': artifact.required,
                'default_path': artifact.default_path,
                'default_content': default_content_getter(artifact.default_path) if artifact.default_path else None,
                'mime_type': artifact.mime_type,
                'allows_multiple': artifact.allows_multiple,
                'min_assignments': artifact.min_assignments,
                'max_assignments': artifact.max_assignments,
            }
        
        source = [
            get_artifact_source(artifact) 
            for artifact in artifacts
        ]
        result = models.VertexTypeArtifactDefinition.objects.bulk_create(
            models.VertexTypeArtifactDefinition(**artifact) for artifact in source
        )

        try:
            connection.check_constraints()
        except IntegrityError as e:
            raise CreateModelException(str(e))

        return result
    
    @staticmethod
    @atomic
    def relationship_types_to_db_bulk(
        relationship_types: Iterable[RelationshipType], 
        ontology_model: models.OntologyModel,
        default_content_getter: Callable[[str], bytes | None]
    ) -> list[models.RelationshipType]:
        
        def get_relationship_type_source(relationship_type: RelationshipType) -> dict:
            if relationship_type.derived_from and not relationship_type.derived_from.fulfilled:
                raise CreateModelException(_("derivation_reference_not_fulfilled{alias}{entity}{name}").format(
                    alias=relationship_type.derived_from.alias, 
                    entity=relationship_type.__class__.__name__, 
                    name=relationship_type.name
                ))
    
            return {
                'id': relationship_type._uuid,
                'ontology_model_id': ontology_model.id,
                'name': relationship_type.name,
                'description': relationship_type.description,
                'label': relationship_type.label,
                'derived_from_id': relationship_type.derived_from.value._uuid if relationship_type.derived_from else None,
                'metadata': relationship_type.metadata,
            }
        
        source = [
            get_relationship_type_source(relationship_type) 
            for relationship_type in relationship_types
        ]
        result = models.RelationshipType.objects.bulk_create(
            models.RelationshipType(**relationship_type) for relationship_type in source
        )

        valid_source_types = []
        for relationship_type in relationship_types:
            valid_source_types.extend(relationship_type.valid_source_types or [])
        valid_target_types = []
        for relationship_type in relationship_types:
            valid_target_types.extend(relationship_type.valid_target_types or [])
        
        OntologyModelService.valid_source_types_to_db_bulk(valid_source_types)
        OntologyModelService.valid_target_types_to_db_bulk(valid_target_types)
        
        properties = []
        artifacts = []
        for relationship_type in relationship_types:
            if relationship_type.properties:
                properties.extend(relationship_type.properties.values())
            if relationship_type.artifacts:
                artifacts.extend(relationship_type.artifacts.values())

        OntologyModelService.relationship_type_properties_to_db_bulk(properties)
        OntologyModelService.relationship_type_artifacts_to_db_bulk(artifacts, default_content_getter=default_content_getter)
        
        try:
            connection.check_constraints()
        except IntegrityError as e:
            raise CreateModelException(str(e))

        return result
    
    @staticmethod
    @atomic
    def valid_source_types_to_db_bulk(valid_source_types: Iterable[OntologyReference[VertexType]]) -> list[models.models.Model]:
        ValidSourceType: models.models.Model = models.RelationshipType.valid_source_types.through
        
        def get_valid_source_type_source(valid_source_type: OntologyReference[VertexType]) -> dict:
            if not valid_source_type.has_owner or not isinstance(valid_source_type.owner, RelationshipType):
                raise CreateModelException(_("owner_wrong_type{entity}{name}{expected}").format(
                    entity=valid_source_type.__class__.__name__, 
                    name=f'valid_source_types[{valid_source_type.alias}]',
                    expected=RelationshipType.__name__
                ))
            
            if not valid_source_type.fulfilled:
                raise CreateModelException(_("reference_not_fulfilled{alias}{owner}{owner_name}").format(
                    alias=valid_source_type.alias, 
                    owner=valid_source_type.owner.__class__.__name__, 
                    owner_name=valid_source_type.owner.name
                ))

            return {
                'relationshiptype_id': valid_source_type.owner._uuid,
                'vertextype_id': valid_source_type.value._uuid,
            }
        
        source = [
            get_valid_source_type_source(valid_source_type) 
            for valid_source_type in valid_source_types
        ]
        result = ValidSourceType.objects.bulk_create(
            ValidSourceType(**valid_source_type) for valid_source_type in source
        )

        try:
            connection.check_constraints()
        except IntegrityError as e:
            raise CreateModelException(str(e))

        return result
    
    @staticmethod
    @atomic
    def valid_target_types_to_db_bulk(valid_target_types: Iterable[OntologyReference[VertexType]]) -> list[models.models.Model]:
        ValidTargetType: models.models.Model = models.RelationshipType.valid_target_types.through
        
        def get_valid_target_type_source(valid_target_type: OntologyReference[VertexType]) -> dict:
            if not valid_target_type.has_owner or not isinstance(valid_target_type.owner, RelationshipType):
                raise CreateModelException(_("owner_wrong_type{entity}{name}{expected}").format(
                    entity=valid_target_type.__class__.__name__, 
                    name=f'valid_target_types[{valid_target_type.alias}]',
                    expected=RelationshipType.__name__
                ))

            if not valid_target_type.fulfilled:
                raise CreateModelException(_("reference_not_fulfilled{alias}{owner}{owner_name}").format(
                    alias=valid_target_type.alias, 
                    owner=valid_target_type.owner.__class__.__name__, 
                    owner_name=valid_target_type.owner.name
                ))                
            
            return {
                'relationshiptype_id': valid_target_type.owner._uuid,
                'vertextype_id': valid_target_type.value._uuid,
            }
        
        source = [
            get_valid_target_type_source(valid_target_type) 
            for valid_target_type in valid_target_types
        ]
        result = ValidTargetType.objects.bulk_create(
            ValidTargetType(**valid_target_type) for valid_target_type in source
        )

        try:
            connection.check_constraints()
        except IntegrityError as e:
            raise CreateModelException(str(e))

        return result
    
    @staticmethod
    @atomic
    def relationship_type_properties_to_db_bulk(properties: Iterable[PropertyDefinition]) -> list[models.RelationshipTypePropertyDefinition]:
        def get_property_source(property: PropertyDefinition) -> dict:
            if not property.has_owner or not isinstance(property.owner, RelationshipType):
                raise CreateModelException(_("owner_wrong_type{entity}{name}{expected}").format(
                    entity=property.__class__.__name__, 
                    name=property.name,
                    expected=RelationshipType.__name__
                ))
            
            if not property.type.fulfilled:
                raise CreateModelException(_("type_not_fulfilled{alias}{entity}{name}").format(
                    alias=property.type.alias, 
                    entity=property.__class__.__name__, 
                    name=property.name
                ))
            
            return {
                'id': property._uuid,
                'relationship_type_id': property.owner._uuid,
                'type_id': property.type.value._uuid,
                'name': property.name,
                'description': property.description,
                'label': property.label,
                'required': property.required,
                'default': property.default,
                'allows_multiple': property.allows_multiple,
                'min_assignments': property.min_assignments,
                'max_assignments': property.max_assignments,
            }
        
        source = [
            get_property_source(property) 
            for property in properties
        ]
        result = models.RelationshipTypePropertyDefinition.objects.bulk_create(
            models.RelationshipTypePropertyDefinition(**property) for property in source
        )

        try:
            connection.check_constraints()
        except IntegrityError as e:
            raise CreateModelException(str(e))

        return result
    
    @staticmethod
    @atomic
    def relationship_type_artifacts_to_db_bulk(
        artifacts: Iterable[ArtifactDefinition], 
        default_content_getter: Callable[[str], bytes | None]
    ) -> list[models.RelationshipTypeArtifactDefinition]:
        
        def get_artifact_source(artifact: ArtifactDefinition) -> dict:
            if not artifact.has_owner or not isinstance(artifact.owner, RelationshipType):
                raise CreateModelException(_("owner_wrong_type{entity}{name}{expected}").format(
                    entity=artifact.__class__.__name__, 
                    name=artifact.name,
                    expected=RelationshipType.__name__
                ))
            
            return {
                'id': artifact._uuid,
                'relationship_type_id': artifact.owner._uuid,
                'name': artifact.name,
                'description': artifact.description,
                'label': artifact.label,
                'required': artifact.required,
                'default_path': artifact.default_path,
                'mime_type': artifact.mime_type,
                'allows_multiple': artifact.allows_multiple,
                'min_assignments': artifact.min_assignments,
                'max_assignments': artifact.max_assignments,
                'default_content': default_content_getter(artifact.default_path) if artifact.default_path else None,
            }
        
        source = [
            get_artifact_source(artifact) 
            for artifact in artifacts
        ]
        result = models.RelationshipTypeArtifactDefinition.objects.bulk_create(
            models.RelationshipTypeArtifactDefinition(**artifact) for artifact in source
        )

        try:
            connection.check_constraints()
        except IntegrityError as e:
            raise CreateModelException(str(e))

        return result

    @staticmethod
    @atomic
    def ontology_model_to_db(ontology_model: OntologyModel) -> models.OntologyModel:
        result = models.OntologyModel.objects.create(
            name=ontology_model.name,
            description=ontology_model.description,
            label=ontology_model.label,
        )

        for resolved in ontology_model._resolved_imports:
            imported_module = resolved[2]
            try:
                imported: models.OntologyModel = imported_module._meta["ontology_model"]
            except KeyError:
                raise CreateModelException(_("recursive_module_load_unsupported{name}").format(name=imported_module.orig_name))
            
            if not isinstance(imported, models.OntologyModel):
                raise CreateModelException(_("unexpected_import_type{name}").format(name=imported_module.orig_name))

            result.imports.add(imported)

        default_content_getter = OntologyModelService.get_default_content_getter(ontology_model)

        OntologyModelService.data_types_to_db_bulk(ontology_model.data_types.values(), result)
        OntologyModelService.vertex_types_to_db_bulk(ontology_model.vertex_types.values(), result, default_content_getter)
        OntologyModelService.relationship_types_to_db_bulk(ontology_model.relationship_types.values(), result, default_content_getter)
        
        try:
            connection.check_constraints()
        except IntegrityError as e:
            raise CreateModelException(str(e))
        
        return result
    
    @staticmethod
    def get_default_content_getter(ontology_model: OntologyModel) -> Callable[[str], bytes | None]:
        def default_content_getter(path: str) -> bytes | None:
            if not isinstance(ontology_model.owner, ModelModule):
                raise CreateModelException(_("owner_wrong_type{entity}{name}{expected}").format(
                    entity=ontology_model.owner.__class__.__name__, 
                    name=ontology_model.owner, 
                    expected=ModelModule.__name__
                ))
            
            data = ontology_model.owner.artifacts.get(path).read()

            if isinstance(data, str):
                data = data.encode('utf-8')

            if not isinstance(data, bytes):
                raise CreateModelException(_("artifact_not_binary{path}").format(
                    path=path
                ))
            return data
        
        return default_content_getter
