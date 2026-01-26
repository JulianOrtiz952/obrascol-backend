from rest_framework import viewsets, response, status
from rest_framework.decorators import action
from django.db.models import Sum
from .models import Bodega, Material, Factura, Movimiento, Marca
from .serializers import (
    BodegaSerializer, MaterialSerializer, 
    FacturaSerializer, MovimientoSerializer, MarcaSerializer
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


class MarcaViewSet(viewsets.ModelViewSet):
    queryset = Marca.objects.all()
    serializer_class = MarcaSerializer

class ReportesViewSet(viewsets.ViewSet):
    """
    ViewSet for generating reports and statistics.
    """
    
    @action(detail=False, methods=['get'])
    def resumen_general(self, request):
        total_entradas = Movimiento.objects.filter(tipo='Entrada').count()
        total_salidas = Movimiento.objects.filter(tipo='Salida').count()
        total_marcas = Marca.objects.filter(activo=True).count()
        
        # Calculate total stock value? Maybe later if we have cost.
        # For now just simple counters
        
        return response.Response({
            'total_entradas': total_entradas,
            'total_salidas': total_salidas,
            'total_marcas_activas': total_marcas,
        })

    @action(detail=False, methods=['get'])
    def top_marcas_entradas(self, request):
        return self._get_top_marcas(tipo_movimiento='Entrada')

    @action(detail=False, methods=['get'])
    def top_marcas_salidas(self, request):
        # Note: Salidas might not always have marca if not enforced, 
        # but we'll query what we have.
        return self._get_top_marcas(tipo_movimiento='Salida')

    def _get_top_marcas(self, tipo_movimiento):
        from django.db.models import Count, Sum
        
        # Aggregate by brand
        data = (
            Movimiento.objects
            .filter(tipo=tipo_movimiento, marca__isnull=False)
            .values('marca__nombre')
            .annotate(
                total_movimientos=Count('id'),
                total_cantidad=Sum('cantidad')
            )
            .order_by('-total_cantidad')[:5]
        )
        
        return response.Response(data)

    @action(detail=False, methods=['get'])
    def productos_promedio(self, request):
        """
        Returns a list of products with their average price based on entries.
        """
        from django.db.models import Avg, F
        
        # Group by material and calculate average price of 'Entrada' movements
        data = (
            Movimiento.objects
            .filter(tipo='Entrada')
            .values(
                'material__id', 
                'material__codigo', 
                'material__nombre', 
                'material__marca__nombre'
            )
            .annotate(precio_promedio=Avg('precio'))
            .order_by('material__nombre')
        )
        
        results = []
        for item in data:
            results.append({
                'id_material': item['material__id'],
                'codigo': item['material__codigo'],
                'nombre': item['material__nombre'],
                'marca': item['material__marca__nombre'] or 'Sin Marca',
                'precio_promedio': round(item['precio_promedio'], 2) if item['precio_promedio'] else 0
            })
            
        return response.Response(results)

class MovimientoViewSet(viewsets.ModelViewSet):
    queryset = Movimiento.objects.all().order_by('-fecha')
    serializer_class = MovimientoSerializer

    @action(detail=False, methods=['get'])
    def resumen_inventario(self, request):
        # Calculate stock per material and bodega
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

    def perform_create(self, serializer):
        movimiento = serializer.save()
        
        material = movimiento.material
        should_save_material = False

        # V2 Logic: Update Material fields on Entry
        if movimiento.tipo == 'Entrada':
            # Update last price
            if movimiento.precio:
                material.ultimo_precio = movimiento.precio
                should_save_material = True
            
            # Update brand if provided
            if movimiento.marca:
                material.marca = movimiento.marca
                should_save_material = True

        # V2 Logic: For Salida (or others), inherit brand from material if not set
        elif movimiento.tipo == 'Salida':
            if not movimiento.marca and material.marca:
                movimiento.marca = material.marca
                movimiento.save()
        
        if should_save_material:
            material.save()
