from django.contrib.admin  import register
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from unfold.admin import ModelAdmin
from unfold.forms import AdminOwnPasswordChangeForm,UserChangeForm,UserCreationForm
from .models import *
# Register your models here.

@register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    # Definir los campos para el formulario de creación de usuarios
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username','dni_usuario','categoria' ,'password1', 'password2', 'email', 'first_name', 'last_name','celular'),
        }),
    )

    # Definir los campos para el formulario de edición de usuarios
    fieldsets = BaseUserAdmin.fieldsets + (
        (None, {'fields': ('dni_usuario','celular')}),  # Agrega tu campo personalizado aquí
    )
    form=UserChangeForm
    add_form=UserCreationForm
    change_password_form=AdminOwnPasswordChangeForm