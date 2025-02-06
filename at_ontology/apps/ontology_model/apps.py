from django.apps import AppConfig


class OntologyModelConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "at_ontology.apps.ontology_model"
    label = "ontology_model"
    verbose_name = "Модель онтологии"
