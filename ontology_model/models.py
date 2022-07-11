from django.db import models
from django.utils.translation import gettext_lazy as _

# Create your models here.


class ElementType(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)

    class Meta:
        verbose_name = 'Тип элемента'
        verbose_name_plural = 'Типы элементов'


class ReflexivityChoices(models.IntegerChoices):
    reflexive = 1, _('Рефлексивно')
    antireflexive = 2, _('Антирефлексивно')
    __empty__ = _('Не указано')


class SymmetryChoices(models.IntegerChoices):
    symmetric = 1, _('Симментрично')
    antisymmetric = 2, _('Антисиметрично')
    __empty__ = _('Не указано')


class TransitivityChoices(models.IntegerChoices):
    transitive = 1, _('Транзитивно')
    intransitive = 2, _('Интранзитивно')


class RelationType(models.Model):
    name = models.CharField(max_length=255, verbose_name="Имя")
    description = models.TextField(
        null=True, blank=True, verbose_name="Описание")

    default_reflexivity = models.IntegerField(
        blank=True, null=True, default=None, choices=ReflexivityChoices.choices, verbose_name="Рефлексивность по умолчанию")
    default_symmetry = models.IntegerField(
        blank=True, null=True, default=None, choices=SymmetryChoices.choices, verbose_name="Симметричность по умолчанию")
    default_transitivity = models.IntegerField(
        choices=TransitivityChoices.choices, default=TransitivityChoices.intransitive, verbose_name="Транзитивность по умолчанию")

    class Meta:
        verbose_name = 'Тип связи'
        verbose_name_plural = 'Типы связей'
