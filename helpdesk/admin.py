from django.contrib import admin
from django.contrib.admin  import register
from unfold.admin import ModelAdmin

from .models import Ticket, TicketType, Asignacion, InteraccionTicket, TicketHistory

@register(TicketType)
class TicketType(ModelAdmin):
    list_display = ['categoria', 'nombre', 'descripcion', 'sla_horas', 'grupo_soporte']
    exclude = ['deleted_at']
    
    def sla_horas(self, obj):
        return f"{obj.sla} horas"
    sla_horas.short_description = "SLA (horas)"
    
@register(Ticket)
class TicketAdmin(ModelAdmin):
    list_display = ['code', 'title', 'tipo', 'prioridad', 'estado', 'created_at']
    list_filter = ['estado', 'prioridad', 'tipo', 'created_at']
    search_fields = ['code', 'title', 'description']
    readonly_fields = ['code', 'close_date']
    exclude = ['deleted_at']
    
@register(Asignacion)
class AsignacionAdmin(ModelAdmin):
    list_display = ['ticket', 'agente', 'solicitante', 'created_at']
    list_filter = ['agente', 'created_at']
    search_fields = ['ticket__code', 'ticket__title', 'agente__username', 'solicitante__username']
    exclude = ['deleted_at']
    
@register(InteraccionTicket)
class InteraccionTicketAdmin(ModelAdmin):
    list_display = ['ticket', 'usuario', 'es_agente', 'created_at']
    list_filter = ['es_agente', 'created_at']
    search_fields = ['ticket__code', 'ticket__title', 'usuario__username', 'mensaje']
    exclude = ['deleted_at']
    
@register(TicketHistory)
class TicketHistoryAdmin(ModelAdmin):
    list_display = ['ticket', 'usuario', 'campo_modificado', 'created_at']
    list_filter = ['campo_modificado', 'created_at']
    search_fields = ['ticket__code', 'ticket__title', 'usuario__username', 'descripcion']
    readonly_fields = ['ticket', 'usuario', 'campo_modificado', 'valor_anterior', 'valor_nuevo', 'descripcion']
    exclude = ['deleted_at']   