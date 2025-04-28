from django.urls import path
from .controller import run_irrigation_system

urlpatterns = [
    path('run/', run_irrigation_system),
]
