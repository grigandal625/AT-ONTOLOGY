import os
import re
import subprocess
import sys


def get_django_settings_module() -> str:
    # Поиск директории с manage.py
    def find_manage_dir() -> str:
        current_dir = os.path.abspath(os.getcwd())
        while True:
            manage_path = os.path.join(current_dir, "manage.py")
            if os.path.isfile(manage_path):
                return current_dir
            parent_dir = os.path.dirname(current_dir)
            if parent_dir == current_dir:
                return None
            current_dir = parent_dir

    manage_dir = find_manage_dir()
    if not manage_dir:
        try:
            __import__("at_ontology.base_server.settings")
            return "at_ontology.base_server.settings"
        except ImportError:
            return None

    command = " ".join([sys.executable, os.path.join(manage_dir, "manage.py"), "get_settings_module"])
    process = subprocess.Popen(
        command,
        shell=True,
        stdout=subprocess.PIPE,
    )

    process.wait()

    command_result = process.stdout.read().decode()
    index = -1
    while not re.match(r"\w", command_result[index]):
        index -= 1
    if index < -1:
        result = command_result[: index + 1]
    else:
        result = command_result

    return result
