import os
import django
import random
from datetime import timedelta

def run():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
    django.setup()
    
    from django.utils import timezone
    from inventario.models import Bodega, Subbodega, Material, Movimiento
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    user = User.objects.filter(is_superuser=True).first() or User.objects.first()

    materials = list(Material.objects.all())
    if not materials:
        print("WARN: No hay materiales en la BD, se creará uno de prueba.")
        mat = Material.objects.create(nombre="Material Prueba", codigo="PRU01", unidad="Und")
        materials = [mat]

    bodega, created = Bodega.objects.get_or_create(nombre="POLVORIN", defaults={"ubicacion": "Sede Principal"})
    if created:
        print('SUCCESS: Bodega "POLVORIN" creada.')
    else:
        print('INFO: Bodega "POLVORIN" ya existe.')

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

    print(f'SUCCESS: Asegurados {len(filas_creadas)} filas distribuídas en 32 estantes.')

    if Movimiento.objects.filter(bodega=bodega, observaciones="POBLADO_AUTOMATICO").exists():
        print('WARN: Ya existen movimientos generados automáticamente en POLVORIN. Evitando duplicados...')
        return

    print('INFO: Generando 1000 movimientos de Entrada...')
    movimientos_a_crear = []
    now = timezone.now()

    for _ in range(1000):
        mat = random.choice(materials)
        fila = random.choice(filas_creadas)
        cant = random.randint(5, 500)
        
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

    Movimiento.objects.bulk_create(movimientos_a_crear)
    print(f'SUCCESS: ¡1000 movimientos de entrada creados con éxito en POLVORIN para {len(materials)} materiales diferentes!')

if __name__ == '__main__':
    run()
