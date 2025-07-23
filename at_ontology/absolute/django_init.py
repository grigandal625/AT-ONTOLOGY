import logging
import os

import django
import dotenv

from at_ontology.core.arguments import ARGS_TO_ENV_MAPPING
from at_ontology.core.arguments import get_args
from at_ontology.utils.settings import get_django_settings_module

dotenv.load_dotenv(".env")

logger = logging.getLogger(__name__)

args = get_args()
for arg_name, arg_value in args.items():
    env_arg_name = ARGS_TO_ENV_MAPPING.get(arg_name)
    if env_arg_name and arg_value:
        os.environ[env_arg_name] = str(arg_value)

settings_module = get_django_settings_module()

os.environ.setdefault("DJANGO_SETTINGS_MODULE", settings_module)
django.setup()
