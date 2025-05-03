from django.db import models
from common.models import TimeStampModel
from helpdesk.choices import TicketStatusOptions,TicketPriorityOptions,TicketGradeOptions,TicketCategoryOptions
from users.models import User


class TicketType(TimeStampModel):
    categoria=models.CharField(max_length=100,choices=TicketCategoryOptions)
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(max_length=500, blank=True, null=True)
    sla = models.IntegerField(max_length=2)

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
    prioridad=models.CharField(choices=TicketPriorityOptions,default=TicketPriorityOptions.BAJA)
    estado=models.CharField(choices=TicketStatusOptions,default=TicketStatusOptions.ABIERTO)
    adjunto=models.FileField(upload_to='tickets/', blank=True, null=True)
    calificacion=models.CharField(choices=TicketGradeOptions,default=TicketGradeOptions.NORMAL)
    close_date=models.DateTimeField(blank=True,null=True)
    tipo = models.ForeignKey(TicketType, on_delete=models.RESTRICT, related_name='tickets')

    class Meta:
        verbose_name = 'Ticket'
        verbose_name_plural = 'Tickets'
        ordering = ['-created_at']

    def __str__(self):
        return f"Ticket #{self.id} - {self.title}"
        
    def save(self, *args, **kwargs):

        if not self.code:
            super(Ticket, self).save(*args, **kwargs)
            self.code = f"#{self.id:05d}"
            super(Ticket, self).save(update_fields=['code'])
        else:
            super(Ticket, self).save(*args, **kwargs)

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


