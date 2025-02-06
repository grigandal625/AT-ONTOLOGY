from django.test import TestCase

from at_ontology.apps.ontology.models import Ontology
from at_ontology.apps.ontology.models import Vertex
from at_ontology.apps.ontology.models import VertexPropertyAssignment
from at_ontology.apps.ontology_model.models import DataType
from at_ontology.apps.ontology_model.models import VertexType
from at_ontology.apps.ontology_model.models import VertexTypePropertyDefinition


class VertexPropertyAssignmentTest(TestCase):
    def setUp(self):
        self.data_type = DataType.objects.create(name="StringType", object_schema={"type": "string"})
        self.object_type = VertexType.objects.create(name="TestVertexType")
        self.property_def = VertexTypePropertyDefinition.objects.create(
            name="TestProperty", object_type=self.object_type, data_type=self.data_type
        )
        self.ontology = Ontology.objects.create(name="TestOntology")
        self.vertex = Vertex.objects.create(name="TestVertex", type=self.object_type, ontology=self.ontology)

    def test_valid_property_value(self):
        assignment = VertexPropertyAssignment.objects.create(
            object=self.vertex, property=self.property_def, value="ValidValue"
        )
        self.assertEqual(assignment.value, "ValidValue")

    def test_invalid_property_value(self):
        with self.assertRaises(Exception):  # ValidationError обрабатывается внутри clean()
            p = VertexPropertyAssignment.objects.create(object=self.vertex, property=self.property_def, value=123)
            p.clean()
