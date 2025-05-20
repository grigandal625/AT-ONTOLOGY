import json
from pathlib import Path
from django.core.management.base import BaseCommand
from at_ontology.apps.ontology.models import Vertex, Relationship, Ontology
from at_ontology.apps.ontology_model.models import OntologyModel, VertexType, RelationshipType
import sqlite3

class Command(BaseCommand):
    help = "Перенос ДИС из JSON"
    def handle(self, *args, **options):

        json_path = Path("at_ontology/apps/ontology/management/commands/DIS.json")

        if not json_path.exists():
            self.stdout.write(self.style.ERROR(f"Файл {json_path} не найден."))
            return

        with open(json_path, "r", encoding="utf-8") as f:
            course_structure = json.load(f)

        ontology = Ontology.objects.get(name="Динамические интеллектуальные системы")
        ontology_model = OntologyModel.objects.get(name="Прикладная онтология курса/дисциплины")

        topic_type = VertexType.objects.get(name="Тема", ontology_model=ontology_model)
        subtopic_type = VertexType.objects.get(name="Подтема", ontology_model=ontology_model)
        relationship_type = RelationshipType.objects.get(name="Иерархическая", ontology_model=ontology_model)

        def create_vertex_hierarchy(structure, parent=None, depth=0):
            for name, children in structure.items():
                vertex, created = Vertex.objects.get_or_create(
                    name=name,
                    ontology=ontology,
                    defaults={"type": topic_type if depth == 0 else subtopic_type}
                )
                if not created:
                    self.stdout.write(f"Пропущено (уже существует): {vertex.name}")
                if parent:
                    Relationship.objects.get_or_create(
                        name="Иерархическая связь",
                        ontology=ontology,
                        type=relationship_type,
                        source=parent,
                        target=vertex
                    )
                create_vertex_hierarchy(children, parent=vertex, depth=depth + 1)

        create_vertex_hierarchy(course_structure)

        self.stdout.write(self.style.SUCCESS("Структура курса успешно загружена из JSON."))



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