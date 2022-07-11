from django.db import models
from ontology_model.models import ElementType, RelationType

# Create your models here.


class File(models.Model):
    content = models.FileField()


class Element(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    type = models.ForeignKey(ElementType, on_delete=models.RESTRICT)
    data = models.JSONField(null=True, blank=True)
    files = models.ManyToManyField(File)


class Relation(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    type = models.ForeignKey(RelationType, on_delete=models.RESTRICT)
