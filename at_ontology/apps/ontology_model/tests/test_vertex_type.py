from django.test import TestCase

from at_ontology.apps.ontology_model.models import VertexType


class VertexTypeTest(TestCase):
    def test_create_vertex_type(self):
        vertex_type = VertexType.objects.create(name="TestVertexType")
        self.assertEqual(str(vertex_type), "TestVertexType")

    def test_abstract_vertex_type(self):
        vertex_type = VertexType.objects.create(name="AbstractType", abstract=True)
        self.assertTrue(vertex_type.abstract)
