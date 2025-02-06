from django.test import TestCase

from at_ontology.apps.ontology_model.models import DataType
from at_ontology.apps.ontology_model.models import VertexType
from at_ontology.apps.ontology_model.models import VertexTypePropertyDefinition


class PropertyDefinitionTest(TestCase):
    def setUp(self):
        self.object_type = VertexType.objects.create(name="TestVertexType")
        self.data_type = DataType.objects.create(name="StringType", object_schema={"type": "string"})

    def test_create_property_definition(self):
        property_def = VertexTypePropertyDefinition.objects.create(
            name="TestProperty", object_type=self.object_type, data_type=self.data_type
        )
        self.assertEqual(str(property_def), "(TestVertexType).TestProperty")

    def test_required_property(self):
        property_def = VertexTypePropertyDefinition.objects.create(
            name="RequiredProperty", object_type=self.object_type, data_type=self.data_type, required=True
        )
        self.assertTrue(property_def.required)

    def test_multiple_values_allowed(self):
        property_def = VertexTypePropertyDefinition.objects.create(
            name="MultipleProperty", object_type=self.object_type, data_type=self.data_type, allows_multiple=True
        )
        self.assertTrue(property_def.allows_multiple)
