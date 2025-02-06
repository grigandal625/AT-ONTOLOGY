from django.core.exceptions import ValidationError
from django.test import TestCase

from at_ontology.apps.ontology_model.models import DataType


class DataTypeModelTest(TestCase):
    def test_valid_object_schema(self):
        data_type = DataType.objects.create(name="TestType", object_schema={"type": "string"})
        data_type.clean()
        self.assertEqual(str(data_type), "TestType")

    def test_invalid_object_schema(self):
        with self.assertRaises(ValidationError):
            data_type = DataType.objects.create(name="InvalidType", object_schema={"type": "unknown"})  # Неверная схема
            data_type.clean()

    def test_nullable_object_schema(self):
        data_type = DataType.objects.create(name="NoSchemaType")
        self.assertIsNone(data_type.object_schema)
