from django.db import models


class UserAccount(models.Model):
    """Usuario de la aplicación sin depender de django.contrib.auth.
    Permite roles de 'admin' y 'customer' y sirve como base para implementar login/register más adelante.
    """

    ROLE_ADMIN = 'admin'
    ROLE_CUSTOMER = 'customer'
    ROLE_CHOICES = (
        (ROLE_ADMIN, 'Administrador'),
        (ROLE_CUSTOMER, 'Cliente'),
    )

    email = models.EmailField(unique=True)
    password_hash = models.CharField(max_length=256, default='')  # Preparado para implementar login/register
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_CUSTOMER)
    first_name = models.CharField(max_length=50, default='')
    last_name = models.CharField(max_length=50, default='')
    is_active = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-created',)

    def __str__(self) -> str:
        return f"{self.email} ({self.role})"
