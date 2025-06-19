import sqlite3

from django.core.management.base import BaseCommand

from at_ontology.apps.ontology.models import Ontology
from at_ontology.apps.ontology.models import Relationship
from at_ontology.apps.ontology.models import Vertex
from at_ontology.apps.ontology_model.models import OntologyModel
from at_ontology.apps.ontology_model.models import RelationshipType
from at_ontology.apps.ontology_model.models import VertexType


class Command(BaseCommand):
    help = "Перенос тем/подтем и иерархических связей между ними"

    def handle(self, *args, **options):
        ontology_1 = self.create_ontology(name="Введение в интеллектуальные системы")
        ontology_2 = self.create_ontology(name="Интеллектуальные диалоговые системы")
        self.create_ontology(name="Динамические интеллектуальные системы")
        ontology_model = self.create_ontology_model(
            name="ATOntology.model.AppliedCourceDisci", label="Прикладная онтология курса/дисциплины"
        )

        element_course = self.create_vertex_type(name="Элемент курса/дисциплины", ontology_model=ontology_model)

        topic = self.create_vertex_type(name="Тема", ontology_model=ontology_model, derived_from=element_course)

        subtopic = self.create_vertex_type(name="Подтема", ontology_model=ontology_model, derived_from=element_course)

        hierarchical_type = self.create_hierarchical_relationship_type(
            ontology_model=ontology_model, topic_type=topic, subtopic_type=subtopic
        )

        conn = sqlite3.connect("development.sqlite3")
        cursor = conn.cursor()

        cursor.execute(
            """
        WITH RECURSIVE chain(id, text, parent_id, root_id, depth) AS (
            SELECT id, text, parent_id, parent_id AS root_id, 1 AS depth
            FROM ka_topics
            WHERE parent_id IN (2, 45)
            UNION ALL
            SELECT t.id, t.text, t.parent_id, c.root_id, c.depth + 1
            FROM ka_topics t
            JOIN chain c ON t.parent_id = c.id
        )
        SELECT id, text, parent_id, root_id, depth FROM chain;
        """
        )

        rows = cursor.fetchall()

        conn.close()

        ontology_by_root = {2: ontology_1, 45: ontology_2}
        id_to_vertex = {}

        for topic_id, text, parent_id, root_id, depth in rows:
            ontology = ontology_by_root[root_id]

            vertex_type = topic if depth == 1 else subtopic

            vertex, _ = Vertex.objects.get_or_create(name=text, ontology=ontology, type=vertex_type)

            id_to_vertex[topic_id] = vertex

            if parent_id in id_to_vertex:
                Relationship.objects.get_or_create(
                    name="Иерархическая связь",
                    ontology=ontology,
                    type=hierarchical_type,
                    source=id_to_vertex[parent_id],
                    target=vertex,
                )

        self.stdout.write(self.style.SUCCESS(f"Перенесено {len(rows)} тем и связей"))

    def create_ontology(self, name: str) -> Ontology:
        ontology, created = Ontology.objects.get_or_create(name=name)

        if created:
            self.stdout.write(self.style.SUCCESS(f"Created Ontology: {ontology.name} (id={ontology.id})"))
        else:
            self.stdout.write(f"Ontology already exists: {ontology.name} (id={ontology.id})")
        return ontology

    def create_ontology_model(self, name: str) -> OntologyModel:
        model, created = OntologyModel.objects.get_or_create(name=name)

        if created:
            self.stdout.write(self.style.SUCCESS(f"Created OntologyModel: {model.name} (id={model.id})"))
        else:
            self.stdout.write(f"OntologyModel already exists: {model.name} (id={model.id})")
        return model

    def create_vertex_type(
        self, name: str, ontology_model: OntologyModel, derived_from: VertexType = None
    ) -> VertexType:
        vt, created = VertexType.objects.get_or_create(
            name=name, ontology_model=ontology_model, derived_from=derived_from
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"Created VertexType: {vt.name} (id={vt.id})"))
        else:
            self.stdout.write(f"VertexType already exists: {vt.name} (id={vt.id})")

        return vt

    def create_hierarchical_relationship_type(self, ontology_model, topic_type, subtopic_type):
        rt, created = RelationshipType.objects.get_or_create(name="Иерархическая", ontology_model=ontology_model)

        # Добавим допустимые типы вершин (если новые или неполные)
        rt.valid_source_vertex_types.set([topic_type, subtopic_type])
        rt.valid_target_vertex_types.set([topic_type, subtopic_type])

        rt.save()

        if created:
            self.stdout.write(self.style.SUCCESS(f"Создан тип связи: {rt.name}"))
        else:
            self.stdout.write(f"Тип связи уже существует: {rt.name}")

        return rt
