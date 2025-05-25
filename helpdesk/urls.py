from django.urls import path
from .views import *

app_name = 'helpdesk'

urlpatterns = [
    path('', index_view, name='home'),
    path('dashboard/', dashboard_view, name='dashboard'),
    path('reportes/', reports_view, name='reports'),
    path('tickets/', ticket_list, name='ticket_list'),
    path('nuevo/', ticket_create, name='ticket_create'),
    path('<int:pk>/', ticket_detail, name='ticket_detail'),
    path('<int:pk>/editar/', ticket_update, name='ticket_update'),
    path('<int:pk>/cerrar/', ticket_close, name='ticket_close'),
    path('<int:pk>/resolver/', ticket_resolve, name='ticket_resolve'),
    path('<int:pk>/calificar/', ticket_rate, name='ticket_rate'),
    path('<int:pk>/reabrir/', ticket_reopen, name='ticket_reopen'),
]
