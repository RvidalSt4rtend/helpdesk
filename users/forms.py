from django import forms
from django.contrib.auth import authenticate


class LoginForm(forms.Form):
    username = forms.CharField(max_length=100)
    password = forms.CharField(max_length=100)  
    
    password = forms.CharField(widget=forms.PasswordInput)

    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        if username and password:
            self.user = authenticate(username=username, password=password)
            if self.user is not None:
                if not self.user.is_active:
                    raise forms.ValidationError('Cuenta Desactivada')
            else:
                raise forms.ValidationError('Credenciales Incorrectas')
            

