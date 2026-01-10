from pathlib import Path

from at_ontology_parser.parsing.parser import Parser
from django.test import TestCase

from at_ontology.apps.ontology_model.import_loader import DBLoader
from at_ontology.apps.ontology_model.service import OntologyModelService

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"

# at_ontology.apps.ontology_model.tests.test_service.OntologyModelServiceTest
class OntologyModelServiceTest(TestCase):
    def setUp(self):
        pass

    def test_load_and_save_model(self):
        mdl_path = FIXTURES_DIR / "normative-types" / "types.mdl.yaml"

        parser = Parser()
        parser.import_loaders.append(DBLoader())

        ontology_model = parser.load_model_yaml_file(mdl_path)
        parser.finalize_references()

        db_model = OntologyModelService.ontology_model_to_db(ontology_model)

        source = OntologyModelService.ontology_model_source_from_db(db_model)

        print(source)

        parser = Parser()
        parser.import_loaders.append(DBLoader())
        new_mdl = parser.load_ontology_model_data(source, mdl_path.name, mdl_path.name)
        parser.finalize_references()
        print(new_mdl)

        parser = Parser()
        parser.import_loaders.append(DBLoader())

        applied_mdl_path = FIXTURES_DIR / "applied-types" / "types.mdl.yaml"

        applied_mdl = parser.load_model_yaml_file(applied_mdl_path)
        parser.finalize_references()

        print(applied_mdl)

        db_applied_model = OntologyModelService.ontology_model_to_db(applied_mdl)

        print(db_applied_model)
