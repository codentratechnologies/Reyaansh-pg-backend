from django.urls import path
from .views import MemberView, PgAvailabilityView

urlpatterns = [
    path('members', MemberView.as_view(), name='member_api'),
    path('pg/availability', PgAvailabilityView.as_view(), name='pg_availability'),
]
