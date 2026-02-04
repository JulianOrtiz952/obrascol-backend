import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from inventario.models import UnidadMedida

def populate_units():
    units = [
        {'nombre': 'Horas', 'abreviacion': 'h'},
        {'nombre': 'Kilómetros', 'abreviacion': 'km'},
        {'nombre': 'Litros', 'abreviacion': 'L'},
        {'nombre': 'Galones', 'abreviacion': 'gal'},
        {'nombre': 'Unidades', 'abreviacion': 'ud'},
        {'nombre': 'Kilogramos', 'abreviacion': 'kg'},
        {'nombre': 'Metros', 'abreviacion': 'm'},
        {'nombre': 'Pulgadas', 'abreviacion': 'pulg'},
        {'nombre': 'Centímetros', 'abreviacion': 'cm'},
        {'nombre': 'Milímetros', 'abreviacion': 'mm'},
        {'nombre': 'Hectáreas', 'abreviacion': 'ha'},
        {'nombre': 'Toneladas', 'abreviacion': 'ton'},
        {'nombre': 'PSI', 'abreviacion': 'psi'},
        {'nombre': 'Voltios', 'abreviacion': 'V'},
        {'nombre': 'Amperios', 'abreviacion': 'A'},
        {'nombre': 'Watts', 'abreviacion': 'W'},
        {'nombre': 'Revoluciones por minuto', 'abreviacion': 'RPM'},
        {'nombre': 'Ciclos', 'abreviacion': 'cic'},
        {'nombre': 'Meses', 'abreviacion': 'mes'},
        {'nombre': 'Días', 'abreviacion': 'día'},
    ]

    for u in units:
        obj, created = UnidadMedida.objects.get_or_create(
            abreviacion=u['abreviacion'],
            defaults={'nombre': u['nombre']}
        )
        if created:
            print(f"Created unit: {u['nombre']} ({u['abreviacion']})")
        else:
            # Update name if it already exists but has different name
            if obj.nombre != u['nombre']:
                obj.nombre = u['nombre']
                obj.save()
                print(f"Updated unit: {u['nombre']} ({u['abreviacion']})")
            else:
                print(f"Unit already exists: {u['nombre']} ({u['abreviacion']})")

if __name__ == '__main__':
    populate_units()
    print("Units population complete!")
