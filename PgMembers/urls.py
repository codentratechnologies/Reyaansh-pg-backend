from django.urls import path
from .views import MemberView

urlpatterns = [
    path('members', MemberView.as_view(), name='member_api'),
]
