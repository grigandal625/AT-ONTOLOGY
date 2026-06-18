from django.test import TestCase
from at_ontology_parser.parsing.parser import Parser
from pathlib import Path
from at_ontology.apps.ontology.tests.similarity_flooding import (
    OntologySimilarityMatcher, print_results
)

DIR_PATH = Path(__file__).parent


class Test(TestCase):

    def test_same_vertex(self):
        parser1 = Parser()
        parser2 = Parser()

        ontology1 = parser1.load_ontology(
            DIR_PATH / "fixtures/test_same_vertex/ontology1.yaml"
        )
        ontology2 = parser2.load_ontology(
            DIR_PATH / "fixtures/test_same_vertex/ontology2.yaml"
        )

        self.assertIsNotNone(ontology1)
        self.assertIsNotNone(ontology2)

        print(f"\nОнтология 1: {ontology1.name} — вершин: {len(ontology1.vertices)}")
        print(f"Онтология 2: {ontology2.name} — вершин: {len(ontology2.vertices)}")

        matcher = OntologySimilarityMatcher(
            ontology1,
            ontology2,
            iterations=10,
            min_score=0.10,
            sf_weight=0.3,
        )
        results = matcher.run(top_k=20)

        self.assertTrue(len(results) > 0)

        print("\n=== ПОИСК ЭКСПЕРТНЫХ ПАР ===")
        expert = [
            "Динамические интегрированные",
            "Онтология",
            "Онтологический инжиниринг",
            "Перечень типовых",
            "Определение динамической",
            "Искусственный интеллект: совр",
        ]
        found = set()
        for r in results:
            la = _get_label_safe(r.vertex_a)
            lb = _get_label_safe(r.vertex_b)
            for kw in expert:
                if kw.lower() in la.lower() and kw not in found:
                    print(f"  ✓ {la[:45]} <-> {lb[:45]}: σ={r.score:.3f}")
                    found.add(kw)

        print_results(results, show_initial=True)
        top = results[0]
        print(f"\nЛучшее: {_get_label_safe(top.vertex_a)} <-> "
              f"{_get_label_safe(top.vertex_b)} ({top.score:.3f})")


def _get_label_safe(v: object) -> str:
    return (getattr(v, 'label', None) or v.name).strip()