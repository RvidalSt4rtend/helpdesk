from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, get_object_or_404, redirect
from .models import Ticket, TicketHistory, TicketStatusOptions, TicketGradeOptions, Asignacion
from .forms import TicketForm, TicketUpdateForm, InteraccionTicketForm, ClienteTicketUpdateForm
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.http import HttpResponseForbidden
from users.choices import UserTypeOptions
from django.db.models import Q, Prefetch

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
        
    return render(request, 'Home/Tickets/ticket_list.html', {
        'tickets': tickets,
        'es_administrador': request.user.tipo_usuario == UserTypeOptions.ADMINISTRADOR,
        'es_soporte': request.user.tipo_usuario == UserTypeOptions.SOPORTE
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
