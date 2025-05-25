from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, get_object_or_404, redirect
from .models import Ticket, TicketHistory, TicketStatusOptions, TicketGradeOptions, Asignacion, TicketType
from .forms import TicketForm, TicketUpdateForm, InteraccionTicketForm, ClienteTicketUpdateForm
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.http import HttpResponseForbidden
from users.choices import UserTypeOptions
from helpdesk.choices import TicketStatusOptions, TicketGradeOptions, TicketPriorityOptions
from django.db.models import Q, Prefetch
from users.models import User
import json
import random
from django.core.paginator import Paginator

# Función para verificar permisos según tipo de usuario
def check_permission(user, action_type, ticket=None):
    """
    Verifica si un usuario tiene permiso para realizar una acción específica.
    
    Args:
        user: Usuario actual
        action_type: Tipo de acción a verificar ('update_status', 'rate', 'update_priority', etc.)
        ticket: Ticket sobre el que se realiza la acción (opcional)
    
    Returns:
        Boolean: True si tiene permiso, False si no lo tiene
    """
    # Si es administrador, tiene todos los permisos
    if user.tipo_usuario == UserTypeOptions.ADMINISTRADOR:
        return True
        
    # Permisos para soporte
    if user.tipo_usuario == UserTypeOptions.SOPORTE:
        # Soporte puede hacer todo excepto calificar la atención y cerrar tickets
        if action_type in ['rate', 'close']:
            return False
        return True
        
    # Permisos para cliente
    if user.tipo_usuario == UserTypeOptions.CLIENTE:
        # Cliente puede reabrir sus propios tickets según el estado
        if action_type == 'reopen' and ticket:
            # Verificar si el usuario es el solicitante del ticket
            es_solicitante = Asignacion.objects.filter(
                ticket=ticket, 
                solicitante=user
            ).exists()
            
            # Si es solicitante y el ticket está RESUELTO, puede reabrirlo fácilmente
            if es_solicitante and ticket.estado == TicketStatusOptions.RESUELTO:
                return True
                
            # Si está CERRADO, solo los administradores pueden reabrirlo
            if ticket.estado == TicketStatusOptions.CERRADO:
                return False
                
            return es_solicitante
        
        # Cliente puede calificar sus propios tickets
        if action_type == 'rate' and ticket:
            es_solicitante = Asignacion.objects.filter(
                ticket=ticket, 
                solicitante=user
            ).exists()
            
            return es_solicitante
            
        # Cliente puede crear tickets, añadir comentarios, pero no puede:
        if action_type in ['update_status', 'update_priority', 'close']:
            return False
            
        # Para otras acciones (como editar su propio ticket)
        return True
        
    # Por defecto, denegar permiso
    return False

@login_required
def index_view(request):
    return render(request, 'Home/Index.html')

@login_required
def ticket_list(request):
    base_query = Ticket.objects.select_related('tipo').prefetch_related('asignaciones__solicitante', 'asignaciones__agente')
    
    # Filtrar tickets según el tipo de usuario
    if request.user.tipo_usuario == UserTypeOptions.ADMINISTRADOR:
        # Administradores ven todos los tickets
        tickets = base_query.all()
    elif request.user.tipo_usuario == UserTypeOptions.SOPORTE:
        # Soporte ve tickets asignados a él
        tickets = base_query.filter(
            asignaciones__agente=request.user
        ).distinct()
    else:
        # Clientes ven tickets donde son solicitantes
        tickets = base_query.filter(
            asignaciones__solicitante=request.user
        ).distinct()
    
    # Aplicar filtros de búsqueda
    search_query = request.GET.get('search', '')
    if search_query:
        tickets = tickets.filter(
            Q(code__icontains=search_query) |
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    # Filtro por estado
    estado = request.GET.get('estado')
    if estado and estado.isdigit():
        tickets = tickets.filter(estado=int(estado))
    
    # Filtro por prioridad
    prioridad = request.GET.get('prioridad')
    if prioridad and prioridad.isdigit():
        tickets = tickets.filter(prioridad=int(prioridad))
    
    # Filtro por categoría
    categoria = request.GET.get('categoria')
    if categoria and categoria.isdigit():
        tickets = tickets.filter(tipo_id=int(categoria))
    
    # Ordenar tickets (por defecto por fecha de creación descendente)
    order_by = request.GET.get('order_by', '-created_at')
    tickets = tickets.order_by(order_by)
    
    # Paginación
    paginator = Paginator(tickets, 10)  # 10 tickets por página
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Obtener listas para los selectores de filtro
    estados = TicketStatusOptions.choices
    prioridades = TicketPriorityOptions.choices
    categorias = TicketType.objects.all()
    
    # Calcular estadísticas para mostrar en la cabecera
    tickets_abiertos = base_query.filter(estado=TicketStatusOptions.ABIERTO).count()
    tickets_resueltos = base_query.filter(estado=TicketStatusOptions.RESUELTO).count()
    tickets_cerrados = base_query.filter(estado=TicketStatusOptions.CERRADO).count()
    tickets_reabiertos = base_query.filter(estado=TicketStatusOptions.REABIERTO).count()
        
    return render(request, 'Home/Tickets/ticket_list.html', {
        'page_obj': page_obj,
        'tickets_count': tickets.count(),
        'estados': estados,
        'prioridades': prioridades,
        'categorias': categorias,
        'tickets_abiertos': tickets_abiertos,
        'tickets_resueltos': tickets_resueltos,
        'tickets_cerrados': tickets_cerrados,
        'tickets_reabiertos': tickets_reabiertos,
        'es_administrador': request.user.tipo_usuario == UserTypeOptions.ADMINISTRADOR,
        'es_soporte': request.user.tipo_usuario == UserTypeOptions.SOPORTE,
        'filtros': {
            'search': search_query,
            'estado': estado,
            'prioridad': prioridad,
            'categoria': categoria,
            'order_by': order_by
        }
    })

@login_required
def ticket_create(request):
    if request.method == 'POST':
        form = TicketForm(request.POST, request.FILES)
        if form.is_valid():
            ticket = form.save(commit=False)
            # Establecer estado Abierto
            ticket.estado = TicketStatusOptions.ABIERTO
            # Guardar el usuario actual para la asignación
            ticket.usuario_actual = request.user
            # Guardamos el ticket, esto activará la asignación automática en el save
            ticket.save()
            
            # Registrar la creación en el historial
            TicketHistory.registrar_cambio(
                ticket=ticket,
                usuario=request.user,
                campo='creacion',
                valor_anterior='',
                valor_nuevo='',
                descripcion='Ticket creado'
            )
            
            messages.success(request, 'Ticket creado correctamente')
            return redirect('helpdesk:ticket_detail', pk=ticket.pk)
    else:
        form = TicketForm()
    return render(request, 'Home/Tickets/ticket_form.html', {'form': form})

@login_required
def ticket_detail(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    
    # Cargar interacciones con información de usuario
    interacciones = ticket.interacciones.all().select_related('usuario')
    
    # Agregar el rol de usuario a cada interacción para mostrarlo en la vista
    for interaccion in interacciones:
        if interaccion.usuario.tipo_usuario == UserTypeOptions.ADMINISTRADOR:
            interaccion.rol_usuario = "Administrador"
        elif interaccion.usuario.tipo_usuario == UserTypeOptions.SOPORTE:
            interaccion.rol_usuario = "Soporte"
        else:
            interaccion.rol_usuario = "Cliente"
    
    historial = ticket.historial.all().order_by('-created_at')  # Ordenar por más reciente primero
    form = InteraccionTicketForm()
    
    # Obtener asignaciones
    asignaciones = ticket.asignaciones.all().select_related('agente', 'solicitante')

    if request.method == 'POST':
        form = InteraccionTicketForm(request.POST)
        if form.is_valid():
            mensaje = form.save(commit=False)
            mensaje.ticket = ticket
            mensaje.usuario = request.user
            mensaje.es_agente = request.user.tipo_usuario in [UserTypeOptions.ADMINISTRADOR, UserTypeOptions.SOPORTE]
            
            # Guardar el mensaje
            mensaje.save()
            
            # Registrar en historial
            TicketHistory.registrar_cambio(
                ticket=ticket,
                usuario=request.user,
                campo='interaccion',
                valor_anterior='',
                valor_nuevo=mensaje.mensaje[:50] + '...' if len(mensaje.mensaje) > 50 else mensaje.mensaje,
                descripcion=f"Mensaje añadido por {request.user.username}"
            )
            
            messages.success(request, 'Mensaje enviado correctamente')
            return redirect('helpdesk:ticket_detail', pk=pk)

    # Verificar permisos para mostrar botones y opciones
    puede_editar = check_permission(request.user, 'update_ticket', ticket)
    puede_cambiar_estado = check_permission(request.user, 'update_status', ticket)
    puede_calificar = check_permission(request.user, 'rate', ticket) and ticket.estado in [TicketStatusOptions.CERRADO, TicketStatusOptions.RESUELTO]
    
    # Permisos para reabrir según el estado
    puede_reabrir = check_permission(request.user, 'reopen', ticket) and ticket.estado in [TicketStatusOptions.CERRADO, TicketStatusOptions.RESUELTO]
    
    # Determinar si el usuario es el solicitante del ticket
    es_solicitante = Asignacion.objects.filter(
        ticket=ticket, 
        solicitante=request.user
    ).exists()
    
    # Para mensajes específicos sobre reapertura
    es_ticket_resuelto = ticket.estado == TicketStatusOptions.RESUELTO
    es_ticket_cerrado = ticket.estado == TicketStatusOptions.CERRADO
    
    # Verificar explícitamente los tipos de usuario
    es_administrador = request.user.tipo_usuario == UserTypeOptions.ADMINISTRADOR
    es_soporte = request.user.tipo_usuario == UserTypeOptions.SOPORTE
    
    puede_cerrar = check_permission(request.user, 'close', ticket) and ticket.estado not in [TicketStatusOptions.CERRADO, TicketStatusOptions.RESUELTO]
    puede_resolver = check_permission(request.user, 'update_status', ticket) and ticket.estado not in [TicketStatusOptions.CERRADO, TicketStatusOptions.RESUELTO]

    # Preparar mensaje informativo sobre la política de resolución/cierre
    mostrar_mensaje_politica = request.user.tipo_usuario in [UserTypeOptions.ADMINISTRADOR, UserTypeOptions.SOPORTE]

    return render(request, 'Home/Tickets/ticket_detail.html', {
        'ticket': ticket,
        'interacciones': interacciones,
        'historial': historial,
        'form': form,
        'asignaciones': asignaciones,
        'puede_calificar': puede_calificar,
        'puede_editar': puede_editar,
        'puede_cambiar_estado': puede_cambiar_estado,
        'puede_reabrir': puede_reabrir,
        'puede_cerrar': puede_cerrar,
        'puede_resolver': puede_resolver,
        'es_solicitante': es_solicitante,
        'es_ticket_resuelto': es_ticket_resuelto,
        'es_ticket_cerrado': es_ticket_cerrado,
        'es_administrador': es_administrador,
        'es_soporte': es_soporte,
        'mostrar_mensaje_politica': mostrar_mensaje_politica,
        'calificacion_opciones': [
            (TicketGradeOptions.MUY_BUENA.value, TicketGradeOptions.MUY_BUENA.label),
            (TicketGradeOptions.BUENA.value, TicketGradeOptions.BUENA.label),
            (TicketGradeOptions.BAJA.value, TicketGradeOptions.BAJA.label),
            (TicketGradeOptions.MUY_BAJA.value, TicketGradeOptions.MUY_BAJA.label),
        ]
    })

@login_required
def ticket_update(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    
    # Verificar permisos
    if not check_permission(request.user, 'update_ticket', ticket):
        messages.error(request, 'No tienes permisos para actualizar este ticket')
        return redirect('helpdesk:ticket_detail', pk=pk)
    
    old_ticket = Ticket.objects.get(pk=ticket.pk)  # Guardar estado previo
    
    # Seleccionar el formulario según el tipo de usuario
    if request.user.tipo_usuario == UserTypeOptions.CLIENTE:
        form = ClienteTicketUpdateForm(request.POST or None, request.FILES or None, instance=ticket)
    else:
        form = TicketUpdateForm(request.POST or None, request.FILES or None, instance=ticket)
    
    if form.is_valid():
        # Preparar para registrar cambios
        ticket.usuario_actual = request.user
        
        # Registrar cada campo modificado
        for field_name in form.changed_data:
            if field_name != 'adjunto':  # Manejar adjuntos de forma especial
                # Verificar permisos específicos para campos sensibles
                if field_name == 'estado' and not check_permission(request.user, 'update_status', ticket):
                    messages.error(request, f'No tienes permisos para modificar el estado del ticket')
                    continue
                
                if field_name == 'prioridad' and not check_permission(request.user, 'update_priority', ticket):
                    messages.error(request, f'No tienes permisos para modificar la prioridad del ticket')
                    continue
                
                old_value = getattr(old_ticket, f'get_{field_name}_display', lambda: getattr(old_ticket, field_name))()
                new_value = getattr(ticket, f'get_{field_name}_display', lambda: getattr(ticket, field_name))()
                
                TicketHistory.registrar_cambio(
                    ticket=ticket,
                    usuario=request.user,
                    campo=field_name,
                    valor_anterior=str(old_value),
                    valor_nuevo=str(new_value),
                    descripcion=f"Cambio en {field_name} de '{old_value}' a '{new_value}'"
                )
        
        # Si hay nuevo adjunto
        if 'adjunto' in form.changed_data:
            if old_ticket.adjunto:
                old_value = old_ticket.adjunto.name.split('/')[-1]
            else:
                old_value = "Sin adjunto"
                
            if ticket.adjunto:
                new_value = ticket.adjunto.name.split('/')[-1]
            else:
                new_value = "Sin adjunto"
                
            TicketHistory.registrar_cambio(
                ticket=ticket,
                usuario=request.user,
                campo='adjunto',
                valor_anterior=old_value,
                valor_nuevo=new_value,
                descripcion=f"Cambio en adjunto de '{old_value}' a '{new_value}'"
            )
            
        form.save()
        messages.success(request, 'Ticket actualizado correctamente')
        return redirect('helpdesk:ticket_detail', pk=pk)
        
    return render(request, 'Home/Tickets/ticket_form.html', {'form': form, 'edit': True})

@login_required
def ticket_close(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    
    # Verificar que el usuario sea administrador
    if request.user.tipo_usuario != UserTypeOptions.ADMINISTRADOR:
        messages.error(request, 'Solo los administradores pueden cerrar tickets')
        return redirect('helpdesk:ticket_detail', pk=pk)
    
    # Verificar permisos
    if not check_permission(request.user, 'close', ticket):
        messages.error(request, 'No tienes permisos para cerrar este ticket')
        return redirect('helpdesk:ticket_detail', pk=pk)
    
    old_estado = ticket.get_estado_display()
    
    ticket.usuario_actual = request.user
    ticket.estado = TicketStatusOptions.CERRADO  # Usar el valor del enum
    ticket.close_date = timezone.now()
    ticket.save()
    
    # Registrar en historial
    TicketHistory.registrar_cambio(
        ticket=ticket,
        usuario=request.user,
        campo='estado',
        valor_anterior=old_estado,
        valor_nuevo=ticket.get_estado_display(),
        descripcion=f"Ticket cerrado por administrador"
    )
    
    messages.success(request, 'Ticket cerrado correctamente')
    return redirect('helpdesk:ticket_detail', pk=pk)

@login_required
def ticket_rate(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    
    # Verificar permisos
    if not check_permission(request.user, 'rate', ticket):
        messages.error(request, 'No tienes permisos para calificar este ticket')
        return redirect('helpdesk:ticket_detail', pk=pk)
    
    if request.method == 'POST':
        calificacion = request.POST.get('calificacion')
        if calificacion and calificacion.isdigit():
            ticket.usuario_actual = request.user  # Para el registro en el historial
            ticket.calificacion = int(calificacion)
            ticket.save()
            messages.success(request, '¡Gracias por calificar el servicio!')
        else:
            messages.error(request, 'Por favor selecciona una calificación válida.')
    return redirect('helpdesk:ticket_detail', pk=pk)

@login_required
def ticket_reopen(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    
    # Verificar permisos
    if not check_permission(request.user, 'reopen', ticket):
        messages.error(request, 'No tienes permisos para reabrir este ticket')
        return redirect('helpdesk:ticket_detail', pk=pk)
    
    if ticket.estado in [TicketStatusOptions.CERRADO, TicketStatusOptions.RESUELTO]:
        # Guardar estado anterior para el registro
        old_estado = ticket.get_estado_display()
        
        # Si está cerrado, verificar que el usuario sea administrador
        if ticket.estado == TicketStatusOptions.CERRADO and request.user.tipo_usuario != UserTypeOptions.ADMINISTRADOR:
            messages.error(request, 'Solo los administradores pueden reabrir tickets cerrados')
            return redirect('helpdesk:ticket_detail', pk=pk)
        
        # Reabrir el ticket
        ticket.usuario_actual = request.user
        ticket.estado = TicketStatusOptions.REABIERTO
        ticket.close_date = None  # Eliminar fecha de cierre
        ticket.save()
        
        # Registrar la acción en el historial
        TicketHistory.registrar_cambio(
            ticket=ticket,
            usuario=request.user,
            campo='estado',
            valor_anterior=old_estado,
            valor_nuevo=ticket.get_estado_display(),
            descripcion=f"Ticket reabierto desde estado {old_estado}"
        )
        
        # Mensajes diferentes según el estado anterior
        if old_estado == TicketStatusOptions.RESUELTO.label:
            messages.success(request, 'Ticket reabierto correctamente. Por favor proporciona más detalles sobre por qué el problema no está resuelto.')
        else:
            messages.success(request, 'Ticket reabierto correctamente desde estado cerrado.')
    else:
        messages.error(request, 'Solo se pueden reabrir tickets cerrados o resueltos')
        
    return redirect('helpdesk:ticket_detail', pk=pk)

@login_required
def ticket_resolve(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    
    # Verificar permisos
    if not check_permission(request.user, 'update_status', ticket):
        messages.error(request, 'No tienes permisos para resolver este ticket')
        return redirect('helpdesk:ticket_detail', pk=pk)
    
    old_estado = ticket.get_estado_display()
    
    ticket.usuario_actual = request.user
    ticket.estado = TicketStatusOptions.RESUELTO  # Usar el valor del enum
    ticket.close_date = timezone.now()
    ticket.save()
    
    # Registrar en historial
    TicketHistory.registrar_cambio(
        ticket=ticket,
        usuario=request.user,
        campo='estado',
        valor_anterior=old_estado,
        valor_nuevo=ticket.get_estado_display(),
        descripcion=f"Ticket marcado como resuelto"
    )
    
    messages.success(request, 'Ticket marcado como resuelto correctamente')
    return redirect('helpdesk:ticket_detail', pk=pk)

@login_required
def dashboard_view(request):
    """
    Dashboard con información resumida y visualizaciones gráficas de tickets
    """
    # Verificar si el usuario tiene permisos para acceder al dashboard
    if request.user.tipo_usuario not in [UserTypeOptions.ADMINISTRADOR, UserTypeOptions.SOPORTE]:
        messages.error(request, 'No tienes permisos para acceder al dashboard')
        return redirect('helpdesk:ticket_list')
    
    # Determinar si es administrador
    es_administrador = request.user.tipo_usuario == UserTypeOptions.ADMINISTRADOR
    
    # Lógica para obtener los tickets filtrados según el tipo de usuario
    if es_administrador:
        # Administradores ven todos los tickets
        tickets_base = Ticket.objects.all()
        tickets_activos = tickets_base.filter(
            estado__in=[TicketStatusOptions.ABIERTO, TicketStatusOptions.REABIERTO]
        )
    else:
        # Agentes de soporte solo ven sus tickets asignados
        tickets_base = Ticket.objects.filter(asignaciones__agente=request.user)
        tickets_activos = tickets_base.filter(
            estado__in=[TicketStatusOptions.ABIERTO, TicketStatusOptions.REABIERTO]
        )
    
    # Contar tickets por categoría/tipo
    tickets_por_categoria = {}
    categorias = TicketType.objects.all()
    for categoria in categorias:
        count = tickets_activos.filter(tipo=categoria).count()
        tickets_por_categoria[categoria.nombre] = count
    
    # Estadísticas generales, filtradas por usuario si es agente
    tickets_abiertos = tickets_base.filter(estado=TicketStatusOptions.ABIERTO).count()
    tickets_resueltos = tickets_base.filter(estado=TicketStatusOptions.RESUELTO).count()
    tickets_cerrados = tickets_base.filter(estado=TicketStatusOptions.CERRADO).count()
    tickets_reabiertos = tickets_base.filter(estado=TicketStatusOptions.REABIERTO).count()
    
    # Total de tickets (global para admin, específicos para agente)
    total_tickets = tickets_base.count()
    
    # Tickets por prioridad
    tickets_criticos = tickets_activos.filter(prioridad=TicketPriorityOptions.CRITICA).count()
    tickets_altos = tickets_activos.filter(prioridad=TicketPriorityOptions.ALTA).count()
    tickets_medios = tickets_activos.filter(prioridad=TicketPriorityOptions.MEDIA).count()
    tickets_bajos = tickets_activos.filter(prioridad=TicketPriorityOptions.BAJA).count()
    
    # Tickets recientes (todos para admin, solo del agente para soporte)
    if es_administrador:
        tickets_recientes = Ticket.objects.all().order_by('-created_at')[:5]
        actividad_reciente = TicketHistory.objects.all().order_by('-created_at')[:10]
    else:
        tickets_recientes = tickets_base.order_by('-created_at')[:5]
        # Mostrar solo actividad relacionada con los tickets del agente
        tickets_ids = tickets_base.values_list('id', flat=True)
        actividad_reciente = TicketHistory.objects.filter(ticket_id__in=tickets_ids).order_by('-created_at')[:10]
    
    # Si es administrador, mostrar carga de trabajo de todos los agentes
    # Si es agente, solo mostrar su propia carga de trabajo
    carga_agentes = []
    
    if es_administrador:
        # Mostrar datos de todos los agentes
        agentes = User.objects.filter(tipo_usuario=UserTypeOptions.SOPORTE)
    else:
        # Solo mostrar datos del agente actual
        agentes = User.objects.filter(id=request.user.id)
    
    # Preparar datos para gráficos en formato JSON
    datos_categorias = {
        'labels': list(tickets_por_categoria.keys()),
        'data': list(tickets_por_categoria.values())
    }
    
    datos_estados = {
        'labels': ['Abiertos', 'Resueltos', 'Cerrados', 'Reabiertos'],
        'data': [tickets_abiertos, tickets_resueltos, tickets_cerrados, tickets_reabiertos]
    }
    
    datos_prioridad = {
        'labels': ['Crítica', 'Alta', 'Media', 'Baja'],
        'data': [tickets_criticos, tickets_altos, tickets_medios, tickets_bajos]
    }
    
    # Datos para el gráfico de rendimiento de agentes
    # Para administradores: todos los agentes
    # Para agentes: solo sus propios datos
    agentes_usernames = []
    agentes_tickets_resueltos = []
    
    # También crear datos detallados para el panel de rendimiento
    agentes_rendimiento = []
    tickets_max = 0  # Para calcular el máximo y hacer las barras proporcionales
    
    for agente in agentes:
        # Contar tickets resueltos por este agente
        tickets_resueltos_agente = Ticket.objects.filter(
            estado=3,  # Estado resuelto
            asignaciones__agente=agente
        ).count()
        
        # Guardar para el gráfico
        agentes_usernames.append(agente.username)
        agentes_tickets_resueltos.append(tickets_resueltos_agente)
        
        # Actualizar el máximo
        if tickets_resueltos_agente > tickets_max:
            tickets_max = tickets_resueltos_agente
        
        # Datos detallados para cada agente
        tickets_pendientes = Ticket.objects.filter(
            estado=1,  # Estado abierto
            asignaciones__agente=agente
        ).count()
        
        # Calcular tiempo medio de resolución (simulado - ajustar según modelo real)
        tiempo_medio = round(random.uniform(1.5, 8.5), 1)  # Ejemplo: entre 1.5 y 8.5 horas
        
        # Calcular satisfacción media (simulado - ajustar según modelo real)
        satisfaccion = round(random.uniform(3.5, 5.0), 1)  # Ejemplo: entre 3.5 y 5.0
        
        # Calcular eficiencia (porcentaje basado en alguna métrica, simulado aquí)
        eficiencia = min(100, int((tickets_resueltos_agente / max(1, tickets_pendientes + tickets_resueltos_agente)) * 100))
        
        # Agregar datos del agente
        agentes_rendimiento.append({
            'username': agente.username,
            'tickets_resueltos': tickets_resueltos_agente,
            'tickets_pendientes': tickets_pendientes,
            'tiempo_medio': tiempo_medio,
            'satisfaccion': satisfaccion,
            'eficiencia': eficiencia
        })
    
    # Ordenar agentes por tickets resueltos (descendente)
    agentes_rendimiento = sorted(agentes_rendimiento, key=lambda x: x['tickets_resueltos'], reverse=True)
    
    # Calcular estadísticas globales
    if agentes_rendimiento:
        tiempo_promedio_global = round(sum(a['tiempo_medio'] for a in agentes_rendimiento) / len(agentes_rendimiento), 1)
        satisfaccion_media = round(sum(a['satisfaccion'] for a in agentes_rendimiento) / len(agentes_rendimiento), 1)
        eficiencia_media = int(sum(a['eficiencia'] for a in agentes_rendimiento) / len(agentes_rendimiento))
        total_resueltos_mes = sum(a['tickets_resueltos'] for a in agentes_rendimiento)
    else:
        tiempo_promedio_global = 0
        satisfaccion_media = 0
        eficiencia_media = 0
        total_resueltos_mes = 0
    
    # Calcular top agentes (con porcentaje sobre promedio) - solo para administradores
    top_agentes = []
    if es_administrador and agentes_rendimiento:
        # Para administradores: obtener el top 5 de todos los agentes
        top_agentes = agentes_rendimiento[:5]
        
        # Calcular promedio de tickets resueltos entre todos los agentes
        promedio_tickets = sum(a['tickets_resueltos'] for a in agentes_rendimiento) / len(agentes_rendimiento)
        
        # Calcular porcentaje sobre el promedio para cada agente del top
        for agente in top_agentes:
            if promedio_tickets > 0:
                agente['porcentaje_sobre_promedio'] = int((agente['tickets_resueltos'] / promedio_tickets * 100) - 100)
            else:
                agente['porcentaje_sobre_promedio'] = 0
    
    # Serializar datos para el gráfico de agentes
    datos_agentes_json = json.dumps({
        'labels': agentes_usernames,
        'data': agentes_tickets_resueltos
    })
    
    return render(request, 'Home/dashboard.html', {
        'total_tickets': total_tickets,
        'tickets_abiertos': tickets_abiertos,
        'tickets_resueltos': tickets_resueltos,
        'tickets_cerrados': tickets_cerrados,
        'tickets_reabiertos': tickets_reabiertos,
        'tickets_por_categoria': tickets_por_categoria,
        'tickets_recientes': tickets_recientes,
        'actividad_reciente': actividad_reciente,
        'carga_agentes': carga_agentes,
        'datos_categorias_json': json.dumps(datos_categorias),
        'datos_estados_json': json.dumps(datos_estados),
        'datos_prioridad_json': json.dumps(datos_prioridad),
        'es_administrador': es_administrador,
        'datos_agentes_json': datos_agentes_json,
        'agentes_rendimiento': agentes_rendimiento,
        'tickets_max': tickets_max or 1,  # Evitar división por cero
        'tiempo_promedio_global': tiempo_promedio_global,
        'satisfaccion_media': satisfaccion_media,
        'eficiencia_media': eficiencia_media,
        'total_resueltos_mes': total_resueltos_mes,
        'top_agentes': top_agentes,
    })

@login_required
def reports_view(request):
    """
    Vista para generar reportes personalizados
    """
    # Verificar si el usuario tiene permisos para acceder a los reportes
    if request.user.tipo_usuario != UserTypeOptions.ADMINISTRADOR:
        messages.error(request, 'No tienes permisos para acceder a los reportes')
        return redirect('helpdesk:ticket_list')
    
    # Establecer filtros por defecto
    fecha_inicio = request.GET.get('fecha_inicio', '')
    fecha_fin = request.GET.get('fecha_fin', '')
    estado = request.GET.get('estado', '')
    prioridad = request.GET.get('prioridad', '')
    categoria = request.GET.get('categoria', '')
    agente = request.GET.get('agente', '')
    
    # Iniciar el queryset base
    tickets = Ticket.objects.all().select_related('tipo').prefetch_related('asignaciones__agente', 'asignaciones__solicitante')
    
    # Aplicar filtros
    if fecha_inicio and fecha_fin:
        from datetime import datetime
        try:
            fecha_inicio_dt = datetime.strptime(fecha_inicio, '%Y-%m-%d')
            fecha_fin_dt = datetime.strptime(fecha_fin, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
            tickets = tickets.filter(created_at__range=[fecha_inicio_dt, fecha_fin_dt])
        except ValueError:
            pass
    
    if estado:
        try:
            estado_valor = int(estado)
            tickets = tickets.filter(estado=estado_valor)
        except ValueError:
            pass
            
    if prioridad:
        try:
            prioridad_valor = int(prioridad)
            tickets = tickets.filter(prioridad=prioridad_valor)
        except ValueError:
            pass
            
    if categoria:
        try:
            categoria_valor = int(categoria)
            tickets = tickets.filter(tipo_id=categoria_valor)
        except ValueError:
            pass
            
    if agente and request.user.tipo_usuario == UserTypeOptions.ADMINISTRADOR:
        try:
            agente_valor = int(agente)
            tickets = tickets.filter(asignaciones__agente_id=agente_valor)
        except ValueError:
            pass
    
    # Obtener listas para los selectores de filtro
    estados = TicketStatusOptions.choices
    prioridades = TicketPriorityOptions.choices
    categorias = TicketType.objects.all()
    
    # Obtener agentes solo si es administrador
    agentes = []
    if request.user.tipo_usuario == UserTypeOptions.ADMINISTRADOR:
        agentes = User.objects.filter(tipo_usuario=UserTypeOptions.SOPORTE)
    
    # Calcular estadísticas para el reporte
    total_tickets = tickets.count()
    promedio_tiempo_resolucion = None
    
    # Si hay tickets en el filtro, calcular estadísticas
    if total_tickets > 0:
        from django.db.models import Avg, F, ExpressionWrapper, fields
        from django.db.models.functions import Extract
        
        # Tickets resueltos o cerrados con tiempo de resolución
        tickets_finalizados = tickets.filter(
            estado__in=[TicketStatusOptions.RESUELTO, TicketStatusOptions.CERRADO],
            close_date__isnull=False
        )
        
        if tickets_finalizados.exists():
            # Calcular tiempo promedio de resolución en días
            tiempo_resolucion = tickets_finalizados.annotate(
                tiempo_resolucion=ExpressionWrapper(
                    F('close_date') - F('created_at'),
                    output_field=fields.DurationField()
                )
            ).aggregate(
                promedio=Avg('tiempo_resolucion')
            )
            
            if tiempo_resolucion['promedio']:
                # Convertir a días
                promedio_tiempo_resolucion = tiempo_resolucion['promedio'].total_seconds() / (60 * 60 * 24)
                promedio_tiempo_resolucion = round(promedio_tiempo_resolucion, 1)
    
    return render(request, 'Home/reports.html', {
        'tickets': tickets,
        'estados': estados,
        'prioridades': prioridades,
        'categorias': categorias,
        'agentes': agentes,
        'filtros': {
            'fecha_inicio': fecha_inicio,
            'fecha_fin': fecha_fin,
            'estado': estado,
            'prioridad': prioridad,
            'categoria': categoria,
            'agente': agente
        },
        'total_tickets': total_tickets,
        'promedio_tiempo_resolucion': promedio_tiempo_resolucion,
        'es_administrador': request.user.tipo_usuario == UserTypeOptions.ADMINISTRADOR
    })
