from rest_framework import viewsets, response, status
from rest_framework.decorators import action
from django.db.models import Sum
from .models import Bodega, Material, Factura, Movimiento
from .serializers import (
    BodegaSerializer, MaterialSerializer, 
    FacturaSerializer, MovimientoSerializer
)

class BodegaViewSet(viewsets.ModelViewSet):
    serializer_class = BodegaSerializer

    def get_queryset(self):
        # By default, only show active bodegas in the list view
        queryset = Bodega.objects.all()
        
        if self.action == 'list':
            incluir_inactivas = self.request.query_params.get('incluir_inactivas', 'false').lower() == 'true'
            if not incluir_inactivas:
                queryset = queryset.filter(activo=True)
        
        return queryset.order_by('nombre')

    @action(detail=True, methods=['post'])
    def toggle_activo(self, request, pk=None):
        """Toggle the activo status of a bodega"""
        bodega = self.get_object()
        bodega.activo = not bodega.activo
        bodega.save()
        serializer = self.get_serializer(bodega)
        return response.Response(serializer.data)

    @action(detail=True, methods=['get'])
    def stock_actual(self, request, pk=None):
        bodega = self.get_object()
        resumen = []
        # Optimize: Only get materials that have movements in this bodega
        material_ids = Movimiento.objects.filter(bodega=bodega).values_list('material', flat=True).distinct()
        materiales = Material.objects.filter(id__in=material_ids)

        for mat in materiales:
            qs = Movimiento.objects.filter(material=mat, bodega=bodega)
            if qs.exists():
                total = 0
                for mov in qs:
                    if mov.tipo in ['Entrada', 'Edicion', 'Ajuste', 'Devolucion']:
                        total += mov.cantidad
                    elif mov.tipo == 'Salida':
                        total -= mov.cantidad
                
                if total > 0:
                    resumen.append({
                        'id_material': mat.id,
                        'codigo': mat.codigo,
                        'referencia': mat.referencia,
                        'nombre': mat.nombre,
                        'cantidad': total,
                        'unidad': mat.unidad
                    })
        return response.Response(resumen)

class MaterialViewSet(viewsets.ModelViewSet):
    queryset = Material.objects.all()
    serializer_class = MaterialSerializer

class FacturaViewSet(viewsets.ModelViewSet):
    queryset = Factura.objects.all()
    serializer_class = FacturaSerializer

class MovimientoViewSet(viewsets.ModelViewSet):
    queryset = Movimiento.objects.all().order_by('-fecha')
    serializer_class = MovimientoSerializer

    @action(detail=False, methods=['get'])
    def resumen_inventario(self, request):
        # Calculate stock per material and bodega
        # Stock = Sum of (Entrada, Edicion, Ajuste, Devolucion) - Sum of (Salida)
        # For simplicity, we can just treat quantities as signed if we want, 
        # but here we'll handle the logic.
        
        # We want a list of {material, bodega, cantidad_total}
        resumen = []
        # Optimize: Fetch all movements at once to avoid N*M queries
        qs = Movimiento.objects.select_related('material', 'bodega').all()
        
        inventory = {}
        
        for mov in qs:
            key = (mov.material.id, mov.bodega.id)
            if key not in inventory:
                inventory[key] = {
                    'material': mov.material,
                    'bodega': mov.bodega,
                    'cantidad': 0
                }
            
            if mov.tipo in ['Entrada', 'Edicion', 'Ajuste', 'Devolucion']:
                inventory[key]['cantidad'] += mov.cantidad
            elif mov.tipo == 'Salida':
                inventory[key]['cantidad'] -= mov.cantidad
        
        resumen = []
        for (mat_id, bod_id), data in inventory.items():
            if data['cantidad'] != 0:
                mat = data['material']
                bod = data['bodega']
                qty = data['cantidad']
                resumen.append({
                    'id_material': mat.id,
                    'codigo': mat.codigo,
                    'referencia': mat.referencia,
                    'nombre': mat.nombre,
                    'id_bodega': bod.id,
                    'bodega': bod.nombre,
                    'cantidad': qty,
                    'unidad': mat.unidad,
                    'estado': self._get_estado(qty)
                })
        
        return response.Response(resumen)

    def _get_estado(self, cantidad):
        if cantidad > 100:
            return 'Alto'
        elif cantidad > 20:
            return 'Medio'
        else:
            return 'Bajo'
