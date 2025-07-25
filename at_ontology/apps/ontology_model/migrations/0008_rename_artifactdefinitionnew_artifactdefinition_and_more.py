# Generated by Django 5.2 on 2025-04-27 19:24
import uuid

import django.db.models.deletion
from django.db import migrations
from django.db import models


class Migration(migrations.Migration):
    dependencies = [
        ("ontology", "0005_rename_relationshipnew_relationship_and_more"),
        ("ontology_model", "0007_alter_artifactassignmentnew_id"),
    ]

    operations = [
        migrations.RenameModel(
            old_name="ArtifactDefinitionNew",
            new_name="ArtifactDefinition",
        ),
        migrations.RenameModel(
            old_name="RelationshipTypeNew",
            new_name="RelationshipType",
        ),
        migrations.RenameModel(
            old_name="VertexTypeNew",
            new_name="VertexType",
        ),
        migrations.CreateModel(
            name="ArtifactAssignment",
            fields=[
                ("_built", models.BooleanField(default=False)),
                (
                    "id",
                    models.UUIDField(
                        default=uuid.UUID("92ba6350-ae44-4735-8b17-12704f0a7743"),
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("path", models.CharField(blank=True, max_length=255, null=True)),
                (
                    "owner",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="children",
                        to="ontology_model.artifactassignment",
                    ),
                ),
            ],
            options={
                "verbose_name": "артефакт",
                "verbose_name_plural": "артефакты",
            },
        ),
        migrations.DeleteModel(
            name="ArtifactAssignmentNew",
        ),
    ]
