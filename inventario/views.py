from rest_framework import viewsets, response, status
from rest_framework.decorators import action
from django.db.models import Sum, Q
from .models import Bodega, Subbodega, Material, Factura, Movimiento, Marca, UnidadMedida
from .serializers import (
    BodegaSerializer, SubbodegaSerializer, MaterialSerializer, 
    FacturaSerializer, MovimientoSerializer, MarcaSerializer,
    UnidadMedidaSerializer
)

class BodegaViewSet(viewsets.ModelViewSet):
    queryset = Bodega.objects.all().order_by('nombre')

    def get_serializer_class(self):
        if self.action == 'list':
            return BodegaSimpleSerializer
        return BodegaSerializer

    def get_queryset(self):
        # By default, only show active bodegas in the list view
        queryset = super().get_queryset()
        
        if self.action == 'list':
            incluir_inactivas = self.request.query_params.get('incluir_inactivas', 'false').lower() == 'true'
            if not incluir_inactivas:
                queryset = queryset.filter(activo=True)
        
        return queryset

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
        
        # Filter by subbodega if provided (support recursive child stock)
        target_sub_id = request.query_params.get('subbodega')
        allowed_sub_ids = None # None means all subbodegas of this bodega
        
        if target_sub_id:
            try:
                target_sub = Subbodega.objects.get(id=target_sub_id, bodega=bodega)
                # Recursive search for all children
                def get_descendants(sub):
                    ids = [sub.id]
                    for child in sub.children.all():
                        ids.extend(get_descendants(child))
                    return ids
                allowed_sub_ids = get_descendants(target_sub)
            except Subbodega.DoesNotExist:
                return response.Response({"error": "Subbodega no encontrada"}, status=404)

        # Get all subbodegas for this bodega (limited if filtered)
        subbodegas_qs = bodega.subbodegas.all()
        if allowed_sub_ids is not None:
             subbodegas_qs = subbodegas_qs.filter(id__in=allowed_sub_ids)
        
        subbodegas = list(subbodegas_qs)
        inventory = {}

        # Movements where this bodega is source or destination
        movimientos = Movimiento.objects.filter(
            Q(bodega=bodega) | Q(bodega_destino=bodega)
        ).select_related('material', 'subbodega', 'subbodega_destino')
        
        if allowed_sub_ids is not None:
            movimientos = movimientos.filter(
                Q(subbodega_id__in=allowed_sub_ids) | Q(subbodega_destino_id__in=allowed_sub_ids)
            )

        for mov in movimientos:
            # Handle source
            if mov.bodega_id == bodega.id:
                sub_id = mov.subbodega_id
                if allowed_sub_ids is not None and sub_id not in allowed_sub_ids:
                    pass # Handled by the filter above but being safe
                else:
                    key = (mov.material_id, sub_id)
                    if key not in inventory:
                        inventory[key] = {'material': mov.material, 'sub_id': sub_id, 'cantidad': 0}
                    
                    if mov.tipo in ['Entrada', 'Edicion', 'Ajuste', 'Devolucion']:
                        inventory[key]['cantidad'] += mov.cantidad
                    elif mov.tipo in ['Salida', 'Traslado']:
                        inventory[key]['cantidad'] -= mov.cantidad
            
            # Handle destination
            if mov.bodega_destino_id == bodega.id:
                sub_dest_id = mov.subbodega_destino_id
                if allowed_sub_ids is not None and sub_dest_id not in allowed_sub_ids:
                    pass
                else:
                    key_dest = (mov.material_id, sub_dest_id)
                    if key_dest not in inventory:
                        inventory[key_dest] = {'material': mov.material, 'sub_id': sub_dest_id, 'cantidad': 0}
                    
                    if mov.tipo == 'Traslado':
                        inventory[key_dest]['cantidad'] += mov.cantidad

        # Map subbodega IDs to objects for easy access
        sub_map = {sb.id: sb for sb in subbodegas}

        for (mat_id, sub_id), data in inventory.items():
            if data['cantidad'] != 0:
                mat = data['material']
                qty = data['cantidad']
                sub_obj = sub_map.get(sub_id)
                resumen.append({
                    'id_material': mat.id,
                    'codigo': mat.codigo,
                    'referencia': mat.referencia,
                    'nombre': mat.nombre,
                    'cantidad': qty,
                    'unidad': mat.unidad,
                    'id_subbodega': sub_id,
                    'subbodega_nombre': sub_obj.get_full_path() if sub_obj else "General"
                })
        
        return response.Response(resumen)

class SubbodegaViewSet(viewsets.ModelViewSet):
    serializer_class = SubbodegaSerializer

    def get_queryset(self):
        queryset = Subbodega.objects.all()
        bodega_id = self.request.query_params.get('bodega')
        if bodega_id:
            queryset = queryset.filter(bodega_id=bodega_id)
        
        parent_id = self.request.query_params.get('parent')
        if parent_id:
            if parent_id == 'null':
                queryset = queryset.filter(parent__isnull=True)
            else:
                queryset = queryset.filter(parent_id=parent_id)
        
        if self.action == 'list':
            incluir_inactivas = self.request.query_params.get('incluir_inactivas', 'false').lower() == 'true'
            if not incluir_inactivas:
                queryset = queryset.filter(activo=True)
            
        return queryset.order_by('nombre')

    @action(detail=True, methods=['post'])
    def toggle_activo(self, request, pk=None):
        subbodega = self.get_object()
        subbodega.activo = not subbodega.activo
        subbodega.save()
        serializer = self.get_serializer(subbodega)
        return response.Response(serializer.data)

class MaterialViewSet(viewsets.ModelViewSet):
    queryset = Material.objects.all()
    serializer_class = MaterialSerializer

class FacturaViewSet(viewsets.ModelViewSet):
    queryset = Factura.objects.all()
    serializer_class = FacturaSerializer


class MarcaViewSet(viewsets.ModelViewSet):
    queryset = Marca.objects.all()
    serializer_class = MarcaSerializer

class UnidadMedidaViewSet(viewsets.ModelViewSet):
    queryset = UnidadMedida.objects.all()
    serializer_class = UnidadMedidaSerializer

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


class MovimientoViewSet(viewsets.ModelViewSet):
    queryset = Movimiento.objects.all().order_by('-fecha')
    serializer_class = MovimientoSerializer

    @action(detail=False, methods=['get'])
    def resumen_inventario(self, request):
        # Calculate stock per material, bodega and subbodega
        qs = Movimiento.objects.select_related('material', 'bodega', 'subbodega', 'bodega_destino', 'subbodega_destino').all()
        
        inventory = {}
        
        for mov in qs:
            # Source key: (material, bodega, subbodega)
            key = (mov.material_id, mov.bodega_id, mov.subbodega_id)
            if key not in inventory:
                inventory[key] = {
                    'material': mov.material,
                    'bodega': mov.bodega,
                    'subbodega': mov.subbodega,
                    'cantidad': 0
                }
            
            if mov.tipo in ['Entrada', 'Edicion', 'Ajuste', 'Devolucion']:
                inventory[key]['cantidad'] += mov.cantidad
            elif mov.tipo == 'Salida':
                inventory[key]['cantidad'] -= mov.cantidad
            elif mov.tipo == 'Traslado':
                # Subtract from source
                inventory[key]['cantidad'] -= mov.cantidad
                # Add to destination
                dest_key = (mov.material_id, mov.bodega_destino_id, mov.subbodega_destino_id)
                if dest_key not in inventory:
                    inventory[dest_key] = {
                        'material': mov.material,
                        'bodega': mov.bodega_destino,
                        'subbodega': mov.subbodega_destino,
                        'cantidad': 0
                    }
                inventory[dest_key]['cantidad'] += mov.cantidad
        
        resumen = []
        for (mat_id, bod_id, sub_id), data in inventory.items():
            if data['cantidad'] != 0:
                mat = data['material']
                bod = data['bodega']
                sub = data['subbodega']
                qty = data['cantidad']
                resumen.append({
                    'id_material': mat.id,
                    'codigo': mat.codigo,
                    'referencia': mat.referencia,
                    'nombre': mat.nombre,
                    'id_bodega': bod.id,
                    'bodega': bod.nombre,
                    'id_subbodega': sub.id if sub else None,
                    'subbodega': sub.get_full_path() if sub else "General",
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
        movimiento = serializer.save(usuario=self.request.user)
        
        material = movimiento.material
        should_save_material = False

        # V2 Logic: Update Material fields on Entry
        if movimiento.tipo == 'Entrada':
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
