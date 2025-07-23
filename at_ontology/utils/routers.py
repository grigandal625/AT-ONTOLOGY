from adrf.routers import SimpleRouter
from rest_framework_nested.routers import NestedMixin


class AsyncNestedRouter(NestedMixin, SimpleRouter):
    """
    Асинхронный вложенный роутер, совместимый с adrf.routers.Router.
    """
