import io
from pathlib import Path
from at_ontology_parser.parsing.parser import ImportLoader, ModelModule, OntologyModule, ImportDefinition, Context, ImportException
from at_ontology.apps.ontology_model.models import ArtifactDefinition, OntologyModel
from at_ontology.apps.ontology_model.service import OntologyModelService
from django.utils.translation import gettext_lazy as _


class DBLoader(ImportLoader):

    def resolve_import(self, source_module: ModelModule | OntologyModule, import_def: ImportDefinition, context: Context):
        if isinstance(source_module, ModelModule):
            orig_module = source_module.parser.get_module_by_orig_name(import_def.file)
            if orig_module:
                return orig_module
        
        import_path = import_def.file
        
        if not import_path.startswith("<") and not import_path.endswith(">"):
            raise ImportException(
                _("unsupported_import_definition{import_path}").format(import_path),
                context=context
            )

        model_name = import_path[1:-1]

        ontology_model = OntologyModel.objects.filter(name=model_name).first()
        if not ontology_model:
            raise ImportException(
                _("ontology_model_not_exists{model_name}").format(model_name),
                context=context
            )
        
        ontology_model_source = OntologyModelService.ontology_model_source_from_db(ontology_model)
        model = source_module.parser.load_ontology_model_data(ontology_model_source, orig_name=import_path, full_path=model_name, context=context.create_child(import_path))

        module = source_module.parser.get_module_by_model(model)
        module._meta['ontology_model'] = ontology_model
        self.load_artifacts(module)
        model._built = True
        module._built = True

        return module
    
    def load_artifacts(self, module: ModelModule):
        ontology_model = module._meta.get('ontology_model')

        if not ontology_model:

            name = str(module.full_path)

            if name.startswith("<") and name.endswith(">"):
                name = name[1:-1]

            ontology_model = OntologyModel.objects.filter(name=name).first()

            if not ontology_model:
                raise ImportException(
                    _("ontology_model_not_exists{model_name}").format(model_name=name),
                    context=module.context
                )

        for vertex_type in ontology_model.vertex_types.all():
            for artifect_def in vertex_type.artifacts.all():
                artifect_def: ArtifactDefinition

                if artifect_def.default_path and artifect_def.default_content:
                    module.artifacts[Path(artifect_def.default_path)] = io.BytesIO(artifect_def.default_content)
        
        for relationship_type in ontology_model.relationship_types.all():
            for artifect_def in relationship_type.artifacts.all():
                artifect_def: ArtifactDefinition

                if artifect_def.default_path and artifect_def.default_content:
                    module.artifacts[Path(artifect_def.default_path)] = io.BytesIO(artifect_def.default_content)

        

