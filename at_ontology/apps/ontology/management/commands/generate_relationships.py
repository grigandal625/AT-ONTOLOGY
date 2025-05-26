from django.core.management.base import BaseCommand
from at_ontology.apps.ontology_model.models import VertexType
from at_ontology.apps.ontology_model.models import OntologyModel
from at_ontology.apps.ontology_model.models import RelationshipType
from at_ontology.apps.ontology_model.models import VertexTypePropertyDefinition
from at_ontology.apps.ontology.models import Ontology
from at_ontology.apps.ontology.models import Vertex
from at_ontology.apps.ontology.models import Relationship
from at_ontology.apps.ontology.models import VertexPropertyAssignment
import random
import sqlite3
import json
from pathlib import Path
class Command(BaseCommand):
    help = "Перенос ДИС из JSON"
    def handle(self, *args, **options):
        ontology = Ontology.objects.get(name="Введение в интеллектуальные системы")
        insyst = Vertex.objects.filter(ontology=ontology)
        ontology = Ontology.objects.get(name="Интеллектуальные диалоговые системы")
        ids = Vertex.objects.filter(ontology=ontology)
        ontology = Ontology.objects.get(name="Динамические интеллектуальные системы")
        dis = Vertex.objects.filter(ontology=ontology)

        ontology_model = OntologyModel.objects.get(name="Прикладная онтология курса/дисциплины")

        agregation, _ = RelationshipType.objects.get_or_create(
            name='Агрегация',
            ontology_model=ontology_model
        )

        asociation, _ = RelationshipType.objects.get_or_create(
            name='Асоциация',
            ontology_model=ontology_model
        )

        weak, _ = RelationshipType.objects.get_or_create(
            name='Слабая',
            ontology_model=ontology_model
        )

        self.generate_relationships(
            vertices=insyst,
            ontology=insyst[0].ontology,
            types=[weak, asociation, agregation]
        )

        self.generate_relationships(
            vertices=ids,
            ontology=ids[0].ontology,
            types=[weak, asociation, agregation]
        )
        self.generate_relationships(
            vertices=dis,
            ontology=dis[0].ontology,
            types=[weak, asociation, agregation]
        )


        self.stdout.write(self.style.SUCCESS(f"Столько вершин {len(ids)}"))

    def generate_relationships(self, vertices: list, ontology, types: list):
        for i in range(len(vertices)):
            rand_percent = random.sample(range(40, 80 + 1), 1)[0]

            number = int(len(range(i+1, len(vertices))) * rand_percent/100)

            rand_indexes = random.sample(range(i+1, len(vertices)), number)

            for j in rand_indexes:

                rand_type = random.sample(range(1, 101), 1)[0]

                if rand_type <= 20:
                    Relationship.objects.get_or_create(
                        name=f"Связь типа: Слабая",
                        ontology=ontology,
                        type=types[0],
                        source=vertices[i],
                        target=vertices[j]
                    )
                elif rand_type <= 55:
                    Relationship.objects.get_or_create(
                        name=f"Связь типа: Агрегация",
                        ontology=ontology,
                        type=types[1],
                        source=vertices[i],
                        target=vertices[j]
                    )
                else:
                    Relationship.objects.get_or_create(
                        name=f"Связь типа: Асоциация",
                        ontology=ontology,
                        type=types[2],
                        source=vertices[i],
                        target=vertices[j]
                    )

