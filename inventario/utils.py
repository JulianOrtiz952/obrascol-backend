import openpyxl
from io import BytesIO
from .models import Bodega, Subbodega, Material, Marca, Factura, Movimiento, UnidadMedida

def export_all_data_to_excel():
    output = BytesIO()
    wb = openpyxl.Workbook()
    
    # Remove default sheet
    default_sheet = wb.active
    wb.remove(default_sheet)
    
    # helper for adding sheets
    def add_sheet(name, queryset, fields, header_names=None):
        ws = wb.create_sheet(title=name)
        headers = header_names if header_names else [f.replace('_', ' ').title() for f in fields]
        ws.append(headers)
        
        for obj in queryset:
            row = []
            for field in fields:
                val = getattr(obj, field)
                # Handle foreign keys or special types
                if hasattr(val, '__str__') and not isinstance(val, (str, int, float, bool, type(None))):
                    row.append(str(val))
                else:
                    row.append(val)
            ws.append(row)

    # 1. Bodegas
    add_sheet(
        "Bodegas", 
        Bodega.objects.all(), 
        ['id', 'nombre', 'ubicacion', 'activo']
    )

    # 2. Subbodegas
    add_sheet(
        "Subbodegas",
        Subbodega.objects.select_related('bodega', 'parent').all(),
        ['id', 'nombre', 'bodega', 'parent', 'activo'],
        ['ID', 'Nombre', 'Bodega Padre', 'Subbodega Padre', 'Activo']
    )

    # 3. Materiales
    add_sheet(
        "Materiales",
        Material.objects.select_related('marca').all(),
        ['id', 'codigo', 'codigo_barras', 'referencia', 'nombre', 'unidad', 'marca'],
        ['ID', 'Código', 'Código Barras', 'Referencia', 'Nombre', 'Unidad', 'Marca']
    )

    # 4. Marcas
    add_sheet(
        "Marcas",
        Marca.objects.all(),
        ['id', 'nombre', 'activo']
    )

    # 5. Facturas
    add_sheet(
        "Facturas",
        Factura.objects.all(),
        ['id', 'numero', 'proveedor', 'fecha']
    )

    # 6. Movimientos (Kardex)
    add_sheet(
        "Movimientos",
        Movimiento.objects.select_related(
            'material', 'bodega', 'subbodega', 'bodega_destino', 
            'subbodega_destino', 'marca', 'factura', 'usuario'
        ).all().order_by('-fecha'),
        ['id', 'fecha', 'tipo', 'material', 'cantidad', 'bodega', 'subbodega', 'bodega_destino', 'subbodega_destino', 'marca', 'factura_manual', 'observaciones', 'usuario'],
        ['ID', 'Fecha', 'Tipo', 'Material', 'Cantidad', 'Bodega', 'Subbodega', 'Bodega Destino', 'Subbodega Destino', 'Marca', 'Factura Manual', 'Observaciones', 'Usuario']
    )

    wb.save(output)
    output.seek(0)
    return output
