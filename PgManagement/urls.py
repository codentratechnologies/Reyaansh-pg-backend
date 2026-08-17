from django.urls import path
from .views import AddPgPropertyView, GetStatesView, GetCitiesView

urlpatterns = [
    path('addpg/', AddPgPropertyView.as_view(), name='add_pg_property'),
    path('states/', GetStatesView.as_view(), name='get_states'),
    path('cities/', GetCitiesView.as_view(), name='get_cities'),
]
