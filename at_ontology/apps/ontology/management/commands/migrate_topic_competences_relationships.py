from django.core.management.base import BaseCommand
from at_ontology.apps.ontology_model.models import VertexType
from at_ontology.apps.ontology_model.models import OntologyModel
from at_ontology.apps.ontology_model.models import RelationshipType
from at_ontology.apps.ontology_model.models import RelationshipTypePropertyDefinition
from at_ontology.apps.ontology.models import Ontology
from at_ontology.apps.ontology.models import Vertex
from at_ontology.apps.ontology.models import Relationship
from at_ontology.apps.ontology.models import RelationshipPropertyAssignment
import sqlite3

class Command(BaseCommand):
    help = "Перенос связей между темами и компетенциями"
    def handle(self, *args, **options):
        ontology_model = OntologyModel.objects.get(name="Прикладная онтология курса/дисциплины")

        weighted_relationship_type, created = RelationshipType.objects.get_or_create(
            name="Весовая",
            ontology_model=ontology_model
        )

        if created:
            self.stdout.write(self.style.SUCCESS(f'Создан тип связи: {weighted_relationship_type.name}'))
        else:
            self.stdout.write(f'Тип связи уже существует: {weighted_relationship_type.name}')

        weighted_relationship_type_definition, created = RelationshipTypePropertyDefinition.objects.get_or_create(
            name='Дефинишн весовой связи',
            ontology_model=ontology_model,
        )
        if created:
            self.stdout.write(self.style.SUCCESS(
                f"Создано определение свойства: {weighted_relationship_type_definition.name} "
                f"(id={weighted_relationship_type_definition.id})"
            ))
        else:
            self.stdout.write(
                f"Определение свойства уже существует: "
                f"{weighted_relationship_type_definition.name} (id={weighted_relationship_type_definition.id})"
            )

        conn = sqlite3.connect('development.sqlite3')
        cursor = conn.cursor()

        cursor.execute("""
                SELECT 
                c.code AS competence_code,
                kt.text AS topic_text,
                ct.weight
                FROM 
                topic_competences ct
                JOIN 
                competences c ON ct.competence_id = c.id
                JOIN 
                ka_topics kt ON ct.ka_topic_id = kt.id;
                """)

        rows = cursor.fetchall()

        conn.close()

        for competence_code, topic_text, weight in rows:
            try:
                competence = Vertex.objects.get(name=competence_code)
            except Vertex.DoesNotExist:
                self.stdout.write(f"Тема не найдена: {topic_text}")
                continue
            except Vertex.MultipleObjectsReturned:
                self.stdout.write(f"Несколько вершин для темы: {topic_text}")
                competence = Vertex.objects.filter(name=competence_code).first()
                self.stdout.write(
                    f"Выбрана первая вершина: {competence.name} "
                    f"(онтология: {competence.ontology.name})"
                )
            try:
                topic = Vertex.objects.get(name=topic_text)
            except Vertex.DoesNotExist:
                self.stdout.write(f"Тема не найдена: {topic_text}")
                continue
            except Vertex.MultipleObjectsReturned:
                self.stdout.write(f"Несколько вершин для темы: {topic_text}")
                topic = Vertex.objects.filter(name=topic_text).first()
                self.stdout.write(
                    f"Выбрана первая вершина: {topic.name} "
                    f"(онтология: {topic.ontology.name})")

            if competence and topic:
                ontology = Ontology.objects.get(name=topic.ontology.name)
                rp, _ = Relationship.objects.get_or_create(
                    name="Связь Компетенция -> Тема",
                    ontology=ontology,
                    type=weighted_relationship_type,
                    source=competence,
                    target=topic
                )
                value_dict = {
                    'weight': weight
                }
                RelationshipPropertyAssignment.objects.get_or_create(
                    definition=weighted_relationship_type_definition,
                    relationship=rp,
                    relationship_type=weighted_relationship_type,
                    value=value_dict
                )


        self.stdout.write(self.style.SUCCESS(f'Перенесено {len(rows)} связей'))


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