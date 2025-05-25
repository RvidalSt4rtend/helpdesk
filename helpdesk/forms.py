from django import forms
from .models import Ticket, InteraccionTicket

class TicketForm(forms.ModelForm):
    """
    Formulario para crear nuevos tickets
    No incluye el campo 'estado' porque todos los tickets se crean en estado 'Abierto'
    """
    class Meta:
        model = Ticket
        fields = ['title', 'description', 'prioridad', 'adjunto', 'tipo']

class TicketUpdateForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ['title', 'description', 'prioridad', 'estado', 'adjunto']

class ClienteTicketUpdateForm(forms.ModelForm):
    """
    Formulario restringido para clientes
    No incluye campos como prioridad o estado que solo debe modificar el soporte
    """
    class Meta:
        model = Ticket
        fields = ['title', 'description', 'adjunto']

class InteraccionTicketForm(forms.ModelForm):
    class Meta:
        model = InteraccionTicket
        fields = ['mensaje']
