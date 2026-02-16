import os
import django
import random
from django.utils import timezone
from datetime import timedelta

# Setup Django Environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from inventario.models import Bodega, Subbodega, Material, Marca, UnidadMedida, Movimiento
from usuarios.models import Usuario

def populate():
    print("Iniciando poblamiento de base de datos...")

    # 1. Crear Unidades de Medida
    unidades_data = [
        ('Unidad', 'und'),
        ('Kilogramo', 'kg'),
        ('Gramo', 'g'),
        ('Metro', 'm'),
        ('Centímetro', 'cm'),
        ('Litro', 'L'),
        ('Galón', 'gal'),
        ('Paquete', 'paq'),
        ('Caja', 'caja'),
        ('Bulto', 'bulto'),
    ]
    unidades = []
    for nombre, abrev in unidades_data:
        u, _ = UnidadMedida.objects.get_or_create(nombre=nombre, abreviacion=abrev)
        unidades.append(u)
    print(f"Creadas {len(unidades)} unidades de medida.")

    # 2. Crear Marcas (Categorías)
    marcas_nombres = ['Sika', 'Argos', 'Pavinco', 'Gerfor', 'Hilti', 'DeWalt', 'Makita', 'Bosch', '3M', 'Generico']
    marcas = []
    for nombre in marcas_nombres:
        m, _ = Marca.objects.get_or_create(nombre=nombre)
        marcas.append(m)
    print(f"Creadas {len(marcas)} marcas.")

    # 3. Crear Usuarios
    usuarios = []
    roles = ['operario', 'administrativo', 'superusuario']
    for i in range(1, 6):
        username = f'usuario{i}'
        user, created = Usuario.objects.get_or_create(
            username=username,
            defaults={
                'email': f'{username}@obrascol.com',
                'rol': random.choice(roles),
                'first_name': f'Usuario {i}',
                'last_name': 'Prueba'
            }
        )
        if created:
            user.set_password('volcan2026')
            user.save()
        usuarios.append(user)
    print(f"Creados/Verificados {len(usuarios)} usuarios.")

    # 4. Crear Bodegas Principales
    bodegas_nombres = ['POLVORIN', 'COCINA', 'TALLER']
    bodegas = {}
    for nombre in bodegas_nombres:
        b, _ = Bodega.objects.get_or_create(nombre=nombre, defaults={'ubicacion': 'Sede Principal'})
        bodegas[nombre] = b
    print(f"Creadas {len(bodegas)} bodegas principales.")

    # 5. Estructura Compleja POLVORIN (32 Estantes y 5 Filas c/u)
    polvorin = bodegas['POLVORIN']
    subbodegas_pool = []
    
    # Letras A-D, Números 1-8 = 32 Estantes
    letras = ['A', 'B', 'C', 'D']
    numeros = range(1, 9) 
    
    print("Generando jerarquía de POLVORIN (160 sub-ubicaciones)...")
    for num in numeros:
        for letra in letras:
            estante_nombre = f"ESTANTE {num}{letra}"
            estante, _ = Subbodega.objects.get_or_create(
                nombre=estante_nombre,
                bodega=polvorin,
                parent=None
            )
            
            # Crear 5 Filas por cada Estante
            for f in range(1, 6):
                fila_nombre = f"FILA {f}"
                fila, _ = Subbodega.objects.get_or_create(
                    nombre=fila_nombre,
                    bodega=polvorin,
                    parent=estante
                )
                subbodegas_pool.append(fila)

    # Añadir subbodegas simples para Cocina y Taller
    for b_name in ['COCINA', 'TALLER']:
        general, _ = Subbodega.objects.get_or_create(nombre='GENERAL', bodega=bodegas[b_name])
        subbodegas_pool.append(general)

    # 6. Crear Materiales (Catálogo)
    materiales_data = [
        ('CEMENTO-01', 'Cemento Gris 50kg', 'Argos', 'Bulto'),
        ('ADIT-02', 'Sika-1 Impermeabilizante', 'Sika', 'Galón'),
        ('TUBO-03', 'Tubo PVC 1/2" 6m', 'Gerfor', 'Metro'),
        ('TAL-04', 'Taladro Percutor 20V', 'DeWalt', 'Unidad'),
        ('GUA-05', 'Guantes de Nitrilo', '3M', 'Paquete'),
        ('PIN-06', 'Pintura Acrílica Blanca', 'Generico', 'Galón'),
        ('TOR-07', 'Tornillo Drywall 1"', 'Generico', 'Caja'),
        ('BRO-08', 'Broca Concreto 1/4"', 'Bosch', 'Unidad'),
        ('DIS-09', 'Disco Corte Acero 4.5"', 'Makita', 'Unidad'),
        ('CAS-10', 'Casco de Seguridad', 'Generico', 'Unidad'),
    ]
    catalogo = []
    for cod, nom, marc_nom, uni_abrev in materiales_data:
        m, _ = Material.objects.get_or_create(
            codigo=cod,
            defaults={
                'nombre': nom,
                'marca': Marca.objects.get(nombre=marc_nom),
                'unidad': uni_abrev,
                'ultimo_precio': random.randint(5000, 500000)
            }
        )
        catalogo.append(m)
    print(f"Creados {len(catalogo)} materiales en el catálogo.")

    # 7. Generar 300 Movimientos de Entrada
    if Movimiento.objects.count() == 0:
        print("Registrando 300 entradas de stock...")
        for i in range(300):
            mat = random.choice(catalogo)
            sub = random.choice(subbodegas_pool)
            user = random.choice(usuarios)
            
            # Fecha aleatoria en los últimos 30 días
            fecha = timezone.now() - timedelta(days=random.randint(0, 30), hours=random.randint(0, 23))
            
            Movimiento.objects.create(
                material=mat,
                bodega=sub.bodega,
                subbodega=sub,
                usuario=user,
                cantidad=random.randint(1, 100),
                precio=mat.ultimo_precio,
                tipo='Entrada',
                fecha=fecha,
                observaciones=f"Carga inicial de datos de prueba #{i+1}"
            )
            if (i+1) % 50 == 0:
                print(f"  -> {i+1} movimientos registrados...")
    else:
        print("Omitiendo creación de movimientos: Ya existen registros en la base de datos.")

    print("\n¡Poblamiento completado con éxito!")
    print(f"Total Bodegas: {Bodega.objects.count()}")
    print(f"Total Subbodegas: {Subbodega.objects.count()}")
    print(f"Total Movimientos (Entradas): {Movimiento.objects.count()}")

if __name__ == "__main__":
    populate()
