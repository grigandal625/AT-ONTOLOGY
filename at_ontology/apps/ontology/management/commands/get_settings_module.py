import os

from django.core.management import BaseCommand


class Command(BaseCommand):
    def check(self, *args, **kwargs):
        return True

    def handle(self, *args, **kwargs):
        result = os.getenv("DJANGO_SETTINGS_MODULE")
        if result == "":
            result = os.environ.get("DJANGO_SETTINGS_MODULE")

        return result
