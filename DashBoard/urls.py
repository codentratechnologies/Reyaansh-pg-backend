from django.urls import path
from .views import (
    SetupAdminView, LoginView, LogoutView, ProtectedDataView, RefreshTokenView, 
    AdminDetailsView, DashboardKPIView, DashboardChartsView, DashboardTablesView, DashboardAlertsView,
    SendCalendarReminderView, AdminProfileView, SendRentReminderEmailView, TriggerDailyRemindersView,
    GeneratePaymentLinkView, SubmitPaymentProofView
)

urlpatterns = [
    path('setup-admin/', SetupAdminView.as_view(), name='setup_admin'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('refresh/', RefreshTokenView.as_view(), name='refresh_token'),
    path('protected-data/', ProtectedDataView.as_view(), name='protected_data'),
    path('admin-details/', AdminDetailsView.as_view(), name='admin_details'),
    path('admin-profile/', AdminProfileView.as_view(), name='admin_profile'),
    path('dashboard-kpis/', DashboardKPIView.as_view(), name='dashboard_kpis'),
    path('dashboard-charts/', DashboardChartsView.as_view(), name='dashboard_charts'),
    path('dashboard-tables/', DashboardTablesView.as_view(), name='dashboard_tables'),
    path('dashboard-alerts/', DashboardAlertsView.as_view(), name='dashboard_alerts'),
    path('send-calendar-reminder/', SendCalendarReminderView.as_view(), name='send_calendar_reminder'),
    path('send-rent-email/', SendRentReminderEmailView.as_view(), name='send_rent_email'),
    path('trigger-daily-reminders/', TriggerDailyRemindersView.as_view(), name='trigger_daily_reminders'),
    path('generate-payment-link/', GeneratePaymentLinkView.as_view(), name='generate_payment_link'),
    path('submit-payment-proof/', SubmitPaymentProofView.as_view(), name='submit_payment_proof'),
]
