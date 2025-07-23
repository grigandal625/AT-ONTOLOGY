import asyncio
import logging
import os
from typing import Tuple

from at_queue.core.session import ConnectionParameters
from django.core import management
from django.core.asgi import get_asgi_application
from uvicorn import Config
from uvicorn import Server

from at_ontology.absolute.django_init import args
from at_ontology.absolute.django_init import get_args
from at_ontology.core.component import ATOntology

logger = logging.getLogger(__name__)


django_application = get_asgi_application()


def get_component(args: dict = None) -> Tuple[ATOntology, dict]:
    args = args or get_args()
    connection_parameters = ConnectionParameters(**args)

    try:
        if not os.path.exists("/var/run/at_ontology/"):
            os.makedirs("/var/run/at_ontology/")

        with open("/var/run/at_ontology/pidfile.pid", "w") as f:
            f.write(str(os.getpid()))
    except PermissionError:
        pass

    return ATOntology(connection_parameters), args


async def main_with_django(args: dict = None):
    component, args = get_component(args=args)
    server_host = args.pop("server_host", "localhost")
    server_port = args.pop("server_port", 8000)

    async def lifespan(app):
        """Пользовательский lifespan для управления asyncio жизненным циклом веб-приложения."""
        logging.basicConfig(level=logging.INFO)

        await component.initialize()
        await component.register()

        loop = asyncio.get_event_loop()
        loop.create_task(component.start())

        yield  # Приложение запущено

    # Обертываем Django-приложение с пользовательским lifespan
    async def app(scope, receive, send):
        if scope["type"] == "lifespan":
            # Обработка событий lifespan
            while True:
                message = await receive()
                if message["type"] == "lifespan.startup":
                    # Запуск lifespan
                    async for _ in lifespan(None):
                        pass
                    await send({"type": "lifespan.startup.complete"})
                elif message["type"] == "lifespan.shutdown":
                    # Завершение lifespan
                    await send({"type": "lifespan.shutdown.complete"})
                    break
        else:
            # Обработка HTTP-запросов через Django
            await django_application(scope, receive, send)

    # Конфигурация и запуск сервера Uvicorn
    config = Config(
        app=app,  # Передаем обернутое ASGI-приложение
        host=server_host,
        port=server_port,
        lifespan="on",  # Включаем поддержку lifespan
    )
    server = Server(config=config)
    await server.serve()


if __name__ == "__main__":
    management.call_command("migrate")
    try:
        management.call_command("createsuperuser", "--no-input")
    except management.base.CommandError:
        pass
    asyncio.run(main_with_django(args=args))
