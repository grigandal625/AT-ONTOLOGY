from django.core.management.base import BaseCommand
from at_ontology.apps.ontology.models import Vertex
from at_ontology.apps.ontology.models import VertexArtifactAssignment
from at_ontology.apps.ontology.models import VertexPropertyAssignment
from at_ontology.apps.ontology.models import Relationship
from at_ontology.apps.ontology.models import RelationshipArtifactAssignment
from at_ontology.apps.ontology.models import RelationshipPropertyAssignment
from at_ontology.apps.ontology_model.models import VertexType

import sqlite3

class Command(BaseCommand):
    help = "Перенос тем/подтем"

    def handle(self, *args, **options):
        vt, created = VertexType.objects.get_or_create(
            name='Элемент курса/дисциплины'
        )
        if created:
            self.stdout.write(self.style.SUCCESS(
                f"Created VertexType: {vt.name} (id={vt.id})"
            ))
        else:
            self.stdout.write(
                f"VertexType already exists: {vt.name} (id={vt.id})"
            )
        conn = sqlite3.connect('C:/Users/petrm/PycharmProjects/AT_ONTOLOGY/development.sqlite3')
        cursor = conn.cursor()
        cursor.execute("SELECT text FROM ka_topics")

        rows = cursor.fetchall()

        for row in rows:
            Vertex.objects.create(name=row[0], type=vt)

        conn.close()

        self.stdout.write(self.style.SUCCESS(f'Перенесено {len(rows)} элементов.'))
