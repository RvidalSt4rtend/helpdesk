from django.utils.translation import gettext_lazy as _
from django.db import models

class TicketPriorityOptions(models.IntegerChoices):
    CRITICA = 1, _("Critica")
    ALTA = 2, _("Alta")
    MEDIA = 3, _("Media")
    BAJA = 4, _("Baja")

class TicketStatusOptions(models.IntegerChoices):
    """
    Estados del ticket y su significado:
    
    - ABIERTO: Problema reportado, pendiente de atención.
    - RESUELTO: El problema fue atendido pero espera confirmación del cliente. Se puede reabrir fácilmente.
    - CERRADO: El proceso está completamente finalizado, no se espera más interacción. No se puede reabrir normalmente.
    - REABIERTO: Ticket que estaba resuelto o cerrado pero fue reabierto por el cliente o soporte.
    """
    ABIERTO = 1, _("Abierto")
    CERRADO = 2, _("Cerrado")
    RESUELTO = 3, _("Resuelto")
    REABIERTO = 4, _("Reabierto")

class TicketGradeOptions(models.IntegerChoices):
    MUY_BUENA = 5, _("Muy Buena")
    BUENA = 4, _("Buena")
    NORMAL = 3, _("Normal")
    BAJA = 2, _("Baja")
    MUY_BAJA = 1, _("Muy Baja")

class TicketCategoryOptions(models.IntegerChoices):
    HARDWARE = 1, _("Hardware")
    SOFTWARE = 2, _("Software")
    REDES = 3, _("Redes")
