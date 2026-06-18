from django.test import TestCase
from at_ontology_parser.parsing.parser import Parser
from pathlib import Path

# Импортируем напрямую из нашего модуля, а не из at_ontology
from at_ontology.apps.ontology.tests.similarity_flooding import OntologySimilarityMatcher, print_results

DIR_PATH = Path(__file__).parent

class Test(TestCase):

    def test_same_vertex(self):
        parser1 = Parser()
        parser2 = Parser()

        print ("Загрузка онтологий")

        ontology1 = parser1.load_ontology(DIR_PATH / "fixtures/test_same_vertex/ontology1.yaml")
        ontology2 = parser2.load_ontology(DIR_PATH / "fixtures/test_same_vertex/ontology2.yaml")

        self.assertIsNotNone(ontology1, "онтология 1 не загрузилась")
        self.assertIsNotNone(ontology2, "онтология 2 не загрузилась")

        matcher = OntologySimilarityMatcher(
            ontology1,
            ontology2,
            iterations=20,
            min_score=0.05,
            # vertex_filter=lambda v: v.name.startswith("Topic_"),  # для реальных онтологий
        )

        results = matcher.run(top_k=10)

        # Тестовые онтологии идентичны, поэтому ожидаем совпадения с σ ≈ 1.0
        self.assertTrue(len(results) > 0, "Не найдено ни одного совпадения")

        for pair in results:
            print(f"{pair.vertex_a.name} <-> {pair.vertex_b.name}: {pair.score:.3f}")

        # Красивый вывод с σ₀
        print_results(results, show_initial=True)

        self.assertTrue(len(results) > 0, "Не найдено ни одного совпадения")
        top = results[0]
        print(f"\nЛучшее совпадение: {top.vertex_a.label} <-> {top.vertex_b.label} ({top.score:.3f})")
