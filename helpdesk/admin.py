from django.contrib import admin
from django.contrib.admin  import register
from unfold.admin import ModelAdmin

from .models import Ticket, TicketType, Asignacion, InteraccionTicket, TicketHistory

@register(TicketType)
class TicketType(ModelAdmin):
    list_display=['categoria','nombre','descripcion','sla']
    exclude = ['deleted_at']   