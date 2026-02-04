from django.contrib.auth.models import AbstractUser
from django.db import models

class Usuario(AbstractUser):
    ROLES = [
        ('operario', 'Operario'),
        ('administrativo', 'Administrativo'),
        ('superusuario', 'Súper Usuario'),
    ]
    
    rol = models.CharField(max_length=20, choices=ROLES, default='operario')
    telefono = models.CharField(max_length=15, blank=True, null=True)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.username} ({self.get_rol_display()})"
