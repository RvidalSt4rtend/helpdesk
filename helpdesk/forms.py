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
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'bg-dark-secondary border-dark-tertiary text-white',
                'style': 'background-color:#232336 !important;color:#fff !important;border-color:#2d2d44 !important;'
            }),
            'description': forms.Textarea(attrs={
                'class': 'bg-dark-secondary border-dark-tertiary text-white',
                'rows': 6,
                'style': 'background-color:#232336 !important;color:#fff !important;border-color:#2d2d44 !important;'
            }),
            'prioridad': forms.Select(attrs={
                'class': 'bg-dark-secondary border-dark-tertiary text-white',
                'style': 'background-color:#232336 !important;color:#fff !important;border-color:#2d2d44 !important;'
            }),
            'tipo': forms.Select(attrs={
                'class': 'bg-dark-secondary border-dark-tertiary text-white',
                'style': 'background-color:#232336 !important;color:#fff !important;border-color:#2d2d44 !important;'
            }),
            'adjunto': forms.ClearableFileInput(attrs={
                'class': 'bg-dark-secondary border-dark-tertiary text-white',
                'style': 'background-color:#232336 !important;color:#fff !important;border-color:#2d2d44 !important;'
            }),
        }

class TicketUpdateForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ['title', 'description', 'prioridad', 'estado', 'adjunto']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'bg-dark-secondary border-dark-tertiary text-white',
                'style': 'background-color:#232336 !important;color:#fff !important;border-color:#2d2d44 !important;'
            }),
            'description': forms.Textarea(attrs={
                'class': 'bg-dark-secondary border-dark-tertiary text-white',
                'rows': 6,
                'style': 'background-color:#232336 !important;color:#fff !important;border-color:#2d2d44 !important;'
            }),
            'prioridad': forms.Select(attrs={
                'class': 'bg-dark-secondary border-dark-tertiary text-white',
                'style': 'background-color:#232336 !important;color:#fff !important;border-color:#2d2d44 !important;'
            }),
            'estado': forms.Select(attrs={
                'class': 'bg-dark-secondary border-dark-tertiary text-white',
                'style': 'background-color:#232336 !important;color:#fff !important;border-color:#2d2d44 !important;'
            }),
            'adjunto': forms.ClearableFileInput(attrs={
                'class': 'bg-dark-secondary border-dark-tertiary text-white',
                'style': 'background-color:#232336 !important;color:#fff !important;border-color:#2d2d44 !important;'
            }),
        }

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
        widgets = {
            'mensaje': forms.Textarea(attrs={
                'class': 'bg-dark-secondary border-dark-tertiary text-secondary-500',
                'rows': 4
            })
        }
