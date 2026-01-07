from django.test import TestCase

from at_ontology.apps.ontology_model.models import RelationshipType
from at_ontology.apps.ontology_model.models import VertexType


class RelationshipTypeTest(TestCase):
    def setUp(self):
        # Создаем тестовые типы вершин
        self.object_type1 = VertexType.objects.create(name="VertexType1")
        self.object_type2 = VertexType.objects.create(name="VertexType2")
        self.abstract_vertex_type = VertexType.objects.create(name="AbstractVertexType", abstract=True)

    def test_create_relationship_type(self):
        """Тест создания типа связи без ограничений на типы вершин."""
        relationship_type = RelationshipType.objects.create(name="TestRelation")
        self.assertEqual(str(relationship_type), "TestRelation")

    def test_add_valid_source_vertex_types(self):
        """Тест добавления допустимых типов родительских вершин."""
        relationship_type = RelationshipType.objects.create(name="TestRelation")
        relationship_type.valid_source_types.add(self.object_type1)
        self.assertIn(self.object_type1, relationship_type.valid_source_types.all())

    def test_add_valid_target_vertex_types(self):
        """Тест добавления допустимых типов дочерних вершин."""
        relationship_type = RelationshipType.objects.create(name="TestRelation")
        relationship_type.valid_target_types.add(self.object_type2)
        self.assertIn(self.object_type2, relationship_type.valid_target_types.all())
