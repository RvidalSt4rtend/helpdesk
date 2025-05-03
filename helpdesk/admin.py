from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from unfold.admin import ModelAdmin, TabularInline
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm
from unfold.sites import UnfoldAdminSite
from django.contrib.auth.admin import UserAdmin
from users.models import User

from .models import Ticket, TicketType, Asignacion, InteraccionTicket, TicketHistory

# Registramos nuestro admin personalizado
admin_site = UnfoldAdminSite(name="helpdesk_admin")


# Inlines para mostrar información relacionada
class AsignacionInline(TabularInline):
    model = Asignacion
    extra = 0
    fields = ('agente', 'solicitante', 'created_at')
    readonly_fields = ('created_at',)


class InteraccionTicketInline(TabularInline):
    model = InteraccionTicket
    extra = 0
    fields = ('usuario', 'mensaje', 'es_agente', 'created_at')
    readonly_fields = ('created_at',)


class TicketHistoryInline(TabularInline):
    model = TicketHistory
    extra = 0
    fields = ('usuario', 'campo_modificado', 'valor_anterior', 'valor_nuevo', 'descripcion', 'created_at')
    readonly_fields = ('usuario', 'campo_modificado', 'valor_anterior', 'valor_nuevo', 'descripcion', 'created_at')
    can_delete = False
    max_num = 0


@admin.register(Ticket, site=admin_site)
class TicketAdmin(ModelAdmin):
    list_display = ('code', 'title', 'tipo', 'estado_colored', 'prioridad_colored', 'calificacion', 'get_agente', 'get_solicitante', 'created_at')
    list_filter = ('estado', 'prioridad', 'tipo', 'calificacion', 'created_at')
    search_fields = ('code', 'title', 'description')
    date_hierarchy = 'created_at'
    readonly_fields = ('code', 'created_at', 'updated_at')
    inlines = [AsignacionInline, InteraccionTicketInline, TicketHistoryInline]
    
    fieldsets = (
        ('Información General', {
            'fields': ('code', 'title', 'description', 'tipo')
        }),
        ('Estado y Prioridad', {
            'fields': ('estado', 'prioridad', 'calificacion')
        }),
        ('Archivos', {
            'fields': ('adjunto',)
        }),
        ('Fechas', {
            'fields': ('created_at', 'updated_at', 'close_date')
        }),
    )
    
    def get_agente(self, obj):
        asignacion = obj.asignaciones.first()
        if asignacion:
            return asignacion.agente.username
        return "-"
    get_agente.short_description = 'Agente'
    
    def get_solicitante(self, obj):
        asignacion = obj.asignaciones.first()
        if asignacion:
            return asignacion.solicitante.username
        return "-"
    get_solicitante.short_description = 'Solicitante'
    
    def estado_colored(self, obj):
        colors = {
            'ABIERTO': 'bg-yellow-100 text-yellow-800',
            'EN_PROGRESO': 'bg-blue-100 text-blue-800',
            'RESUELTO': 'bg-green-100 text-green-800',
            'CERRADO': 'bg-gray-100 text-gray-800',
            'ESPERANDO_RESPUESTA': 'bg-purple-100 text-purple-800',
        }
        
        return format_html(
            '<span class="px-2 py-1 rounded-full {}">{}</span>',
            colors.get(obj.estado, ''),
            obj.get_estado_display()
        )
    estado_colored.short_description = 'Estado'
    
    def prioridad_colored(self, obj):
        colors = {
            'ALTA': 'bg-red-100 text-red-800',
            'MEDIA': 'bg-orange-100 text-orange-800',
            'BAJA': 'bg-green-100 text-green-800',
            'URGENTE': 'bg-red-300 text-red-900',
        }
        
        return format_html(
            '<span class="px-2 py-1 rounded-full {}">{}</span>',
            colors.get(obj.prioridad, ''),
            obj.get_prioridad_display()
        )
    prioridad_colored.short_description = 'Prioridad'
    
    def save_model(self, request, obj, form, change):
        # Guardamos el modelo original
        super().save_model(request, obj, form, change)
        
        if change:  # Si se está actualizando un objeto existente
            # Obtenemos el objeto original
            old_obj = Ticket.objects.get(pk=obj.pk)
            
            # Verificamos los campos que han cambiado
            changed_fields = []
            for field in ['title', 'description', 'prioridad', 'estado', 'calificacion']:
                old_value = getattr(old_obj, field)
                new_value = getattr(obj, field)
                
                if old_value != new_value:
                    # Registramos el cambio en el historial
                    TicketHistory.registrar_cambio(
                        ticket=obj,
                        usuario=request.user,
                        campo=field,
                        valor_anterior=old_value,
                        valor_nuevo=new_value,
                        descripcion=f"Cambio de {field} de {old_value} a {new_value}"
                    )
    
    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for instance in instances:
            if isinstance(instance, InteraccionTicket):
                # Comprobamos si el usuario es un agente
                if hasattr(request.user, 'is_staff') and request.user.is_staff:
                    instance.es_agente = True
                instance.usuario = request.user
            instance.save()
        formset.save_m2m()


@admin.register(TicketType, site=admin_site)
class TicketTypeAdmin(ModelAdmin):
    list_display = ('nombre', 'categoria', 'sla', 'created_at')
    list_filter = ('categoria',)
    search_fields = ('nombre', 'descripcion')
    fields = ('nombre', 'categoria', 'descripcion', 'sla', 'created_at', 'updated_at')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Asignacion, site=admin_site)
class AsignacionAdmin(ModelAdmin):
    list_display = ('ticket', 'agente', 'solicitante', 'created_at')
    list_filter = ('agente', 'solicitante')
    search_fields = ('ticket__title', 'agente__username', 'solicitante__username')
    fields = ('ticket', 'agente', 'solicitante', 'created_at', 'updated_at')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(InteraccionTicket, site=admin_site)
class InteraccionTicketAdmin(ModelAdmin):
    list_display = ('ticket', 'usuario', 'mensaje_preview', 'es_agente', 'created_at')
    list_filter = ('es_agente', 'created_at', 'usuario')
    search_fields = ('ticket__title', 'usuario__username', 'mensaje')
    fields = ('ticket', 'usuario', 'mensaje', 'es_agente', 'created_at', 'updated_at')
    readonly_fields = ('created_at', 'updated_at')
    
    def mensaje_preview(self, obj):
        return obj.mensaje[:50] + '...' if len(obj.mensaje) > 50 else obj.mensaje
    mensaje_preview.short_description = 'Mensaje'


@admin.register(TicketHistory, site=admin_site)
class TicketHistoryAdmin(ModelAdmin):
    list_display = ('ticket', 'usuario', 'campo_modificado', 'valor_anterior_preview', 'valor_nuevo_preview', 'created_at')
    list_filter = ('campo_modificado', 'usuario', 'created_at')
    search_fields = ('ticket__title', 'usuario__username', 'descripcion')
    fields = ('ticket', 'usuario', 'campo_modificado', 'valor_anterior', 'valor_nuevo', 'descripcion', 'created_at', 'updated_at')
    readonly_fields = ('ticket', 'usuario', 'campo_modificado', 'valor_anterior', 'valor_nuevo', 'descripcion', 'created_at', 'updated_at')
    
    def valor_anterior_preview(self, obj):
        return obj.valor_anterior[:30] + '...' if obj.valor_anterior and len(obj.valor_anterior) > 30 else obj.valor_anterior
    valor_anterior_preview.short_description = 'Valor Anterior'
    
    def valor_nuevo_preview(self, obj):
        return obj.valor_nuevo[:30] + '...' if obj.valor_nuevo and len(obj.valor_nuevo) > 30 else obj.valor_nuevo
    valor_nuevo_preview.short_description = 'Valor Nuevo'

