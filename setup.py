import os
import shutil

from setuptools import setup
from setuptools.command.install import install


class PostInstallCommand(install):
    def run(self):
        install.run(self)

        base_server_path = os.path.join(os.path.dirname(__file__), "at_ontology", "base_server")

        if "base_server" in self.distribution.extras_require:
            dest = os.path.join(os.getcwd(), "base_server")
            shutil.copytree(base_server_path, dest)
            print(f"Django project template copied to {dest}")
        else:
            if os.path.exists(base_server_path):
                shutil.rmtree(base_server_path)
                print(f"Deleted {base_server_path} because 'base_server' extra was not specified.")


setup(
    cmdclass={
        "install": PostInstallCommand,
    },
)
