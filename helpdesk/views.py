from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, get_object_or_404, redirect
from .models import Ticket, TicketHistory, TicketStatusOptions, TicketGradeOptions
from .forms import TicketForm, TicketUpdateForm, InteraccionTicketForm
from django.contrib.auth.decorators import login_required
from django.utils import timezone

@login_required
def index_view(request):
    return render(request, 'Home/Index.html')

@login_required
def ticket_list(request):
    tickets = Ticket.objects.all()
    return render(request, 'Home/Tickets/ticket_list.html', {'tickets': tickets})

@login_required
def ticket_create(request):
    if request.method == 'POST':
        form = TicketForm(request.POST, request.FILES)
        if form.is_valid():
            ticket = form.save(commit=False)
            # Guardamos el ticket
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
    interacciones = ticket.interacciones.all()
    historial = ticket.historial.all().order_by('-created_at')  # Ordenar por más reciente primero
    form = InteraccionTicketForm()

    if request.method == 'POST':
        form = InteraccionTicketForm(request.POST)
        if form.is_valid():
            mensaje = form.save(commit=False)
            mensaje.ticket = ticket
            mensaje.usuario = request.user
            mensaje.es_agente = request.user.is_staff
            
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

    return render(request, 'Home/Tickets/ticket_detail.html', {
        'ticket': ticket,
        'interacciones': interacciones,
        'historial': historial,
        'form': form,
        'puede_calificar': ticket.estado in [TicketStatusOptions.CERRADO, TicketStatusOptions.RESUELTO],
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
    old_ticket = Ticket.objects.get(pk=ticket.pk)  # Guardar estado previo
    
    form = TicketUpdateForm(request.POST or None, request.FILES or None, instance=ticket)
    if form.is_valid():
        # Preparar para registrar cambios
        ticket.usuario_actual = request.user
        
        # Registrar cada campo modificado
        for field_name in form.changed_data:
            if field_name != 'adjunto':  # Manejar adjuntos de forma especial
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
        descripcion=f"Ticket cerrado"
    )
    
    messages.success(request, 'Ticket cerrado correctamente')
    return redirect('helpdesk:ticket_detail', pk=pk)

@login_required
def ticket_rate(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
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
    if ticket.estado in [TicketStatusOptions.CERRADO, TicketStatusOptions.RESUELTO]:
        # Guardar estado anterior para el registro
        old_estado = ticket.get_estado_display()
        
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
            descripcion=f"Ticket reabierto"
        )
        
        messages.success(request, 'Ticket reabierto correctamente')
    else:
        messages.error(request, 'Solo se pueden reabrir tickets cerrados o resueltos')
        
    return redirect('helpdesk:ticket_detail', pk=pk)
