from django import forms
from .models import Ticket, InteraccionTicket

class TicketForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ['title', 'description', 'prioridad', 'estado', 'adjunto', 'tipo']

class TicketUpdateForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ['title', 'description', 'prioridad', 'estado', 'adjunto']

class InteraccionTicketForm(forms.ModelForm):
    class Meta:
        model = InteraccionTicket
        fields = ['mensaje']
