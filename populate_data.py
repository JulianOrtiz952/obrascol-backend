import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from inventario.models import Material, Bodega

def populate():
    # Bodegas
    b1, _ = Bodega.objects.get_or_create(nombre='Bodega Principal', ubicacion='Sede Norte')
    b2, _ = Bodega.objects.get_or_create(nombre='Bodega Secundaria', ubicacion='Sede Sur')
    Bodega.objects.get_or_create(nombre='En Tránsito')

    # Materiales
    mats = [
        {'codigo': 'MAQ-001', 'codigo_barras': '7701234567890', 'referencia': 'REF-2024-001', 'nombre': 'Tornillo M12x50', 'unidad': 'pcs'},
        {'codigo': 'MAQ-002', 'codigo_barras': '7709876543210', 'referencia': 'REF-2024-002', 'nombre': 'Rodamiento SKF 6205', 'unidad': 'pcs'},
        {'codigo': 'MAQ-003', 'codigo_barras': '7705556667778', 'referencia': 'REF-2024-003', 'nombre': 'Correa transportadora 3m', 'unidad': 'm'},
        {'codigo': 'MAQ-004', 'codigo_barras': '7701112223334', 'referencia': 'REF-2024-004', 'nombre': 'Aceite hidráulico 20L', 'unidad': 'L'},
        {'codigo': 'MAQ-005', 'codigo_barras': '7704445556667', 'referencia': 'REF-2024-005', 'nombre': 'Filtro de aire industrial', 'unidad': 'pcs'},
        {'codigo': 'MAQ-006', 'codigo_barras': '7707778889990', 'referencia': 'REF-2024-006', 'nombre': 'Válvula neumática 1/2', 'unidad': 'pcs'},
    ]

    for m in mats:
        mat, created = Material.objects.get_or_create(codigo=m['codigo'], defaults=m)
        if not created:
            for key, value in m.items():
                setattr(mat, key, value)
            mat.save()

    print("Initial data populated successfully!")

if __name__ == '__main__':
    populate()
