from django.test import TestCase
from at_ontology_parser.parsing.parser import Parser
from pathlib import Path

from at_ontology.apps.ontology.tests.embeddings_matcher import EmbeddingsSimilarityMatcher
from at_ontology.apps.ontology.tests.similarity_flooding import print_results

DIR_PATH = Path(__file__).parent


class Test(TestCase):

    def test_same_vertex(self):
        parser1 = Parser()
        parser2 = Parser()

        ontology1 = parser1.load_ontology(DIR_PATH / "fixtures/test_same_vertex/ontology1.yaml")
        ontology2 = parser2.load_ontology(DIR_PATH / "fixtures/test_same_vertex/ontology2.yaml")

        self.assertIsNotNone(ontology1, "Онтология 1 не загрузилась")
        self.assertIsNotNone(ontology2, "Онтология 2 не загрузилась")

        print(f"\nОнтология 1: {ontology1.name} — вершин: {len(ontology1.vertices)}")
        print(f"Онтология 2: {ontology2.name} — вершин: {len(ontology2.vertices)}")

        matcher = EmbeddingsSimilarityMatcher(
            ontology1,
            ontology2,
            use_sf=True,
            min_score=0.3,
            vertex_filter=lambda v: v.name.startswith("Topic_"),
        )
        results = matcher.run(top_k=20)

        self.assertTrue(len(results) > 0, "Не найдено ни одного соответствия")

        print("\n=== ПОИСК ЭКСПЕРТНЫХ ПАР ===")
        expert_keywords = [
            "Онтология",
            "Определение динамической",
            "Перечень типовых",
            "Архитектура динамической",
            "Динамические интегрированные",
            "Основные понятия",
        ]
        for r in results:
            label_a = getattr(r.vertex_a, 'label', '') or ''
            label_b = getattr(r.vertex_b, 'label', '') or ''
            for kw in expert_keywords:
                if kw.lower() in label_a.lower():
                    print(f"  {label_a[:50]} <-> {label_b[:50]}: σ={r.score:.3f}")

        print_results(results, show_initial=True)

        top = results[0]
        print(f"\nЛучшее совпадение: {top.vertex_a.label} <-> {top.vertex_b.label} ({top.score:.3f})")