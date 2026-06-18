from pathlib import Path
import yaml
from django.test import TestCase

from at_ontology.apps.ontology.management.commands.load_from_legacy_db import LegacyService
from at_ontology.apps.ontology_model.management.commands.load_ontology_model import Command as LoadOntologyModel

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
DB_PATH = FIXTURES_DIR / "legacy_db" / "development_new01.06.sqlite3"
OUT_DIR = FIXTURES_DIR / "exported_ontologies"

TARGET_NAMES = {
    "Введение в интеллектуальные системы",
    "Технология построения динамических интеллектуальных систем",
}


def slugify_name(name: str) -> str:
    safe = name.replace(" ", "_").replace("/", "-").replace("\\", "-")
    return "".join(c for c in safe if c.isalnum() or c in "_-")


class ExportOntologyToYamlTest(TestCase):

    def setUp(self):
        LoadOntologyModel().handle(file=str(FIXTURES_DIR / "normative-types/types.mdl.yaml"))
        LoadOntologyModel().handle(file=str(FIXTURES_DIR / "applied-types/types.mdl.yaml"))
        return super().setUp()

    def test_export_ontologies_to_yaml(self):
        OUT_DIR.mkdir(parents=True, exist_ok=True)

        service = LegacyService(DB_PATH)
        root_topics = service.root_ka_topics()

        found = []
        for root_topic in root_topics:
            if root_topic.text not in TARGET_NAMES:
                continue

            print(f"\nСбор: {root_topic.text!r}")
            ontology_source = service.get_ontology_source(root_topic)

            file_name = slugify_name(root_topic.text) + ".yaml"
            out_path = OUT_DIR / file_name

            with open(out_path, "w", encoding="utf-8") as f:
                yaml.dump(
                    ontology_source,
                    f,
                    default_flow_style=False,
                    allow_unicode=True,
                    sort_keys=False,
                )

            print(f"Сохранено: {out_path}")
            self.assertTrue(out_path.exists(), f"Файл не создан: {out_path}")
            found.append(root_topic.text)

        missing = TARGET_NAMES - set(found)
        self.assertEqual(
            missing, set(),
            f"Не найдены в БД: {missing}"
        )