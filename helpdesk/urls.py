from django.urls import path
from .views import *

app_name = 'helpdesk'

urlpatterns = [
    path('', index_view, name='home'),
]
