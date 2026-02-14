import os
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from inventario.models import Bodega, Subbodega, Movimiento

def migrate_data():
    print("Starting data migration for sub-warehouses...")
    
    # 1. Ensure a "General" sub-warehouse exists for each warehouse
    bodegas = Bodega.objects.all()
    for bodega in bodegas:
        general, created = Subbodega.objects.get_or_create(
            bodega=bodega,
            nombre="General",
            defaults={'activo': True}
        )
        if created:
            print(f"Created 'General' sub-warehouse for {bodega.nombre}")
        else:
            print(f"'General' sub-warehouse already exists for {bodega.nombre}")

    # 2. Link existing movements without a sub-warehouse to the "General" one
    # Note: We need to check both origin and destination sub-warehouses
    
    movements_origin = Movimiento.objects.filter(subbodega__isnull=True)
    count_origin = 0
    for mov in movements_origin:
        general = Subbodega.objects.get(bodega=mov.bodega, nombre="General")
        mov.subbodega = general
        mov.save()
        count_origin += 1
    
    movements_dest = Movimiento.objects.filter(tipo='Traslado', subbodega_destino__isnull=True)
    count_dest = 0
    for mov in movements_dest:
        if mov.bodega_destino:
            general = Subbodega.objects.get(bodega=mov.bodega_destino, nombre="General")
            mov.subbodega_destino = general
            mov.save()
            count_dest += 1
    
    print(f"Migration completed. Updated {count_origin} origin links and {count_dest} destination links.")

if __name__ == "__main__":
    migrate_data()
