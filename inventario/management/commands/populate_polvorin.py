import random
from datetime import timedelta
from django.utils import timezone
from django.core.management.base import BaseCommand
from inventario.models import Bodega, Subbodega, Material, Movimiento
from django.contrib.auth import get_user_model

class Command(BaseCommand):
    help = 'Popula la bodega Polvorin con estantes, filas y 1000 movimientos de entrada de prueba'

    def handle(self, *args, **kwargs):
        User = get_user_model()
        user = User.objects.filter(is_superuser=True).first() or User.objects.first()

        materials = list(Material.objects.all())
        if not materials:
            self.stdout.write(self.style.WARNING("No hay materiales en la BD, se creará uno de prueba."))
            mat = Material.objects.create(nombre="Material Prueba", codigo="PRU01", unidad="Und")
            materials = [mat]

        # 1. Crear Bodega
        bodega, created = Bodega.objects.get_or_create(nombre="POLVORIN", defaults={"ubicacion": "Sede Principal"})
        if created:
            self.stdout.write(self.style.SUCCESS('Bodega "POLVORIN" creada.'))
        else:
            self.stdout.write('Bodega "POLVORIN" ya existe.')

        # 2. Crear Estantes y Filas
        filas_creadas = []
        for n in range(1, 9):
            for letra in ['A', 'B', 'C', 'D']:
                estante_nombre = f"ESTANTE {n}{letra}"
                estante, est_created = Subbodega.objects.get_or_create(
                    nombre=estante_nombre, 
                    bodega=bodega, 
                    parent=None
                )
                
                for f in range(1, 6):
                    fila_nombre = f"FILA {f}"
                    fila, fila_created = Subbodega.objects.get_or_create(
                        nombre=fila_nombre,
                        bodega=bodega,
                        parent=estante
                    )
                    filas_creadas.append(fila)

        self.stdout.write(self.style.SUCCESS(f'Asegurados {len(filas_creadas)} filas distribuídas en 32 estantes.'))

        # 3. Crear Movimientos
        if Movimiento.objects.filter(bodega=bodega, observaciones="POBLADO_AUTOMATICO").exists():
            self.stdout.write(self.style.WARNING('Ya existen movimientos generados automáticamente en POLVORIN. Si quieres agregar más, borra o edita la observación de los anteriores. Saliendo para evitar duplicados en producción...'))
            return

        self.stdout.write('Generando 1000 movimientos de Entrada...')
        movimientos_a_crear = []
        now = timezone.now()

        for _ in range(1000):
            mat = random.choice(materials)
            fila = random.choice(filas_creadas)
            cant = random.randint(5, 500)
            
            # spread in the past 120 days
            dias_atras = random.randint(0, 120)
            fecha_mov = now - timedelta(days=dias_atras)

            mov = Movimiento(
                tipo='Entrada',
                material=mat,
                bodega=bodega,
                subbodega=fila,
                cantidad=cant,
                usuario=user,
                observaciones='POBLADO_AUTOMATICO',
                fecha=fecha_mov
            )
            movimientos_a_crear.append(mov)

        # Bulk create es mejor para rendimiento
        Movimiento.objects.bulk_create(movimientos_a_crear)
        
        self.stdout.write(self.style.SUCCESS(f'¡1000 movimientos de entrada creados con éxito en POLVORIN para {len(materials)} materiales diferentes!'))
