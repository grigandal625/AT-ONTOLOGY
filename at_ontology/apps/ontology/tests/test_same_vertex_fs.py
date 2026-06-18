from django.test import TestCase
from at_ontology_parser.parsing.parser import Parser
from pathlib import Path
from at_ontology.apps.ontology.tests.similarity_flooding_copy_cool_run2 import OntologySimilarityMatcher, print_results

DIR_PATH = Path(__file__).parent


class Test(TestCase):

    def test_same_vertex(self):
        parser1 = Parser()
        parser2 = Parser()

        ontology1 = parser1.load_ontology(DIR_PATH / "fixtures/test_same_vertex/o1.yaml")
        ontology2 = parser2.load_ontology(DIR_PATH / "fixtures/test_same_vertex/o2.yaml")

        self.assertIsNotNone(ontology1, "Онтология 1 не загрузилась")
        self.assertIsNotNone(ontology2, "Онтология 2 не загрузилась")

        print(f"\nОнтология 1: {ontology1.name} — вершин: {len(ontology1.vertices)}")
        print(f"Онтология 2: {ontology2.name} — вершин: {len(ontology2.vertices)}")

        matcher = OntologySimilarityMatcher(
            ontology1,
            ontology2,
            iterations=20,
            min_score=0.05,
            vertex_filter=lambda v: v.name.startswith("Topic_"),
        )
        results = matcher.run(top_k=20)

        print("\n=== ПОИСК ЭКСПЕРТНЫХ ПАР ===")
        expert_a = ["Онтология", "Определение динамической", "Перечень типовых", "Архитектура динамической"]
        for r in results:
            label_a = getattr(r.vertex_a, 'label', '') or ''
            label_b = getattr(r.vertex_b, 'label', '') or ''
            for ea in expert_a:
                if ea.lower() in label_a.lower():
                    print(f"  {label_a[:50]} <-> {label_b[:50]}: σ={r.score:.3f}")

        self.assertTrue(len(results) > 0, "Не найдено ни одного соответствия")

        print_results(results, show_initial=True)

        top = results[0]
        print(f"\nЛучшее совпадение: {top.vertex_a.label} <-> {top.vertex_b.label} ({top.score:.3f})")