from django.urls import path, include

urlpatterns = [
    path('irrigation/', include('irrigation.urls')),
]
