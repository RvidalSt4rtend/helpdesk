from django.utils.translation import gettext_lazy as _
from django.db import models

class UserTypeOptions(models.IntegerChoices):
    ADMINISTRADOR = 1, _("Administrador")
    SOPORTE = 2, _("Soporte")
    CLIENTE = 3, _("Cliente")

