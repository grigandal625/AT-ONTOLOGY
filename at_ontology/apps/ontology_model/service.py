from io import BytesIO
from io import IOBase
from pathlib import Path
from typing import Iterable
from typing import Optional
from typing import TYPE_CHECKING
from typing import Union

from at_ontology_parser.model.definitions import ArtifactDefinition
from at_ontology_parser.model.definitions import ConstraintDefinition
from at_ontology_parser.model.definitions import PropertyDefinition
from at_ontology_parser.model.handler import OntologyModel
from at_ontology_parser.model.types import DataType
from at_ontology_parser.model.types import RelationshipType
from at_ontology_parser.model.types import VertexType
from at_ontology_parser.parsing.parser import ModelModule
from at_ontology_parser.parsing.parser import Parser
from at_ontology_parser.reference import OntologyReference
from django.core import exceptions
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
    def data_type_source_from_db(data_type: models.DataType) -> dict:
        return {
            "description": data_type.description,
            "derived_from": data_type.derived_from.name if data_type.derived_from else None,
            "label": data_type.label,
            "constraints": [constraint.data for constraint in data_type.constraints.all()]
            if data_type.constraints.all().exists()
            else None,
            "object_schema": data_type.object_schema,
        }

    @staticmethod
    def data_types_source_from_db(data_types: Iterable[models.DataType]) -> dict:
        return {data_type.name: OntologyModelService.data_type_source_from_db(data_type) for data_type in data_types}

    @staticmethod
    def vertex_type_source_from_db(vertex_type: models.VertexType) -> dict:
        return {
            "description": vertex_type.description,
            "label": vertex_type.label,
            "derived_from": vertex_type.derived_from.name if vertex_type.derived_from else None,
            "metadata": vertex_type.metadata,
            "properties": OntologyModelService.properties_source_from_db(vertex_type.properties.all()),
            "artifacts": OntologyModelService.artifacts_source_from_db(vertex_type.artifacts.all()),
        }

    @staticmethod
    def vertex_types_source_from_db(vertex_types: Iterable[models.VertexType]) -> dict:
        return {
            vertex_type.name: OntologyModelService.vertex_type_source_from_db(vertex_type)
            for vertex_type in vertex_types
        }

    @staticmethod
    def artifact_definition_source_from_db(
        artifact: models.VertexTypeArtifactDefinition | models.RelationshipTypeArtifactDefinition,
    ) -> dict:
        return {
            "description": artifact.description,
            "label": artifact.label,
            "required": artifact.required,
            "default_path": artifact.default_path,
            "mime_type": artifact.mime_type,
            "allows_multiple": artifact.allows_multiple,
            "min_assignments": artifact.min_assignments,
            "max_assignments": artifact.max_assignments,
        }

    @staticmethod
    def artifacts_source_from_db(artifacts: Iterable[models.ArtifactDefinition]) -> dict:
        return {
            artifact.name: OntologyModelService.artifact_definition_source_from_db(artifact) for artifact in artifacts
        }

    @staticmethod
    def property_definition_source_from_db(
        property: models.VertexTypePropertyDefinition | models.RelationshipTypePropertyDefinition,
    ) -> dict:
        return {
            "description": property.description,
            "type": property.type.name,
            "label": property.label,
            "required": property.required,
            "default": property.default,
            "allows_multiple": property.allows_multiple,
            "min_assignments": property.min_assignments,
            "max_assignments": property.max_assignments,
        }

    @staticmethod
    def properties_source_from_db(properties: Iterable[models.PropertyDefinition]) -> dict:
        return {
            property.name: OntologyModelService.property_definition_source_from_db(property) for property in properties
        }

    @staticmethod
    def relationship_type_source_from_db(relationship_type: models.RelationshipType) -> dict:
        return {
            "description": relationship_type.description,
            "label": relationship_type.label,
            "metadata": relationship_type.metadata,
            "derived_from": relationship_type.derived_from.name if relationship_type.derived_from else None,
            "valid_source_vertex_types": [t.name for t in relationship_type.valid_source_types.all()],
            "valid_target_vertex_types": [t.name for t in relationship_type.valid_target_types.all()],
            "properties": OntologyModelService.properties_source_from_db(relationship_type.properties.all()),
            "artifacts": OntologyModelService.artifacts_source_from_db(relationship_type.artifacts.all()),
        }

    @staticmethod
    def relationship_types_source_from_db(relationship_types: Iterable[models.RelationshipType]) -> dict:
        return {
            relationship_type.name: OntologyModelService.relationship_type_source_from_db(relationship_type)
            for relationship_type in relationship_types
        }

    @staticmethod
    def ontology_model_source_from_db(ontology_model: models.OntologyModel) -> dict:
        return {
            "name": ontology_model.name,
            "description": ontology_model.description,
            "label": ontology_model.label,
            "imports": [f"<{imported.name}>" for imported in ontology_model.imports.all()],
            "data_types": OntologyModelService.data_types_source_from_db(ontology_model.data_types.all()),
            "vertex_types": OntologyModelService.vertex_types_source_from_db(ontology_model.vertex_types.all()),
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
    def data_type_to_db(data_type: DataType, ontology_model: models.OntologyModel) -> models.DataType:
        try:
            derived_from = OntologyModelService.get_derived_from_data_type(data_type.derived_from, ontology_model)
        except exceptions.ObjectDoesNotExist:
            raise CreateModelException(_("data_type_not_exists{name}").format(name=data_type.derived_from.alias))
        except exceptions.MultipleObjectsReturned:
            raise BrokenModelException(_("data_type_multiple{name}").format(name=data_type.derived_from.alias))

        result = models.DataType.objects.create(
            ontology_model=ontology_model,
            derived_from=derived_from,
            name=data_type.name,
            label=data_type.label,
            description=data_type.description,
            object_schema=data_type.object_schema_resolved,
        )

        for constraint in data_type.constraints:
            with atomic():
                OntologyModelService.constraint_to_db(constraint, result)

        return result

    @staticmethod
    def get_derived_from_data_type(
        derived_from: Optional[OntologyReference[DataType]], ontology_model: models.OntologyModel
    ) -> Optional[models.DataType]:
        if derived_from:
            return models.DataType.objects.get(
                ontology_model__in=OntologyModelService.get_importing_models_queryset_deep(
                    ontology_model=ontology_model
                ),
                name=derived_from.alias,
            )
        else:
            return None

    @staticmethod
    @atomic
    def constraint_to_db(constraint: ConstraintDefinition, data_type: models.DataType) -> models.ConstraintDefinition:
        result = models.ConstraintDefinition.objects.create(
            data_type=data_type,
            name=constraint.name,
            data={constraint.name: constraint.args},
        )

        return result

    @staticmethod
    @atomic
    def vertex_type_to_db(vertex_type: VertexType, ontology_model: models.OntologyModel) -> models.VertexType:
        try:
            derived_from = OntologyModelService.get_derived_from_vertex(vertex_type.derived_from, ontology_model)
        except exceptions.ObjectDoesNotExist:
            raise CreateModelException(_("vertex_type_not_exists{name}").format(name=vertex_type.derived_from.alias))
        except exceptions.MultipleObjectsReturned:
            raise BrokenModelException(_("vertex_type_multiple{name}").format(name=vertex_type.derived_from.alias))

        result = models.VertexType.objects.create(
            ontology_model=ontology_model,
            name=vertex_type.name,
            label=vertex_type.label,
            description=vertex_type.description,
            derived_from=derived_from,
            metadata=vertex_type.metadata,
        )

        for property in vertex_type.properties:
            with atomic():
                OntologyModelService.vertex_type_property_definition_to_db(property, result)

        for artifact in vertex_type.artifacts:
            with atomic():
                OntologyModelService.vertex_type_artifact_definition_to_db(artifact, result)

        return result

    @staticmethod
    def get_importing_models_queryset_deep(
        ontology_model: models.OntologyModel, watched: QuerySet[models.OntologyModel] = None
    ) -> QuerySet[models.OntologyModel]:
        watched = watched or models.OntologyModel.objects.none()

        current = models.OntologyModel.objects.filter(pk=ontology_model.pk)
        queryset = ontology_model.imports.all().exclude(pk__in=watched.values_list("pk", flat=True)) | current

        new_watched = watched | current

        for model in queryset.exclude(pk__in=new_watched.values_list("pk", flat=True)):
            queryset = queryset | OntologyModelService.get_importing_models_queryset_deep(model, watched=new_watched)
            queryset = queryset.distinct()

        return queryset

    @staticmethod
    def get_derived_from_vertex(
        derived_from: Optional[OntologyReference[VertexType]], ontology_model: models.OntologyModel
    ) -> Optional[models.VertexType]:
        if derived_from:
            return models.VertexType.objects.get(
                ontology_model__in=OntologyModelService.get_importing_models_queryset_deep(
                    ontology_model=ontology_model
                ),
                name=derived_from.alias,
            )
        else:
            return None

    @staticmethod
    @atomic
    def vertex_type_property_definition_to_db(
        property: PropertyDefinition, vertex_type: VertexType, ontology_model: models.OntologyModel
    ) -> models.VertexTypePropertyDefinition:
        result = models.VertexTypePropertyDefinition.objects.create(
            vertex_type=vertex_type,
            type=OntologyModelService.get_data_type(property.type, ontology_model),
            name=property.name,
            label=property.label,
            description=property.description,
            required=property.required,
            default=property.default,
            allows_multiple=property.allows_multiple,
            min_assignments=property.min_assignments,
            max_assignments=property.max_assignments,
        )

        return result

    @staticmethod
    @atomic
    def vertex_type_artifact_definition_to_db(
        artifact: ArtifactDefinition, vertex_type: VertexType, ontology_model: models.OntologyModel
    ) -> models.VertexTypeArtifactDefinition:
        result = models.VertexTypeArtifactDefinition.objects.create(
            vertex_type=vertex_type,
            name=artifact.name,
            label=artifact.label,
            description=artifact.description,
            required=artifact.required,
            default_path=artifact.default_path,
            mime_type=artifact.mime_type,
            allows_multiple=artifact.allows_multiple,
            min_assignments=artifact.min_assignments,
            max_assignments=artifact.max_assignments,
        )

        return result

    @staticmethod
    def get_data_type(ref: OntologyReference[DataType], ontology_model: models.OntologyModel) -> models.DataType:
        return models.DataType.objects.get(
            ontology_model__in=OntologyModelService.get_importing_models_queryset_deep(ontology_model=ontology_model),
            name=ref.alias,
        )

    @staticmethod
    @atomic
    def relationship_type_to_db(
        relationship_type: RelationshipType, ontology_model: models.OntologyModel
    ) -> models.RelationshipType:
        try:
            derived_from = OntologyModelService.get_derived_from_relationship_type(
                relationship_type.derived_from, ontology_model
            )
        except exceptions.ObjectDoesNotExist:
            raise CreateModelException(
                _("relationship_type_not_exists{name}").format(name=relationship_type.derived_from.alias)
            )
        except exceptions.MultipleObjectsReturned:
            raise BrokenModelException(
                _("relationship_type_multiple{name}").format(name=relationship_type.derived_from.alias)
            )

        result = models.RelationshipType.objects.create(
            ontology_model=ontology_model,
            name=relationship_type.name,
            label=relationship_type.label,
            description=relationship_type.description,
            metadata=relationship_type.metadata,
            derived_from=derived_from,
        )

        for property in relationship_type.properties.values():
            with atomic():
                OntologyModelService.relationship_type_property_definition_to_db(property, result)

        for artifact in relationship_type.artifacts.values():
            with atomic():
                OntologyModelService.relationship_type_artifact_definition_to_db(artifact, result)

        if relationship_type.valid_source_types:
            result.valid_source_types.add(
                OntologyModelService.get_vertex_types_queryset(
                    names=[ref.alias for ref in relationship_type.valid_source_types], ontology_model=ontology_model
                )
            )

        if relationship_type.valid_target_types:
            result.valid_target_types.add(
                OntologyModelService.get_vertex_types_queryset(
                    names=[ref.alias for ref in relationship_type.valid_target_types], ontology_model=ontology_model
                )
            )

        return result

    @staticmethod
    def get_derived_from_relationship_type(
        derived_from: Optional[OntologyReference[RelationshipType]], ontology_model: models.OntologyModel
    ) -> Optional[models.RelationshipType]:
        if derived_from:
            return models.RelationshipType.objects.get(
                ontology_model__in=OntologyModelService.get_importing_models_queryset_deep(
                    ontology_model=ontology_model
                ),
                name=derived_from.alias,
            )
        else:
            return None

    @staticmethod
    def relationship_type_property_definition_to_db(
        property: PropertyDefinition, relationship_type: RelationshipType
    ) -> models.RelationshipTypePropertyDefinition:
        result = models.RelationshipTypePropertyDefinition.objects.create(
            relationship_type=relationship_type,
            type=OntologyModelService.get_data_type(property.type, ontology_model=relationship_type.ontology_model),
            name=property.name,
            label=property.label,
            description=property.description,
            required=property.required,
            default=property.default,
            allows_multiple=property.allows_multiple,
            min_assignments=property.min_assignments,
            max_assignments=property.max_assignments,
        )

        return result

    @staticmethod
    def relationship_type_artifact_definition_to_db(
        artifact: ArtifactDefinition, relationship_type: RelationshipType
    ) -> models.RelationshipTypeArtifactDefinition:
        result = models.RelationshipTypeArtifactDefinition.objects.create(
            relationship_type=relationship_type,
            name=artifact.name,
            label=artifact.label,
            description=artifact.description,
            required=artifact.required,
            default_path=artifact.default_path,
            mime_type=artifact.mime_type,
            allows_multiple=artifact.allows_multiple,
            min_assignments=artifact.min_assignments,
            max_assignments=artifact.max_assignments,
        )

        return result

    @staticmethod
    def get_vertex_types_queryset(
        names: list[str], ontology_model: models.OntologyModel
    ) -> QuerySet[models.VertexType]:
        result = models.VertexType.objects.filter(
            ontology_model__in=OntologyModelService.get_importing_models_queryset_deep(ontology_model=ontology_model),
            name__in=names,
        )

        for name in names:
            if name not in result.values_list("name", flat=True):
                raise BrokenModelException(_("vertex_type_not_exists{name}").format(name=name))

        return result

    @staticmethod
    @atomic
    def ontology_model_to_db(ontology_model: OntologyModel) -> models.OntologyModel:
        result = models.OntologyModel.objects.create(
            name=ontology_model.name,
            label=ontology_model.label,
            description=ontology_model.description,
        )

        for imp in ontology_model.imports:
            try:
                imported = OntologyModelService.get_imported_model(imp)
            except exceptions.ObjectDoesNotExist:
                raise CreateModelException(_("ontology_model_not_exists{name}").format(name=imported.alias))
            except exceptions.MultipleObjectsReturned:
                raise BrokenModelException(_("ontology_model_multiple{name}").format(name=imported.alias))
            result.imports.add(imported)

        for data_type in ontology_model.data_types.values():
            with atomic():
                OntologyModelService.data_type_to_db(data_type, result)

        for vertex_type in ontology_model.vertex_types.values():
            with atomic():
                OntologyModelService.vertex_type_to_db(vertex_type, result)

        for relationship_type in ontology_model.relationship_types.values():
            with atomic():
                OntologyModelService.relationship_type_to_db(relationship_type, result)

        OntologyModelService.artifact_default_contents_to_db(ontology_model, result)

        return result

    @staticmethod
    @atomic
    def artifact_default_contents_to_db(ontology_model: OntologyModel, ontology_model_db: models.OntologyModel) -> None:
        module: ModelModule = ontology_model.owner

        if not module:
            raise CreateModelException(_("module_not_exists"))
        if not isinstance(module, ModelModule):
            raise CreateModelException(_("unexpected_module_type"))

        for vertex_type in ontology_model_db.vertex_types.all():
            for artifact_definition in vertex_type.artifacts.all():
                OntologyModelService.artifact_default_content_to_db(artifact_definition, module)

        for relationship_type in ontology_model_db.relationship_types.all():
            for artifact_definition in relationship_type.artifacts.all():
                OntologyModelService.artifact_default_content_to_db(artifact_definition, module)

    @staticmethod
    @atomic
    def artifact_default_content_to_db(
        artifact_definition: models.VertexTypeArtifactDefinition | models.RelationshipTypeArtifactDefinition,
        module: ModelModule,
    ) -> models.VertexTypeArtifactDefinition | models.RelationshipTypeArtifactDefinition:
        artifact = module.artifacts.get(artifact_definition.default_path)

        if not artifact:
            raise CreateModelException(_("artifact_not_exists{path}").format(path=artifact_definition.default_path))

        content = artifact.read()

        if isinstance(content, str):
            content = content.encode("utf-8")

        if not isinstance(content, bytes):
            raise CreateModelException(_("artifact_not_bytes{name}").format(name=artifact_definition.default_path))

        artifact_definition.default_content = content
        artifact_definition.save()

        return artifact_definition

    @staticmethod
    def get_imported_model(imported: OntologyReference[OntologyModel]) -> models.OntologyModel:
        return models.OntologyModel.objects.get(name=imported.alias)

    @staticmethod
    def get_vertex_type(
        vertex_type: OntologyReference[VertexType], source: Union[models.OntologyModel, "ontology_models.Ontology"]
    ) -> models.VertexType:
        if isinstance(source, models.OntologyModel):
            imported_models = OntologyModelService.get_importing_models_queryset_deep(source)
        else:
            imported_models = models.OntologyModel.objects.none()
            for model in source.imports.all():
                imported_models = imported_models | OntologyModelService.get_importing_models_queryset_deep(model)
                imported_models = imported_models.distinct()

        return models.VertexType.objects.get(ontology_model__in=imported_models, name=vertex_type.alias)

    @staticmethod
    def get_relationship_type(
        relationship_type: OntologyReference[RelationshipType],
        source: Union[models.OntologyModel, "ontology_models.Ontology"],
    ) -> models.RelationshipType:
        if isinstance(source, models.OntologyModel):
            imported_models = OntologyModelService.get_importing_models_queryset_deep(source)
        else:
            imported_models = models.OntologyModel.objects.none()
            for model in source.imports.all():
                imported_models = imported_models | OntologyModelService.get_importing_models_queryset_deep(model)
                imported_models = imported_models.distinct()

        return models.RelationshipType.objects.get(ontology_model__in=imported_models, name=relationship_type.alias)

    @staticmethod
    def get_vertex_artifact_definition(
        artifact: OntologyReference[ArtifactDefinition], source: Union[models.VertexType, "ontology_models.Vertex"]
    ) -> models.VertexTypeArtifactDefinition:
        vertex_type = source if isinstance(source, models.VertexType) else source.type
        return vertex_type.artifacts.get(name=artifact.alias)

    @staticmethod
    def get_relationship_artifact_definition(
        artifact: OntologyReference[ArtifactDefinition],
        source: Union[models.RelationshipType, "ontology_models.Relationship"],
    ) -> models.RelationshipTypeArtifactDefinition:
        relationship_type = source if isinstance(source, models.RelationshipType) else source.type
        return relationship_type.artifacts.get(name=artifact.alias)

    @staticmethod
    def get_vertex_property_definition(
        property: OntologyReference[PropertyDefinition], source: Union[models.VertexType, "ontology_models.Vertex"]
    ) -> models.VertexTypePropertyDefinition:
        vertex_type = source if isinstance(source, models.VertexType) else source.type
        return vertex_type.properties.get(name=property.alias)

    @staticmethod
    def get_relationship_property_definition(
        property: OntologyReference[PropertyDefinition],
        source: Union[models.RelationshipType, "ontology_models.Relationship"],
    ) -> models.RelationshipTypePropertyDefinition:
        relationship_type = source if isinstance(source, models.RelationshipType) else source.type
        return relationship_type.properties.get(name=property.alias)

    @staticmethod
    def ontology_model_archive_from_db(ontology_model: models.OntologyModel) -> Path:
        from at_ontology.apps.ontology_model.import_loader import DBLoader

        model_source = OntologyModelService.ontology_model_source_from_db(ontology_model)

        parser = Parser()
        parser.import_loaders.append(DBLoader())

        model = parser.load_ontology_model_data(model_source, f"<{ontology_model.name}", ontology_model.name)

        return parser.build_archive(model)
