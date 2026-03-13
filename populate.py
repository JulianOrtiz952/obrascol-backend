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
    
    # Check and create default superuser
    if not User.objects.filter(is_superuser=True).exists():
        print("INFO: No hay súper usuarios. Creando usuario por defecto 'volcan'.")
        user = User.objects.create_superuser(
            username='volcan', 
            email='admin@obrascol.com', 
            password='volcanpassword123',
            rol='superusuario'
        )
        print("SUCCESS: Usuario 'volcan' creado con contraseña 'volcanpassword123'.")
    else:
        user = User.objects.filter(is_superuser=True).first()

    print("INFO: Eliminando materiales y movimientos de prueba antiguos para reemplazarlos con reales...")
    Movimiento.objects.filter(observaciones="POBLADO_AUTOMATICO").delete()
    Material.objects.filter(nombre="Material Prueba").delete()

    material_data = [
        {"codigo": "EPI001", "nombre": "Guantes de carnaza", "unidad": "Par"},
        {"codigo": "EPI002", "nombre": "Guantes de nitrilo", "unidad": "Par"},
        {"codigo": "EPI003", "nombre": "Botas pantaneras", "unidad": "Par"},
        {"codigo": "EPI004", "nombre": "Botas de seguridad", "unidad": "Par"},
        {"codigo": "EPI005", "nombre": "Casco de seguridad", "unidad": "Unidad"},
        {"codigo": "EPI006", "nombre": "Gafas de protección", "unidad": "Unidad"},
        {"codigo": "INS001", "nombre": "ACPM", "unidad": "Galon"},
        {"codigo": "INS002", "nombre": "Grasa para maquinaria", "unidad": "Cuñete"},
        {"codigo": "INS003", "nombre": "Aceite hidráulico", "unidad": "Balde"},
        {"codigo": "INS004", "nombre": "Pintura amarilla tráfico", "unidad": "Cuñete"},
        {"codigo": "INS005", "nombre": "Pintura blanca", "unidad": "Galon"},
        {"codigo": "HER001", "nombre": "Brocha 4 pulgadas", "unidad": "Unidad"},
        {"codigo": "HER002", "nombre": "Disco de corte 4.5\"", "unidad": "Unidad"},
        {"codigo": "HER004", "nombre": "Electrodos 6013", "unidad": "Caja"},
        {"codigo": "MAT001", "nombre": "Cemento gris", "unidad": "Bulto"},
        {"codigo": "MAT003", "nombre": "Alambre dulce negro", "unidad": "Kilo"},
        {"codigo": "MAT004", "nombre": "Cinta de precaución", "unidad": "Rollo"},
        {"codigo": "INS006", "nombre": "Sikaflex", "unidad": "Tubo"},
        {"codigo": "HER005", "nombre": "Pala cuadrada", "unidad": "Unidad"},
        {"codigo": "HER006", "nombre": "Pica", "unidad": "Unidad"},
    ]

    materials = []
    for m in material_data:
        mat, _ = Material.objects.get_or_create(codigo=m["codigo"], defaults={"nombre": m["nombre"], "unidad": m["unidad"]})
        materials.append(mat)


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

    # Se omitió el checkeo de existencia previa para regenerar idempotentemente

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
