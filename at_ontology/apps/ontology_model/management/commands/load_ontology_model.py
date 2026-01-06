import logging

from at_ontology_parser.parsing.parser import Parser
from django.core.management import BaseCommand

from at_ontology.apps.ontology_model.import_loader import DBLoader
from at_ontology.apps.ontology_model.service import OntologyModelService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--file", type=str, help="File to import")

        return super().add_arguments(parser)

    def handle(self, *args, **options):
        file = options["file"]

        parser = Parser()
        parser.import_loaders.append(DBLoader())

        ontology_model = parser.load_model_yaml_file(file)
        parser.finalize_references()
        ontology_model = OntologyModelService.ontology_model_to_db(ontology_model)

        logger.info("Loaded ontology model: %s", ontology_model)
