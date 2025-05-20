from django.core.management.base import BaseCommand
from at_ontology.apps.ontology_model.models import VertexType
from at_ontology.apps.ontology_model.models import OntologyModel
from at_ontology.apps.ontology.models import Ontology
from at_ontology.apps.ontology.models import Vertex
import sqlite3

class Command(BaseCommand):
    help = "Перенос компетенций"
    def handle(self, *args, **options):
        ontology_model = OntologyModel.objects.get(name="Прикладная онтология курса/дисциплины")
        ontology = Ontology.objects.get(name="Введение в интеллектуальные системы")
        competence_type = self.create_vertex_type(
            name="Компетенция",
            ontology_model=ontology_model
        )

        conn = sqlite3.connect('development.sqlite3')
        cursor = conn.cursor()

        cursor.execute("""
                SELECT code, description
                FROM competences;
                """)

        rows = cursor.fetchall()

        conn.close()

        for code, description in rows:
            Vertex.objects.get_or_create(
                name=code,
                type=competence_type,
                description=description,
                ontology=ontology
            )

        self.stdout.write(self.style.SUCCESS(f'Перенесено {len(rows)} компетенций'))


    def create_vertex_type(self, name: str, ontology_model: OntologyModel, derived_from: VertexType = None) -> VertexType:
        vt, created = VertexType.objects.get_or_create(
            name=name,
            ontology_model=ontology_model,
            derived_from=derived_from
        )
        if created:
            self.stdout.write(self.style.SUCCESS(
                f"Created VertexType: {vt.name} (id={vt.id})"
            ))
        else:
            self.stdout.write(
                f"VertexType already exists: {vt.name} (id={vt.id})"
            )

        return vt