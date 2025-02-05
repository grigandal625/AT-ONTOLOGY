from django.db import models

# Create your models here.


class ValueContainedEntity(models.Model):
    value = models.JSONField(verbose_name="значение", null=True, blank=True)

    class Meta:
        verbose_name = "значение сущности"
        verbose_name_plural = "значения сущностей"
        abstract = True


class File(models.Model):
    name = models.CharField(max_length=255, verbose_name="Имя")
    content = models.FileField(verbose_name="содержимое")

    class Meta:
        verbose_name = "файл"
        verbose_name_plural = "файлы"

    def __str__(self):
        return self.name


class Vertex(models.Model):
    name = models.CharField(max_length=255, verbose_name="имя")
    description = models.TextField(null=True, blank=True, verbose_name="описание")
    type = models.ForeignKey("ontology_model.VertexType", on_delete=models.RESTRICT, verbose_name="тип вершины")
    files = models.ManyToManyField(File, verbose_name="Файлы", blank=True)

    class Meta:
        verbose_name = "вершина"
        verbose_name_plural = "вершины"

    def __str__(self):
        return f"{self.name} ({self.type})"


class VertexPropertyAssignments(ValueContainedEntity):
    vertex = models.ForeignKey(Vertex, on_delete=models.CASCADE, verbose_name="вершина", related_name="properties")
    property = models.ForeignKey(
        "ontology_model.VertexTypePropertyDefinition",
        on_delete=models.CASCADE,
        verbose_name="исходное свойство типа вершины",
    )

    class Meta:
        verbose_name = "присвоенное значение свойства вершины"
        verbose_name_plural = "присвоенные значения свойств вершин"

    def __str__(self):
        return f"{self.vertex.name}.{self.property.name}"


class Relationship(models.Model):
    source = models.ForeignKey(
        Vertex, on_delete=models.CASCADE, verbose_name="родительская вершина", related_name="output_relations"
    )
    target = models.ForeignKey(
        Vertex, on_delete=models.CASCADE, verbose_name="дочерняя вершина", related_name="input_relations"
    )
    type = models.ForeignKey(
        "ontology_model.RelationshipType",
        on_delete=models.RESTRICT,
        verbose_name="тип связи",
    )
    name = models.CharField(max_length=255, null=True, blank=True, verbose_name="имя")
    description = models.TextField(null=True, blank=True, verbose_name="описание")
    files = models.ManyToManyField(File, verbose_name="файлы", blank=True)

    class Meta:
        verbose_name = "связь"
        verbose_name_plural = "связи"

    def __str__(self):
        if self.name:
            return f"{self.name} - {self.type}"
        return str(self.type)


class RelationshipPropertyAssignments(ValueContainedEntity):
    relationship = models.ForeignKey(
        Relationship, on_delete=models.CASCADE, verbose_name="связь", related_name="properties"
    )
    property = models.ForeignKey(
        "ontology_model.RelationshipTypePropertyDefinition",
        on_delete=models.CASCADE,
        verbose_name="исходное свойство типа связи",
    )

    class Meta:
        verbose_name = "присвоенное значение свойства связи"
        verbose_name_plural = "присвоенные значения свойств связей"

    def __str__(self):
        return f"{self.relationship.name}.{self.property.name}"
