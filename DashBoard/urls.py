from django.urls import path
from .views import (
    SetupAdminView, LoginView, LogoutView, ProtectedDataView, RefreshTokenView, 
    AdminDetailsView, DashboardKPIView, DashboardChartsView, DashboardTablesView, DashboardAlertsView,
    TestNotificationView
)

urlpatterns = [
    path('setup-admin/', SetupAdminView.as_view(), name='setup_admin'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('refresh/', RefreshTokenView.as_view(), name='refresh_token'),
    path('protected-data/', ProtectedDataView.as_view(), name='protected_data'),
    path('admin-details/', AdminDetailsView.as_view(), name='admin_details'),
    path('dashboard-kpis/', DashboardKPIView.as_view(), name='dashboard_kpis'),
    path('dashboard-charts/', DashboardChartsView.as_view(), name='dashboard_charts'),
    path('dashboard-tables/', DashboardTablesView.as_view(), name='dashboard_tables'),
    path('dashboard-alerts/', DashboardAlertsView.as_view(), name='dashboard_alerts'),
    path('test-notification/', TestNotificationView.as_view(), name='test_notification'),
]
