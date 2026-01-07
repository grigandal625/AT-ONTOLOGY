from pathlib import Path
from django.test import TestCase
from at_ontology.apps.ontology.management.commands.load_from_legacy_db import Command as LoadLegacy
from at_ontology.apps.ontology_model.management.commands.load_ontology_model import Command as LoadOntologyModel

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"

# at_ontology.apps.ontology.tests.test_load_legacy
class LoadLegacyTest(TestCase):

    def setUp(self):

        LoadOntologyModel().handle(file=str(FIXTURES_DIR / 'normative-types/types.mdl.yaml'))
        LoadOntologyModel().handle(file=str(FIXTURES_DIR / 'applied-types/types.mdl.yaml'))

        return super().setUp()
    
    def test_load_legacy(self):
        LoadLegacy().handle(db=str(FIXTURES_DIR / 'legacy_db/development.sqlite3'))
