from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional
from django.core.management import BaseCommand
from sqlite3 import connect

from at_ontology.apps.ontology.service import OntologyService
from at_ontology_parser.parsing.parser import Parser
from at_ontology.apps.ontology_model.import_loader import DBLoader

import time

COURSE_ELEMENT = 'CourceDiscipline.vertex_types.CourseElement'
COMPETENCE = 'CourceDiscipline.vertex_types.Competence'

HIERARCHY = 'CourceDiscipline.relationship_types.Hierarchy'
AGREGATION = 'CourceDiscipline.relationship_types.Agregation'
ASSOCIATION = 'CourceDiscipline.relationship_types.Association'
WEAK = 'CourceDiscipline.relationship_types.Weak'
COMPETENCE_TO_ELEMENT = 'CourceDiscipline.relationship_types.CompetenceToElement'

@dataclass(frozen=True)
class KaTopic:
    id: int
    text: str
    ancestry: Optional[str]

    @property
    def parent_id(self):

        if self.ancestry is None:
            return None
        
        return self.ancestry.split("/")[-1]

@dataclass(frozen=True)
class KaQuestion:
    id: int
    text: str
    ka_topic_id: int
    difficulty: int


@dataclass
class KaAnswer:
    id: int
    text: str
    ka_question_id: int
    correct: bool

    def __post_init__(self):
        self.correct = bool(self.correct)

@dataclass(frozen=True)
class TopicRelation:
    ka_topic_id: int
    related_topic_id: int
    rel_type: Literal[1, 2, 3]

    @property
    def relation_type(self):
        return {
            0: AGREGATION,
            1: ASSOCIATION,
            2: WEAK,
        }[self.rel_type]
    
@dataclass(frozen=True)
class Competence:
    id: int
    code: str
    description: str

@dataclass(frozen=True)
class TopicCompetence:
    ka_topic_id: int
    competence_id: int
    weight: float

class LegacyService:
    
    def __init__(self, db_path: str | Path):
        self.db_path = db_path
        self.conn = connect(str(db_path))
        self.cursor = self.conn.cursor()
    
    def root_ka_topics(self) -> list[KaTopic]:
        self.cursor.execute("SELECT id, text, ancestry from ka_topics WHERE ancestry IS NULL")
        return [KaTopic(*item) for item in self.cursor.fetchall()]
    
    def get_ka_topic(self, topic_id: int | str) -> KaTopic:
        self.cursor.execute("SELECT id, text, ancestry from ka_topics WHERE id = :topic_id", {'topic_id': str(topic_id)})
        return KaTopic(*self.cursor.fetchone())
    
    def _get_children(self, topic_id: int | str) -> list[KaTopic]:
        self.cursor.execute("SELECT id, text, ancestry from ka_topics WHERE ancestry LIKE '%/' || :topic_id OR ancestry = :topic_id", {'topic_id': str(topic_id)})
        return [KaTopic(*item) for item in self.cursor.fetchall()]
    
    def children(self, ka_topic: KaTopic) -> list[KaTopic]:
        return self._get_children(ka_topic.id)
    
    def _get_parent(self, topic_id) -> Optional[KaTopic]:
        topic = self.get_ka_topic(topic_id)
        if topic.parent_id is None:
            return None
        
        return self.get_ka_topic(topic.parent_id)
    
    def parent(self, ka_topic: KaTopic) -> Optional[KaTopic]:
        if ka_topic.parent_id is None:
            return None

        return self.get_ka_topic(ka_topic.parent_id)
    
    def _get_subtree(self, topic_id: int | str) -> list[KaTopic]:
        topic_id = str(topic_id)
        self.cursor.execute("""
            SELECT id, text, ancestry
            FROM ka_topics
            WHERE
                ancestry = :id
                OR ancestry LIKE :id || '/%'
                OR ancestry LIKE '%/' || :id
                OR ancestry LIKE '%/' || :id || '/%'
        """, {"id": topic_id})

        return [KaTopic(*row) for row in self.cursor.fetchall()]
    
    def subtree(self, ka_topic: KaTopic) -> list[KaTopic]:
        return self._get_subtree(ka_topic.id)
    
    def get_topics(self, topic_ids: list[int | str]) -> list[KaTopic]:
        self.cursor.execute("""
            SELECT id, text, ancestry
            FROM ka_topics
            WHERE id IN :topic_ids
        """, {"topic_ids": tuple(topic_ids)})
        return [KaTopic(*row) for row in self.cursor.fetchall()]
    
    def _get_parents(self, topic_id: int | str) -> list[KaTopic]:
        topic = self.get_ka_topic(topic_id)
        if not topic.ancestry:
            return []
        
        parent_ids = topic.ancestry.split("/")
        return self.get_topics(parent_ids)
        
    def get_ka_question(self, question_id: int | str) -> KaQuestion:
        self.cursor.execute("""
            SELECT id, text, ka_topic_id, difficulty
            FROM ka_questions
            WHERE id = :question_id
        """, {"question_id": str(question_id)})
        return KaQuestion(*self.cursor.fetchone())
    
    def _get_ka_questions(self, question_ids: list[int | str]) -> list[KaQuestion]:
        self.cursor.execute("""
            SELECT id, text, ka_topic_id, difficulty
            FROM ka_questions
            WHERE id IN :question_ids
        """, {"question_ids": tuple(question_ids)})
        return [KaQuestion(*row) for row in self.cursor.fetchall()]
    
    def _get_topic_questions(self, topic_id: int | str) -> list[KaQuestion]:
        self.cursor.execute("""
            SELECT id, text, ka_topic_id, difficulty
            FROM ka_questions
            WHERE ka_topic_id = :topic_id
        """, {"topic_id": str(topic_id)})
        return [KaQuestion(*row) for row in self.cursor.fetchall()]
    
    def get_topic_questions(self, topic: KaTopic) -> list[KaQuestion]:
        return self._get_topic_questions(topic.id)
    
    def get_ka_answer(self, answer_id: int | str) -> KaAnswer:
        self.cursor.execute("""
            SELECT id, text, ka_question_id, correct
            FROM ka_answers
            WHERE id = :answer_id
        """, {"answer_id": str(answer_id)})
        return KaAnswer(*self.cursor.fetchone())
    
    def _get_ka_answers(self, answer_ids: list[int | str]) -> list[KaAnswer]:
        self.cursor.execute("""
            SELECT id, text, ka_question_id, correct
            FROM ka_answers
            WHERE id IN :answer_ids
        """, {"answer_ids": tuple(answer_ids)})
        return [KaAnswer(*row) for row in self.cursor.fetchall()]
    
    def _get_ka_question_answers(self, question_id: int | str) -> list[KaAnswer]:
        self.cursor.execute("""
            SELECT id, text, ka_question_id, correct
            FROM ka_answers
            WHERE ka_question_id = :question_id
        """, {"question_id": str(question_id)})
        return [KaAnswer(*row) for row in self.cursor.fetchall()]
    
    def get_ka_question_answers(self, question: KaQuestion) -> list[KaAnswer]:
        return self._get_ka_question_answers(question.id)
    
    def _get_output_relations(self, topic_id: int | str) -> list[TopicRelation]:
        self.cursor.execute("""
            SELECT ka_topic_id, related_topic_id, rel_type
            FROM topic_relations
            WHERE ka_topic_id = :topic_id
        """, {"topic_id": str(topic_id)})
        return [TopicRelation(*row) for row in self.cursor.fetchall()]
    
    def get_output_relations(self, topic: KaTopic) -> list[TopicRelation]:
        return self._get_output_relations(topic.id)

    def _get_input_relations(self, topic_id: int | str) -> list[TopicRelation]:
        self.cursor.execute("""
            SELECT ka_topic_id, related_topic_id, rel_type
            FROM topic_relations
            WHERE related_topic_id = :topic_id
        """, {"topic_id": str(topic_id)})
        return [TopicRelation(*row) for row in self.cursor.fetchall()]
    
    def get_input_relations(self, topic: KaTopic) -> list[TopicRelation]:
        return self._get_input_relations(topic.id)
    
    def _get_competence(self, competence_id: int | str) -> Competence:
        self.cursor.execute("""
            SELECT id, code, description
            FROM competences
            WHERE id = :competence_id
        """, {"competence_id": str(competence_id)})
        return Competence(*self.cursor.fetchone())
    
    def _get_competences(self, competence_ids: list[int | str]) -> list[Competence]:
        self.cursor.execute("""
            SELECT id, code, description
            FROM competences
            WHERE id IN :competence_ids
        """, {"competence_ids": tuple(competence_ids)})
        return [Competence(*row) for row in self.cursor.fetchall()]
    
    def _get_all_competences(self) -> list[Competence]:
        self.cursor.execute("""
            SELECT id, code, description
            FROM competences
        """)
        return [Competence(*row) for row in self.cursor.fetchall()]
    
    def _get_topic_competences(self, topic_id: int | str) -> list[TopicCompetence]:
        self.cursor.execute("""
            SELECT ka_topic_id, competence_id, weight
            FROM topic_competences
            WHERE ka_topic_id = :topic_id
        """, {"topic_id": str(topic_id)})
        return [TopicCompetence(*row) for row in self.cursor.fetchall()]
    
    def _get_cmp_topic_competences(self, competence_id: int | str) -> list[TopicCompetence]:
        self.cursor.execute("""
            SELECT ka_topic_id, competence_id, weight
            FROM topic_competences
            WHERE competence_id = :competence_id
        """, {"competence_id": str(competence_id)})
        return [TopicCompetence(*row) for row in self.cursor.fetchall()]
    
    def get_topic_competences(self, topic: KaTopic) -> list[TopicCompetence]:
        return self._get_topic_competences(topic.id)
    
    def get_cmp_topic_competences(self, competence: Competence) -> list[TopicCompetence]:
        return self._get_cmp_topic_competences(competence.id)
    
    def ka_topic_to_vertex_source(self, topic: KaTopic) -> dict:
        questions = self.get_topic_questions(topic)
        result = {
            'label': topic.text,
            'type': COURSE_ELEMENT,
            'metadata': {'legacy_db_id': topic.id, 'parent_id': topic.parent_id}
        }

        if questions:
            result['properties'] = { 
                'questions': [{
                    'question': question.text,
                    'difficulty': question.difficulty,
                    'answers': [{
                        'answer': answer.text,
                        'correct': answer.correct
                    } for answer in self.get_ka_question_answers(question)]
                } for question in questions]
            }
        
        return result

    def competence_to_vertex_source(self, competence: Competence) -> dict:
        return {
            'label': competence.code,
            'type': COMPETENCE,
            'metadata': {'legacy_db_id': competence.id},
            'properties': {
                'code': competence.code,
                'description': competence.description
            }
        }
    
    def collect_vertices(self, root_ka_topic: KaTopic) -> dict[str, dict]:
        vertices = {}
        index = 0
        for topic in [root_ka_topic] + self.subtree(root_ka_topic):
            vertices[f'Topic_{index}'] = self.ka_topic_to_vertex_source(topic)

            index += 1

        index = 0
        
        for competence in self._get_all_competences():
            vertices[f'Competence_{index}'] = self.competence_to_vertex_source(competence)
            index += 1

        return vertices

    def collect_hierarchy_relationships(self, vertices: dict[str, dict]) -> dict[str, dict]:
        relationships = {}
        index = 0

        def find_vertex_by_id(id, vertices: dict[str, dict], type):
            return next(iter([
                (name, vertex)
                for name, vertex in vertices.items() 
                if str(vertex.get('metadata', {}).get('legacy_db_id')) == str(id) and vertex['type'] == type
            ]), None)

        for vertex_name, vertex in vertices.items():
            if vertex['type'] == COURSE_ELEMENT and vertex['metadata']['parent_id'] is not None:
                source = vertex_name

                target_name_and_vertex = find_vertex_by_id(vertex['metadata']['parent_id'], vertices, COURSE_ELEMENT)
                if target_name_and_vertex is None:
                    raise RuntimeError(f'Cannot find parent vertex for {vertex_name}')
                
                target = target_name_and_vertex[0]

                relationships[f'Hierarchy_{index}'] = {
                    'source': source,
                    'target': target,
                    'type': HIERARCHY
                }
                index += 1

        return relationships

    def collect_topic_relationships(self, vertices: dict[str, dict]) -> dict[str, dict]:

        relationships = {}
        index = 0

        def find_vertex_by_id(id, vertices: dict[str, dict], type):
            return next(iter([
                (name, vertex)
                for name, vertex in vertices.items() 
                if str(vertex.get('metadata', {}).get('legacy_db_id')) == str(id) and vertex['type'] == type
            ]), None)
        
        for vertex_name, vertex in vertices.items():
            if vertex['type'] == COURSE_ELEMENT:
                ka_topic_id = vertex['metadata']['legacy_db_id']
                ka_topic = self.get_ka_topic(ka_topic_id)

                for relation in self.get_output_relations(ka_topic):
                    target_name_and_vertex = find_vertex_by_id(relation.related_topic_id, vertices, COURSE_ELEMENT)
                    if target_name_and_vertex is None:
                        # print(f'Cannot find target vertex for relation {relation} from {vertex_name}')
                        continue
                    
                    target = target_name_and_vertex[0]

                    relationships[f'Relation_{index}'] = {
                        'source': vertex_name,
                        'target': target,
                        'type': relation.relation_type
                    }
                    index += 1
        return relationships
    
    def collect_topic_competence_relationships(self, vertices: dict[str, dict]) -> dict[str, dict]:
        relationships = {}
        index = 0

        def find_vertex_by_id(id, vertices: dict[str, dict], type):
            return next(iter([
                (name, vertex)
                for name, vertex in vertices.items() 
                if str(vertex.get('metadata', {}).get('legacy_db_id')) == str(id) and vertex['type'] == type
            ]), None)
        
        for vertex_name, vertex in vertices.items():
            if vertex['type'] == COMPETENCE:
                competence_id = vertex['metadata']['legacy_db_id']

                source = vertex_name

                for topic_competence in self._get_cmp_topic_competences(competence_id):

                    name_and_vertex = find_vertex_by_id(topic_competence.ka_topic_id, vertices, COURSE_ELEMENT)
                    
                    if not name_and_vertex:
                        continue

                    target = name_and_vertex[0]

                    relationships[f'CompetenceToElement_{index}'] = {
                        'source': source,
                        'target': target,
                        'type': COMPETENCE_TO_ELEMENT,
                        'properties': {
                            'weight': topic_competence.weight
                        }
                    }
                    index += 1
        return relationships

    def get_ontology_source(self, root_topic: KaTopic) -> dict:
        vertices = self.collect_vertices(root_topic)

        result = {
            'name': root_topic.text,
            'label': root_topic.text,
            'imports': ['<applied-course-discipline-types>'],
            'vertices': vertices,
            'relationships': {
                **self.collect_hierarchy_relationships(vertices),
                **self.collect_topic_relationships(vertices),
                **self.collect_topic_competence_relationships(vertices)
            }
        }

        return result
                
    
    
class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('--db', type=str, help='Path to legacy db')

        return super().add_arguments(parser)
    
    def handle(self, *args, **options):

        service = LegacyService(options['db'])

        for root_topic in service.root_ka_topics():
            print(f'Generating ontology for {root_topic.text}')

            print('Loading source')

            start = time.perf_counter()
            
            ontology_source = service.get_ontology_source(root_topic)

            end = time.perf_counter()
            print(f'Loaded in {end - start:.2f} seconds')

            parser = Parser()
            parser.import_loaders.append(DBLoader())

            print('Parsing ontology')

            start = time.perf_counter()

            ontology = parser.load_ontology_data(ontology_source, '<ontology>', 'ontology')

            end = time.perf_counter()
            print(f'Parsed in {end - start:.2f} seconds')

            print('Validating references')

            start = time.perf_counter()

            parser.finalize_references()

            end = time.perf_counter()
            print(f'Validated in {end - start:.2f} seconds')

            print('Saving ontology')

            start = time.perf_counter()

            OntologyService.ontology_to_db(ontology)

            end = time.perf_counter()
            print(f'Saved in {end - start:.2f} seconds')

        
