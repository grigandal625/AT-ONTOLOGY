# Generated by Django 5.2 on 2025-05-13 13:18
import uuid

import django.db.models.deletion
from django.db import migrations
from django.db import models


class Migration(migrations.Migration):
    dependencies = [
        ("ontology", "0005_rename_relationshipnew_relationship_and_more"),
        (
            "ontology_model",
            "0009_remove_artifactdefinition_owner_importdefinition_and_more",
        ),
    ]

    operations = [
        migrations.CreateModel(
            name="RelationshipArtifactAssignment",
            fields=[
                ("_built", models.BooleanField(default=False)),
                (
                    "id",
                    models.UUIDField(
                        default=uuid.UUID("51071152-cd5f-406e-ab6d-c28728f7e139"),
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("path", models.CharField(blank=True, max_length=255, null=True)),
                (
                    "definition",
                    models.ForeignKey(
                        help_text="Используемый ArtifactDefinition",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="definition_relationship_artifact_assignments",
                        to="ontology_model.relationshiptypeartifactdefinition",
                    ),
                ),
                (
                    "owner",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="children",
                        to="ontology.relationshipartifactassignment",
                    ),
                ),
                (
                    "relationship",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="relationship_artifact_assignments",
                        to="ontology.relationship",
                    ),
                ),
                (
                    "relationship_type",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="relationship_type_artifact_assigments",
                        to="ontology_model.relationshiptype",
                    ),
                ),
            ],
            options={
                "verbose_name": "артефакт связи",
                "verbose_name_plural": "артефакты связей",
            },
        ),
        migrations.CreateModel(
            name="RelationshipPropertyAssignment",
            fields=[
                ("_built", models.BooleanField(default=False)),
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        help_text="Уникальный идентификатор (UUID)",
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("value", models.JSONField(help_text="Произвольное значение свойства")),
                (
                    "definition",
                    models.ForeignKey(
                        help_text="Используемый ArtifactDefinition",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="relationship_property_assignments",
                        to="ontology_model.relationshiptypepropertydefinition",
                    ),
                ),
                (
                    "owner",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="children",
                        to="ontology.relationshippropertyassignment",
                    ),
                ),
                (
                    "relationship",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="artifact_assignments",
                        to="ontology.relationship",
                    ),
                ),
                (
                    "relationship_type",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="relationship_type_property_assigments",
                        to="ontology_model.relationshiptype",
                    ),
                ),
            ],
            options={
                "verbose_name": " свойство связи",
                "verbose_name_plural": "свойства связей",
            },
        ),
        migrations.CreateModel(
            name="VertexArtifactAssignment",
            fields=[
                ("_built", models.BooleanField(default=False)),
                (
                    "id",
                    models.UUIDField(
                        default=uuid.UUID("51071152-cd5f-406e-ab6d-c28728f7e139"),
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("path", models.CharField(blank=True, max_length=255, null=True)),
                (
                    "definition",
                    models.ForeignKey(
                        help_text="Используемый ArtifactDefinition",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="vertex_artifact_assignments",
                        to="ontology_model.vertextypeartifactdefinition",
                    ),
                ),
                (
                    "owner",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="children",
                        to="ontology.vertexartifactassignment",
                    ),
                ),
                (
                    "vertex",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="artifact_assignments",
                        to="ontology.vertex",
                    ),
                ),
                (
                    "vertex_type",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="vertex_type_artifact_assigments",
                        to="ontology_model.vertextype",
                    ),
                ),
            ],
            options={
                "verbose_name": "артефакт вершины",
                "verbose_name_plural": "артефакты вершины",
            },
        ),
        migrations.CreateModel(
            name="VertexPropertyAssignment",
            fields=[
                ("_built", models.BooleanField(default=False)),
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        help_text="Уникальный идентификатор (UUID)",
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("value", models.JSONField(help_text="Произвольное значение свойства")),
                (
                    "definition",
                    models.ForeignKey(
                        help_text="Используемый ArtifactDefinition",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="vertex_property_assignments",
                        to="ontology_model.vertextypepropertydefinition",
                    ),
                ),
                (
                    "owner",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="children",
                        to="ontology.vertexpropertyassignment",
                    ),
                ),
                (
                    "vertex",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="property_assignments",
                        to="ontology.vertex",
                    ),
                ),
                (
                    "vertex_type",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="vertex_type_property_assigments",
                        to="ontology_model.vertextype",
                    ),
                ),
            ],
            options={
                "verbose_name": "свойство вершины",
                "verbose_name_plural": "свойства вершин",
            },
        ),
    ]
