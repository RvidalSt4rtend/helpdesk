from django.core.management.base import BaseCommand
from django.utils import timezone
from helpdesk.models import Ticket, TicketHistory, TicketStatusOptions
from django.contrib.auth import get_user_model
import datetime

User = get_user_model()

class Command(BaseCommand):
    help = 'Cierra automáticamente tickets que han superado su SLA'

    def handle(self, *args, **options):
        # Obtener el usuario del sistema
        system_user, created = User.objects.get_or_create(
            username='sistema',
            defaults={'is_staff': True, 'is_active': True}
        )
        
        # Obtener tickets abiertos
        tickets_abiertos = Ticket.objects.filter(
            estado=TicketStatusOptions.ABIERTO,
        )
        
        count = 0
        for ticket in tickets_abiertos:
            # Calcular tiempo transcurrido desde la creación
            tiempo_transcurrido = timezone.now() - ticket.created_at
            sla_hours = ticket.tipo.sla
            
            # Si el tiempo transcurrido supera el SLA, cerrar el ticket
            if tiempo_transcurrido > datetime.timedelta(hours=sla_hours):
                # Guardar información para el historial
                ticket.usuario_actual = system_user
                ticket.estado = TicketStatusOptions.CERRADO
                ticket.close_date = timezone.now()
                ticket.save()
                
                # Registrar en historial
                TicketHistory.registrar_cambio(
                    ticket=ticket,
                    usuario=system_user,
                    campo='estado',
                    valor_anterior=TicketStatusOptions.ABIERTO.label,
                    valor_nuevo=TicketStatusOptions.CERRADO.label,
                    descripcion='Ticket cerrado automáticamente por exceder SLA'
                )
                
                count += 1
        
        self.stdout.write(self.style.SUCCESS(f'{count} tickets cerrados automáticamente por SLA')) 