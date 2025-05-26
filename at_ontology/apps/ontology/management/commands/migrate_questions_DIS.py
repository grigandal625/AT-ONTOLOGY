from django.core.management.base import BaseCommand
from at_ontology.apps.ontology_model.models import VertexType
from at_ontology.apps.ontology_model.models import OntologyModel
from at_ontology.apps.ontology_model.models import DataType
from at_ontology.apps.ontology_model.models import VertexTypePropertyDefinition
from at_ontology.apps.ontology.models import Ontology
from at_ontology.apps.ontology.models import Vertex
from at_ontology.apps.ontology.models import VertexPropertyAssignment
import sqlite3
import json
from pathlib import Path
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




        question_type_definition = VertexTypePropertyDefinition.objects.get(name="Дефинишн вопроса")

        json_path = Path("at_ontology/apps/ontology/management/commands/questions_DIS.json")
        with open(json_path, "r", encoding="utf-8") as f:
            questions = json.load(f)

        json_path = Path("at_ontology/apps/ontology/management/commands/question_topic_DIS.json")
        with open(json_path, "r", encoding="utf-8") as f:
            question_topic = json.load(f)

        for q in questions:
            v_name = question_topic[q['question']]
            try:
                v = Vertex.objects.get(name=v_name)
            except Vertex.DoesNotExist:
                self.stdout.write(f"Тема не найдена: {v_name}")
                continue

            VertexPropertyAssignment.objects.get_or_create(
                definition=question_type_definition,
                vertex=v,
                vertex_type=v.type,
                value=q
            )



        self.stdout.write(self.style.SUCCESS(f"Добавлено {len(questions)} вопросов."))



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