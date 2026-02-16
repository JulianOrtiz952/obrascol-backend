from django.db import models
from django.utils import timezone
from django.conf import settings

class Bodega(models.Model):
    nombre = models.CharField(max_length=100)
    ubicacion = models.CharField(max_length=255, blank=True)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre

class Subbodega(models.Model):
    nombre = models.CharField(max_length=100)
    bodega = models.ForeignKey(Bodega, on_delete=models.CASCADE, related_name='subbodegas')
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    activo = models.BooleanField(default=True)

    def get_full_path(self):
        if self.parent:
            return f"{self.parent.get_full_path()} > {self.nombre}"
        return self.nombre

    def __str__(self):
        return f"{self.bodega.nombre} - {self.get_full_path()}"

class Material(models.Model):
    codigo = models.CharField(max_length=50, unique=True)
    codigo_barras = models.CharField(max_length=100, unique=True, blank=True, null=True)
    referencia = models.CharField(max_length=100, blank=True, null=True)
    nombre = models.CharField(max_length=200)
    unidad = models.CharField(max_length=20) # pcs, m, L, etc.
    # New fields for V2
    marca = models.ForeignKey('Marca', on_delete=models.SET_NULL, null=True, blank=True, related_name='materiales')
    ultimo_precio = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    
    def __str__(self):
        return f"{self.codigo} - {self.nombre}"

class Factura(models.Model):
    numero = models.CharField(max_length=100, unique=True)
    proveedor = models.CharField(max_length=200, blank=True)
    fecha = models.DateField()

    def __str__(self):
        return self.numero

class Marca(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre

class UnidadMedida(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    abreviacion = models.CharField(max_length=10, unique=True)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.nombre} ({self.abreviacion})"

class Movimiento(models.Model):
    TIPO_MOVIMIENTO = [
        ('Entrada', 'Entrada'),
        ('Salida', 'Salida'),
        ('Traslado', 'Traslado'),
        ('Edicion', 'Edición'),
        ('Ajuste', 'Ajuste'),
        ('Devolucion', 'Devolución'),
    ]
    
    material = models.ForeignKey(Material, on_delete=models.CASCADE, related_name='movimientos')
    bodega = models.ForeignKey(Bodega, on_delete=models.CASCADE, related_name='movimientos')
    subbodega = models.ForeignKey(Subbodega, on_delete=models.SET_NULL, null=True, blank=True, related_name='movimientos')
    bodega_destino = models.ForeignKey(Bodega, on_delete=models.SET_NULL, null=True, blank=True, related_name='traslados_recibidos')
    subbodega_destino = models.ForeignKey(Subbodega, on_delete=models.SET_NULL, null=True, blank=True, related_name='traslados_recibidos')
    marca = models.ForeignKey(Marca, on_delete=models.SET_NULL, null=True, blank=True, related_name='movimientos')
    factura = models.ForeignKey(Factura, on_delete=models.SET_NULL, null=True, blank=True, related_name='movimientos')
    factura_manual = models.CharField(max_length=100, blank=True, null=True)
    cantidad = models.IntegerField()
    precio = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='movimientos')
    fecha = models.DateTimeField(default=timezone.now)
    tipo = models.CharField(max_length=20, choices=TIPO_MOVIMIENTO)
    observaciones = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.tipo} - {self.material.nombre} - {self.cantidad}"
