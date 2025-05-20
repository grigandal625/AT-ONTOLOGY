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


class Command(BaseCommand):
    help = "Перенос вопросов"

    def handle(self, *args, **options):
        # Получаем нужную модель онтологии и саму онтологию
        ontology_model = OntologyModel.objects.get(
            name="Прикладная онтология курса/дисциплины"
        )
        ontology = Ontology.objects.get(
            name="Введение в интеллектуальные системы"
        )

        topic_type = VertexType.objects.get(name='Тема')
        # Создаём или получаем DataType для типа вопроса
        with open(
            'at_ontology/apps/ontology/management/commands/question_schema.json',
            'r', encoding='utf-8'
        ) as f:
            schema = json.load(f)

        question_type, created = DataType.objects.get_or_create(
            name="Тип вопроса",
            ontology_model=ontology_model,
            object_schema=schema
        )
        if created:
            self.stdout.write(self.style.SUCCESS(
                f"Создан DataType: {question_type.name} (id={question_type.id})"
            ))
        else:
            self.stdout.write(
                f"DataType уже существует: {question_type.name} (id={question_type.id})"
            )

        # Создаём или получаем определение свойства для типа вопроса
        question_type_definition, created = VertexTypePropertyDefinition.objects.get_or_create(
            name='Дефинишн вопроса',
            ontology_model=ontology_model,
            type=question_type
        )
        if created:
            self.stdout.write(self.style.SUCCESS(
                f"Создано определение свойства: {question_type_definition.name} "
                f"(id={question_type_definition.id})"
            ))
        else:
            self.stdout.write(
                f"Определение свойства уже существует: "
                f"{question_type_definition.name} (id={question_type_definition.id})"
            )

        # Читаем вопросы из SQLite
        conn = sqlite3.connect('development.sqlite3')
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                q.text        AS question_text,
                q.difficulty,
                t.text        AS topic_text,
                a.text        AS answer_text,
                a.correct     AS is_correct
            FROM ka_questions AS q
            JOIN ka_topics    AS t
              ON q.ka_topic_id = t.id
            JOIN ka_answers   AS a
              ON a.ka_question_id = q.id
            WHERE q.disable = 0
            ORDER BY q.id, a.id;
        """)
        rows = cursor.fetchall()
        conn.close()

        # Группируем по теме и тексту вопроса
        questions_by_topic = {}
        for question_text, difficulty, topic_text, answer_text, is_correct in rows:
            # Пытаемся найти вершину по имени темы
            try:
                topic_vertex = Vertex.objects.get(name=topic_text)
            except Vertex.DoesNotExist:
                self.stdout.write(f"Тема не найдена: {topic_text}")
                continue
            except Vertex.MultipleObjectsReturned:
                self.stdout.write(f"Несколько вершин для темы: {topic_text}")
                topic_vertex = Vertex.objects.filter(name=topic_text).first()
                self.stdout.write(
                    f"Выбрана первая вершина: {topic_vertex.name} "
                    f"(онтология: {topic_vertex.ontology.name})"
                )

            key = (topic_text, question_text)
            if key not in questions_by_topic:
                questions_by_topic[key] = {
                    "question": question_text,
                    "difficulty": difficulty,
                    "answers": []
                }
            questions_by_topic[key]["answers"].append({
                "answer": answer_text,
                "correct": bool(is_correct)
            })

        # Собираем итоговый список пар [тема, объект_вопроса]
        output_list = []
        for (topic_text, _), qobj in questions_by_topic.items():
            output_list.append([topic_text, qobj])

        # Выводим единым JSON-массивом
        for topic_text, question_obj in output_list:
            try:
                topic_vertex = Vertex.objects.get(name=topic_text)
            except Vertex.DoesNotExist:
                self.stdout.write(f"Тема не найдена: {topic_text}")
                continue
            except Vertex.MultipleObjectsReturned:
                self.stdout.write(f"Несколько вершин для темы: {topic_text}")
                topic_vertex = Vertex.objects.filter(name=topic_text).first()
                self.stdout.write(
                    f"Выбрана первая вершина: {topic_vertex.name} "
                    f"(онтология: {topic_vertex.ontology.name})"
                )
            VertexPropertyAssignment.objects.get_or_create(
                definition=question_type_definition,
                vertex=topic_vertex,
                vertex_type=topic_type,
                value=question_obj
            )







