from django.urls import path
from .views import *

app_name = 'users'

urlpatterns = [
    path('login', login_view, name='login'),
    path('logout', logout_view, name='logout'),
] 
