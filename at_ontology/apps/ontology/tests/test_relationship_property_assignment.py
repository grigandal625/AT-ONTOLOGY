from django.test import TestCase

from at_ontology.apps.ontology.models import Ontology
from at_ontology.apps.ontology.models import Relationship
from at_ontology.apps.ontology.models import RelationshipPropertyAssignment
from at_ontology.apps.ontology.models import Vertex
from at_ontology.apps.ontology_model.models import DataType
from at_ontology.apps.ontology_model.models import RelationshipType
from at_ontology.apps.ontology_model.models import RelationshipTypePropertyDefinition
from at_ontology.apps.ontology_model.models import VertexType


class RelationshipPropertyAssignmentTest(TestCase):
    def setUp(self):
        self.data_type = DataType.objects.create(name="StringType", object_schema={"type": "string"})
        self.relationship_type = RelationshipType.objects.create(name="TestRelation")
        self.property_def = RelationshipTypePropertyDefinition.objects.create(
            name="TestProperty", object_type=self.relationship_type, data_type=self.data_type
        )
        self.source_vertex = Vertex.objects.create(
            name="SourceVertex",
            type=VertexType.objects.create(name="SourceType"),
            ontology=Ontology.objects.create(name="TestOntology"),
        )
        self.target_vertex = Vertex.objects.create(
            name="TargetVertex", type=VertexType.objects.create(name="TargetType"), ontology=self.source_vertex.ontology
        )
        self.relationship = Relationship.objects.create(
            source=self.source_vertex, target=self.target_vertex, type=self.relationship_type
        )

    def test_valid_property_value(self):
        assignment = RelationshipPropertyAssignment.objects.create(
            object=self.relationship, property=self.property_def, value="ValidValue"
        )
        self.assertEqual(assignment.value, "ValidValue")

    def test_invalid_property_value(self):
        with self.assertRaises(Exception):  # ValidationError обрабатывается внутри clean()
            p = RelationshipPropertyAssignment.objects.create(
                object=self.relationship, property=self.property_def, value=123
            )
            p.clean()
