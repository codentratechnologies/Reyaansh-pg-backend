from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('DashBoard.urls')),
    path('api/', include('PgManagement.urls')),
    path('api/', include('PgMembers.urls')),
]
