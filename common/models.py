from django.db import models

STATUS_OPTIONS = (
    (1, "Activo"),
    (2, "Inactivo"),
    (3, "Eliminado"),
)


class TimeStampModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True)

    class Meta:
        """Indicates that it is abstract and not saved in DB."""

        abstract = True


class StatusModel(models.Model):
    status = models.PositiveIntegerField(choices=STATUS_OPTIONS, default=1)

    class Meta:
        """Indicates that it is abstract and not saved in DB."""

        abstract = True