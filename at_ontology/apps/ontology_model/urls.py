from adrf.routers import DefaultRouter
from django.urls import include
from django.urls import path

router = DefaultRouter()

urlpatterns = [
    path(r"ontology_model/", include(router.urls)),
]
