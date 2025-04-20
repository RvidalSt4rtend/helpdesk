from django.shortcuts import render,redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpResponse
from .forms import LoginForm

from urllib.parse import urlparse

def login_view(request):
    context ={ 'form': LoginForm()}
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('helpdesk:home')
            else:
                return HttpResponse(status=401)
        else:
            context['form'] = form
    return render(request, 'Login/Login.html', context)

def logout_view(request):
    logout(request)
    return redirect('users:login')
