from adrf.routers import DefaultRouter
from django.urls import include
from django.urls import path

from at_ontology.apps.ontology import views

router = DefaultRouter()

router.register(r"vertices", views.VertexViewSet, basename="vertices")

urlpatterns = [
    path(r"ontology/", include(router.urls)),
]
