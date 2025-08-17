from django.contrib.admin  import register
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from unfold.admin import ModelAdmin
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm
from .models import *
# Register your models here.

@register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    # Definir los campos para el formulario de creación de usuarios
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'username', 'dni_usuario', 'password1', 'password2', 'email',
                'first_name', 'last_name', 'celular', 'tipo_usuario', 'groups'
            ),
        }),
    )

    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm

    def get_fieldsets(self, request, obj=None):
        # Obtén los fieldsets originales
        fieldsets = list(super().get_fieldsets(request, obj))
        if obj:  # Si estamos editando
            # Elimina el fieldset de permisos
            fieldsets = [fs for fs in fieldsets if fs[0] != 'Permissions']
            # Agrega tus campos personalizados en un nuevo fieldset
            fieldsets.append(
                (None, {'fields': (
                    'dni_usuario', 'celular', 'tipo_usuario', 'groups'
                )})
            )
        return fieldsets
