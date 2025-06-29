from django.db import models
from common.models import TimeStampModel
from helpdesk.choices import TicketStatusOptions,TicketPriorityOptions,TicketGradeOptions,TicketCategoryOptions
from users.models import User
from django.db.models import Count
from django.contrib.auth.models import Group
import random


class TicketType(TimeStampModel):
    categoria=models.IntegerField(choices=TicketCategoryOptions)
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(max_length=500, blank=True, null=True)
    sla = models.IntegerField("SLA", help_text="El SLA está expresado en horas", max_length=2)
    grupo_soporte = models.ForeignKey(Group, on_delete=models.SET_NULL, related_name='tipos_ticket', null=True, blank=True, verbose_name='Grupo de soporte asignado')

    class Meta:
        verbose_name = 'Tipo de Ticket'
        verbose_name_plural = 'Tipos de Tickets'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre

# Create your models here.
class Ticket(TimeStampModel):
    code=models.CharField(max_length=10, unique=True, blank=True, null=True)
    title=models.CharField(max_length=100)
    description=models.TextField(max_length=800,blank=True,null=True)
    prioridad=models.IntegerField(choices=TicketPriorityOptions,default=TicketPriorityOptions.BAJA)
    estado=models.IntegerField(choices=TicketStatusOptions,default=TicketStatusOptions.ABIERTO)
    adjunto=models.FileField(upload_to='tickets/', blank=True, null=True)
    calificacion=models.IntegerField(choices=TicketGradeOptions,default=TicketGradeOptions.NORMAL)
    close_date=models.DateTimeField(blank=True,null=True)
    tipo = models.ForeignKey(TicketType, on_delete=models.RESTRICT, related_name='tickets')

    class Meta:
        verbose_name = 'Ticket'
        verbose_name_plural = 'Tickets'
        ordering = ['-created_at']

    def __str__(self):
        return f"Ticket #{self.id} - {self.title}"
        
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        
        # Guardar el estado anterior para detectar cambios
        if not is_new:
            old_instance = Ticket.objects.get(pk=self.pk)
            old_estado = old_instance.estado
            old_calificacion = old_instance.calificacion
        
        # Guardar primero para generar un ID si es nuevo
        if not self.code:
            super(Ticket, self).save(*args, **kwargs)
            self.code = f"#{self.id:05d}"
            super(Ticket, self).save(update_fields=['code'])
        else:
            super(Ticket, self).save(*args, **kwargs)
        
        # Asignar automáticamente si es un ticket nuevo y hay un usuario actual
        if is_new and hasattr(self, 'usuario_actual'):
            self.asignar_automaticamente(self.usuario_actual)
        
        # Registrar cambios si no es nuevo
        if not is_new and hasattr(self, 'usuario_actual'):
            # Registrar cambio de estado si hubo cambio
            if old_estado != self.estado:
                TicketHistory.registrar_cambio(
                    ticket=self,
                    usuario=self.usuario_actual,
                    campo='estado',
                    valor_anterior=old_instance.get_estado_display(),
                    valor_nuevo=self.get_estado_display(),
                    descripcion=f"Cambio de estado de {old_instance.get_estado_display()} a {self.get_estado_display()}"
                )
            
            # Registrar calificación si fue calificado
            if old_calificacion != self.calificacion and self.calificacion != TicketGradeOptions.NORMAL:
                TicketHistory.registrar_cambio(
                    ticket=self,
                    usuario=self.usuario_actual,
                    campo='calificacion',
                    valor_anterior=old_instance.get_calificacion_display(),
                    valor_nuevo=self.get_calificacion_display(),
                    descripcion=f"Ticket calificado con {self.get_calificacion_display()}"
                )
    
    def asignar_automaticamente(self, solicitante):
        """
        Asigna automáticamente el ticket a un agente del grupo correspondiente
        utilizando una estrategia de balanceo de carga
        
        Args:
            solicitante: Usuario que creó el ticket
        """
        if not self.tipo or not self.tipo.grupo_soporte:
            return False
        
        # Obtener el nombre del grupo de soporte
        nombre_grupo = self.tipo.grupo_soporte.name
        
        # Obtener agentes disponibles para este grupo
        agentes = User.get_agentes_disponibles(grupo=nombre_grupo)
        
        if not agentes.exists():
            return False
        
        # Estrategia: asignar al agente con menos tickets abiertos
        agentes_con_carga = agentes.annotate(
            total_tickets=Count('tickets_asignados', filter=models.Q(
                tickets_asignados__ticket__estado=TicketStatusOptions.ABIERTO) | 
                models.Q(tickets_asignados__ticket__estado=TicketStatusOptions.REABIERTO)
            )
        ).order_by('total_tickets')
        
        # Si hay empate, elegir aleatoriamente entre los que tienen menos carga
        min_carga = agentes_con_carga.first().total_tickets
        agentes_menos_cargados = agentes_con_carga.filter(total_tickets=min_carga)
        agente_seleccionado = random.choice(list(agentes_menos_cargados))
        
        # Crear la asignación
        Asignacion.objects.create(
            ticket=self,
            agente=agente_seleccionado,
            solicitante=solicitante
        )
        
        # Registrar en historial
        TicketHistory.registrar_cambio(
            ticket=self,
            usuario=solicitante,
            campo='asignacion',
            valor_anterior='',
            valor_nuevo=agente_seleccionado.username,
            descripcion=f"Ticket asignado automáticamente a {agente_seleccionado.username}"
        )
        
        return True

class Asignacion(TimeStampModel):
    ticket = models.ForeignKey(Ticket, on_delete=models.RESTRICT, related_name='asignaciones')
    agente = models.ForeignKey(User, on_delete=models.RESTRICT, related_name='tickets_asignados')
    solicitante = models.ForeignKey(User, on_delete=models.RESTRICT, related_name='tickets_solicitados')

    class Meta:
        verbose_name = 'Asignación'
        verbose_name_plural = 'Asignaciones'
        ordering = ['-created_at']

    def __str__(self):
        return f"Asignación de {self.ticket.title} - Agente: {self.agente.username}"

class InteraccionTicket(TimeStampModel):
    ticket = models.ForeignKey(Ticket, on_delete=models.RESTRICT, related_name='interacciones')
    usuario = models.ForeignKey(User, on_delete=models.RESTRICT, related_name='mensajes_enviados')
    mensaje = models.TextField(max_length=1000)
    es_agente = models.BooleanField(default=False)  # Para identificar si el mensaje lo envió un agente o un usuario

    class Meta:
        ordering = ['created_at']  # Ordenar por fecha de creación
        verbose_name = 'Interacción de Ticket'
        verbose_name_plural = 'Interacciones de Tickets'

    def __str__(self):
        return f"Mensaje de {self.usuario.username} en ticket {self.ticket.id}"

class TicketHistory(TimeStampModel):
    ticket = models.ForeignKey(Ticket, on_delete=models.RESTRICT, related_name='historial')
    usuario = models.ForeignKey(User, on_delete=models.RESTRICT, related_name='cambios_realizados')
    campo_modificado = models.CharField(max_length=50)  # Nombre del campo que se modificó
    valor_anterior = models.TextField(blank=True, null=True)  # Valor anterior del campo
    valor_nuevo = models.TextField(blank=True, null=True)  # Nuevo valor del campo
    descripcion = models.TextField(max_length=500, blank=True, null=True)  # Descripción opcional del cambio


    class Meta:
        verbose_name = 'Historial de Ticket'
        verbose_name_plural = 'Historial de Tickets'
        ordering = ['-created_at']

    def __str__(self):
        return f"Cambio en {self.ticket.code} - {self.campo_modificado} por {self.usuario.username}"

    @classmethod
    def registrar_cambio(cls, ticket, usuario, campo, valor_anterior, valor_nuevo, descripcion=None):
        """
        Método de clase para registrar un cambio en el historial del ticket
        """
        return cls.objects.create(
            ticket=ticket,
            usuario=usuario,
            campo_modificado=campo,
            valor_anterior=str(valor_anterior),
            valor_nuevo=str(valor_nuevo),
            descripcion=descripcion
        )


