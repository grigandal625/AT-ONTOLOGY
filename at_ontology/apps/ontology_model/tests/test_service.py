from pathlib import Path
from django.test import TestCase
from at_ontology.apps.ontology_model.service import OntologyModelService
from at_ontology_parser.parsing.parser import Parser
from at_ontology.apps.ontology_model.import_loader import DBLoader

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


class OntologyModelServiceTest(TestCase):

    def setUp(self):
        pass

    def test_load_and_save_model(self):
        mdl_path = FIXTURES_DIR / "test_upload.mdl.yaml"

        parser = Parser()
        parser.import_loaders.append(DBLoader())

        ontology_model = parser.load_model_yaml_file(mdl_path)

        db_model = OntologyModelService.ontology_model_to_db(ontology_model)

        source = OntologyModelService.ontology_model_source_from_db(db_model)

        print(source)

        parser = Parser()
        parser.import_loaders.append(DBLoader())
        new_mdl = parser.load_ontology_model_data(source, mdl_path.name, mdl_path.name)

        print(new_mdl)