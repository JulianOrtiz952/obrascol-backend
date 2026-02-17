import os
import django
import random
from django.utils import timezone
from datetime import timedelta

# Setup Django Environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.conf import settings
from inventario.models import Bodega, Subbodega, Material, Marca, UnidadMedida, Movimiento
from usuarios.models import Usuario

def populate():
    print("=== DEBUG OBRASCOL POPULATE ===")
    print(f"Target Database: {settings.DATABASES['default'].get('NAME', 'Unknown')}")
    print(f"Host: {settings.DATABASES['default'].get('HOST', 'localhost')}")
    print("===============================")
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
        # Check by abbreviation first as it's the more common identifier
        u = UnidadMedida.objects.filter(abreviacion=abrev).first()
        if not u:
            # Check by name just in case
            u = UnidadMedida.objects.filter(nombre=nombre).first()
        
        if not u:
            u = UnidadMedida.objects.create(nombre=nombre, abreviacion=abrev)
        unidades.append(u)
    print(f"Creadas {len(unidades)} unidades de medida.")

    # 2. Crear Marcas (Categorías)
    marcas_nombres = ['Sika', 'Argos', 'Pavinco', 'Gerfor', 'Hilti', 'DeWalt', 'Makita', 'Bosch', '3M', 'Generico']
    marcas = []
    for nombre in marcas_nombres:
        m = Marca.objects.filter(nombre=nombre).first()
        if not m:
            m = Marca.objects.create(nombre=nombre)
        marcas.append(m)
    print(f"Creadas {len(marcas)} marcas.")

    # 3. Crear Usuarios
    usuarios = []
    roles = ['operario', 'administrativo', 'superusuario']
    for i in range(1, 6):
        username = f'usuario{i}'
        user = Usuario.objects.filter(username=username).first()
        if not user:
            user = Usuario.objects.create(
                username=username,
                email=f'{username}@obrascol.com',
                rol=random.choice(roles),
                first_name=f'Usuario {i}',
                last_name='Prueba'
            )
            user.set_password('volcan2026')
            user.save()
        usuarios.append(user)
    print(f"Creados/Verificados {len(usuarios)} usuarios.")

    # 4. Crear Bodegas Principales
    bodegas_nombres = ['POLVORIN', 'COCINA', 'TALLER']
    bodegas = {}
    for nombre in bodegas_nombres:
        b = Bodega.objects.filter(nombre=nombre).first()
        if not b:
            b = Bodega.objects.create(nombre=nombre, ubicacion='Sede Principal')
        else:
            # Update location if it exists but is different/empty
            if b.ubicacion != 'Sede Principal':
                b.ubicacion = 'Sede Principal'
                b.save()
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
            estante = Subbodega.objects.filter(nombre=estante_nombre, bodega=polvorin, parent=None).first()
            if not estante:
                estante = Subbodega.objects.create(
                    nombre=estante_nombre,
                    bodega=polvorin,
                    parent=None
                )
            
            # Crear 5 Filas por cada Estante
            for f in range(1, 6):
                fila_nombre = f"FILA {f}"
                fila = Subbodega.objects.filter(nombre=fila_nombre, bodega=polvorin, parent=estante).first()
                if not fila:
                    fila = Subbodega.objects.create(
                        nombre=fila_nombre,
                        bodega=polvorin,
                        parent=estante
                    )
                subbodegas_pool.append(fila)

    # Añadir subbodegas simples para Cocina y Taller
    for b_name in ['COCINA', 'TALLER']:
        b = bodegas[b_name]
        general = Subbodega.objects.filter(nombre='GENERAL', bodega=b).first()
        if not general:
            general = Subbodega.objects.create(nombre='GENERAL', bodega=b)
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
        m = Material.objects.filter(codigo=cod).first()
        if not m:
            m = Material.objects.create(
                codigo=cod,
                nombre=nom,
                marca=Marca.objects.get(nombre=marc_nom),
                unidad=uni_abrev
            )
        catalogo.append(m)
    print(f"Creados {len(catalogo)} materiales en el catálogo.")

    # Diagnostic: Current Counts
    print(f"Estado actual: Movimientos={Movimiento.objects.count()}, Subbodegas={Subbodega.objects.count()}")

    # 7. Generar 300 Movimientos de Entrada
    # We'll check if we already have our specific test movements to avoid duplicates on every build
    test_movs_count = Movimiento.objects.filter(observaciones__icontains="Carga inicial de datos de prueba").count()
    
    if test_movs_count < 300:
        print(f"Registrando {300 - test_movs_count} entradas de stock faltantes...")
        for i in range(test_movs_count, 300):
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
                tipo='Entrada',
                fecha=fecha,
                observaciones=f"Carga inicial de datos de prueba #{i+1}"
            )
            if (i+1) % 50 == 0:
                print(f"  -> {i+1} movimientos registrados...")
    else:
        print("Ya existen los 300 movimientos de prueba en la base de datos.")

    print("\n¡Poblamiento completado con éxito!")
    print(f"Total Bodegas: {Bodega.objects.count()}")
    print(f"Total Subbodegas: {Subbodega.objects.count()}")
    print(f"Total Movimientos (Entradas): {Movimiento.objects.count()}")

if __name__ == "__main__":
    populate()
