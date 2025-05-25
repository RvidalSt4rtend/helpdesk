from django.db import models
from django.contrib.auth.models import AbstractUser
from .choices import UserTypeOptions
# Create your models here.


class User(AbstractUser):
    dni_usuario = models.CharField(max_length=100, blank=True, null=True,unique=True)
    celular= models.CharField(max_length=100, blank=True, null=True)
    tipo_usuario = models.IntegerField(choices=UserTypeOptions.choices, blank=True, null=True)
    

    def __str__(self):
        return self.username
    
    @classmethod
    def get_agentes_disponibles(cls, grupo=None):
        """
        Retorna una lista de agentes activos (usuarios de tipo soporte)
        Si se especifica un grupo, filtra por usuarios que pertenezcan a ese grupo
        """
        agentes = cls.objects.filter(is_active=True, tipo_usuario=UserTypeOptions.SOPORTE)
        
        if grupo:
            agentes = agentes.filter(groups__name=grupo)
            
        return agentes

