from django.test import TestCase

from at_ontology.apps.ontology.models import Ontology
from at_ontology.apps.ontology.models import Relationship
from at_ontology.apps.ontology.models import Vertex
from at_ontology.apps.ontology_model.models import RelationshipType
from at_ontology.apps.ontology_model.models import VertexType


class RelationshipTest(TestCase):
    def setUp(self):
        self.ontology = Ontology.objects.create(name="TestOntology")
        self.source_type = VertexType.objects.create(name="SourceType")
        self.target_type = VertexType.objects.create(name="TargetType")
        self.relationship_type = RelationshipType.objects.create(name="TestRelation")
        self.relationship_type.valid_source_types.add(self.source_type)
        self.relationship_type.valid_target_types.add(self.target_type)
        self.source_vertex = Vertex.objects.create(name="SourceVertex", type=self.source_type, ontology=self.ontology)
        self.target_vertex = Vertex.objects.create(name="TargetVertex", type=self.target_type, ontology=self.ontology)

    def test_valid_relationship(self):
        relationship = Relationship.objects.create(
            source=self.source_vertex, target=self.target_vertex, type=self.relationship_type
        )
        self.assertEqual(str(relationship), f"({relationship.pk}) TestRelation")

    def test_invalid_ontology(self):
        another_ontology = Ontology.objects.create(name="AnotherOntology")
        invalid_vertex = Vertex.objects.create(name="InvalidVertex", type=self.target_type, ontology=another_ontology)
        with self.assertRaises(Exception):  # ValidationError обрабатывается внутри clean()
            r = Relationship.objects.create(
                source=self.source_vertex, target=invalid_vertex, type=self.relationship_type
            )
            r.clean()

    def test_invalid_source_vertex_type(self):
        invalid_vertex_type = VertexType.objects.create(name="InvalidType")
        invalid_vertex = Vertex.objects.create(name="InvalidVertex", type=invalid_vertex_type, ontology=self.ontology)
        with self.assertRaises(Exception):  # ValidationError обрабатывается внутри clean()
            r = Relationship.objects.create(
                source=invalid_vertex, target=self.target_vertex, type=self.relationship_type
            )
            r.clean()
