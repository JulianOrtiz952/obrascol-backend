from rest_framework import viewsets, response, status
from rest_framework.decorators import action
from django.db.models import Sum, Q
from .models import Bodega, Subbodega, Material, Factura, Movimiento, Marca, UnidadMedida
from .serializers import (
    BodegaSerializer, BodegaSimpleSerializer, SubbodegaSerializer, 
    MaterialSerializer, FacturaSerializer, MovimientoSerializer, 
    MarcaSerializer, UnidadMedidaSerializer
)
from .utils import export_all_data_to_excel, import_all_data_from_excel
from django.http import FileResponse

class BodegaViewSet(viewsets.ModelViewSet):
    queryset = Bodega.objects.prefetch_related('subbodegas').all().order_by('nombre')

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
        
        # Filter by subbodega if provided (support recursive child stock)
        target_sub_id = request.query_params.get('subbodega')
        allowed_sub_ids = None 
        
        if target_sub_id:
            try:
                target_sub = Subbodega.objects.get(id=target_sub_id, bodega=bodega)
                def get_descendants(sub):
                    ids = [sub.id]
                    for child in sub.children.all():
                        ids.extend(get_descendants(child))
                    return ids
                allowed_sub_ids = get_descendants(target_sub)
            except Subbodega.DoesNotExist:
                return response.Response({"error": "Subbodega no encontrada"}, status=404)

        # 1. SQL Aggregation for Stock
        from django.db.models import Sum, F, Case, When, Value
        
        filters = Q(bodega=bodega) | Q(bodega_destino=bodega)
        if allowed_sub_ids is not None:
            filters &= (Q(subbodega_id__in=allowed_sub_ids) | Q(subbodega_destino_id__in=allowed_sub_ids))

        # We aggregate in two parts: as source and as destination
        # Then we combine in Python. This is MUCH faster than iterating over all movements.
        sources = Movimiento.objects.filter(bodega=bodega).values('material', 'subbodega').annotate(
            qty=Sum(
                Case(
                    When(tipo__in=['Entrada', 'Edicion', 'Ajuste', 'Devolucion'], then=F('cantidad')),
                    When(tipo__in=['Salida', 'Traslado'], then=-F('cantidad')),
                    default=Value(0)
                )
            )
        )
        
        destinations = Movimiento.objects.filter(bodega_destino=bodega).values('material', 'subbodega_destino').annotate(
            qty=Sum(
                Case(
                    When(tipo='Traslado', then=F('cantidad')),
                    default=Value(0)
                )
            )
        )

        if allowed_sub_ids is not None:
            sources = sources.filter(subbodega_id__in=allowed_sub_ids)
            destinations = destinations.filter(subbodega_destino_id__in=allowed_sub_ids)

        inventory = {}
        for s in sources:
            key = (s['material'], s['subbodega'])
            inventory[key] = s['qty'] or 0
        
        for d in destinations:
            key = (d['material'], d['subbodega_destino'])
            inventory[key] = inventory.get(key, 0) + (d['qty'] or 0)

        # 2. Fetch required Objects in bulk to avoid N+1
        material_ids = {k[0] for k in inventory.keys()}
        sub_ids = {k[1] for k in inventory.keys() if k[1] is not None}
        
        materials = {m.id: m for m in Material.objects.filter(id__in=material_ids)}
        # Optimized full path fetching
        subs_qs = Subbodega.objects.filter(id__in=sub_ids).select_related('parent', 'parent__parent', 'parent__parent__parent')
        subs = {s.id: s for s in subs_qs}

        resumen = []
        for (mat_id, sub_id), qty in inventory.items():
            if qty != 0:
                mat = materials.get(mat_id)
                sub_obj = subs.get(sub_id)
                resumen.append({
                    'id_material': mat_id,
                    'codigo': mat.codigo if mat else "",
                    'referencia': mat.referencia if mat else "",
                    'nombre': mat.nombre if mat else "Desconocido",
                    'cantidad': qty,
                    'unidad': mat.unidad if mat else "",
                    'id_subbodega': sub_id,
                    'subbodega_nombre': sub_obj.get_full_path() if sub_obj else "General"
                })
        
        return response.Response(resumen)

class SubbodegaViewSet(viewsets.ModelViewSet):
    serializer_class = SubbodegaSerializer

    def get_queryset(self):
        queryset = Subbodega.objects.select_related('bodega', 'parent').all()
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
    def exportar_excel(self, request):
        excel_file = export_all_data_to_excel()
        response = FileResponse(
            excel_file, 
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="backup_inventario.xlsx"'
        return response

    @action(detail=False, methods=['post'])
    def importar_excel(self, request):
        excel_file = request.FILES.get('archivo')
        if not excel_file:
            return response.Response({"error": "No se proporcionó ningún archivo"}, status=400)
        
        try:
            summary = import_all_data_from_excel(excel_file, user=request.user)
            return response.Response(summary)
        except Exception as e:
            return response.Response({"error": str(e)}, status=500)

    @action(detail=False, methods=['get'])
    def descargar_plantilla(self, request):
        excel_file = export_all_data_to_excel(template=True)
        response = FileResponse(
            excel_file, 
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="plantilla_inventario.xlsx"'
        return response

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
    queryset = Movimiento.objects.select_related(
        'material', 'material__marca', 'bodega', 'subbodega', 'marca', 
        'factura', 'bodega_destino', 'subbodega_destino', 'usuario'
    ).all().order_by('-fecha')
    serializer_class = MovimientoSerializer

    @action(detail=False, methods=['get'])
    def resumen_inventario(self, request):
        # 1. SQL Aggregation (Grouping by Material, Bodega, Subbodega)
        from django.db.models import Sum, Case, When, F, Value
        
        # We need to handle movements as source and as destination separately because of Traslados
        sources = Movimiento.objects.values('material', 'bodega', 'subbodega').annotate(
            q=Sum(
                Case(
                    When(tipo__in=['Entrada', 'Edicion', 'Ajuste', 'Devolucion'], then=F('cantidad')),
                    When(tipo__in=['Salida', 'Traslado'], then=-F('cantidad')),
                    default=Value(0)
                )
            )
        )
        
        destinations = Movimiento.objects.filter(tipo='Traslado').values('material', 'bodega_destino', 'subbodega_destino').annotate(
            q=Sum('cantidad')
        )

        inventory = {}
        for s in sources:
            key = (s['material'], s['bodega'], s['subbodega'])
            inventory[key] = s['q'] or 0
        
        for d in destinations:
            key = (d['material'], d['bodega_destino'], d['subbodega_destino'])
            inventory[key] = inventory.get(key, 0) + (d['q'] or 0)

        # 2. Bulk fetch Meta information
        material_ids = {k[0] for k in inventory.keys()}
        bodega_ids = {k[1] for k in inventory.keys()}
        sub_ids = {k[2] for k in inventory.keys() if k[2] is not None}

        materials = {m.id: m for m in Material.objects.filter(id__in=material_ids)}
        bodegas_map = {b.id: b for b in Bodega.objects.filter(id__in=bodega_ids)}
        subs = {s.id: s for s in Subbodega.objects.filter(id__in=sub_ids).select_related('parent', 'parent__parent', 'parent__parent__parent')}

        resumen = []
        for (mat_id, bod_id, sub_id), qty in inventory.items():
            if qty != 0:
                mat = materials.get(mat_id)
                bod = bodegas_map.get(bod_id)
                sub = subs.get(sub_id)
                resumen.append({
                    'id_material': mat_id,
                    'codigo': mat.codigo if mat else "",
                    'referencia': mat.referencia if mat else "",
                    'nombre': mat.nombre if mat else "Desconocido",
                    'id_bodega': bod_id,
                    'bodega': bod.nombre if bod else "Desconocida",
                    'id_subbodega': sub_id,
                    'subbodega': sub.get_full_path() if sub else "General",
                    'cantidad': qty,
                    'unidad': mat.unidad if mat else "",
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
