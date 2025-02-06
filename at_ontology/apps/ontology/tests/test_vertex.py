from django.test import TestCase

from at_ontology.apps.ontology.models import Ontology
from at_ontology.apps.ontology.models import Vertex
from at_ontology.apps.ontology_model.models import VertexType


class VertexTest(TestCase):
    def setUp(self):
        self.ontology = Ontology.objects.create(name="TestOntology")
        self.concrete_type = VertexType.objects.create(name="ConcreteType")
        self.abstract_type = VertexType.objects.create(name="AbstractType", abstract=True)

    def test_create_vertex_with_concrete_type(self):
        vertex = Vertex.objects.create(name="TestVertex", type=self.concrete_type, ontology=self.ontology)
        self.assertEqual(str(vertex), "TestVertex (ConcreteType)")

    def test_create_vertex_with_abstract_type(self):
        with self.assertRaises(Exception):  # ValidationError обрабатывается внутри clean()
            v = Vertex.objects.create(name="InvalidVertex", type=self.abstract_type, ontology=self.ontology)
            v.clean()
