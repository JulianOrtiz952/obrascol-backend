from rest_framework import serializers
from django.db.models import Q, Sum
from .models import Bodega, Subbodega, Material, Factura, Movimiento, Marca, UnidadMedida
from usuarios.serializers import UsuarioSerializer

class MarcaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Marca
        fields = ['id', 'nombre', 'activo']

class UnidadMedidaSerializer(serializers.ModelSerializer):
    class Meta:
        model = UnidadMedida
        fields = ['id', 'nombre', 'abreviacion', 'activo']

class SubbodegaSerializer(serializers.ModelSerializer):
    full_path = serializers.ReadOnlyField(source='get_full_path')
    
    class Meta:
        model = Subbodega
        fields = ['id', 'nombre', 'full_path', 'bodega', 'parent', 'activo']

class BodegaSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bodega
        fields = ['id', 'nombre', 'ubicacion', 'activo']

class BodegaSerializer(serializers.ModelSerializer):
    materiales_count = serializers.SerializerMethodField()
    # Removing nested subbodegas from here as it's a performance killer in lists
    # Front-end should fetch subbodegas separately or we only include them in detail view
    
    class Meta:
        model = Bodega
        fields = ['id', 'nombre', 'ubicacion', 'activo', 'materiales_count']
    
    def get_materiales_count(self, obj):
        from django.db.models import Sum, Case, When, F, Value
        
        # Calculate stock per material using efficient aggregation (only 2 queries)
        sources = Movimiento.objects.filter(bodega=obj).values('material').annotate(
            stock=Sum(
                Case(
                    When(tipo__in=['Entrada', 'Edicion', 'Ajuste', 'Devolucion'], then=F('cantidad')),
                    When(tipo__in=['Salida', 'Traslado'], then=-F('cantidad')),
                    default=Value(0)
                )
            )
        )
        
        destinations = Movimiento.objects.filter(bodega_destino=obj).values('material').annotate(
            stock=Sum(
                Case(
                    When(tipo='Traslado', then=F('cantidad')),
                    default=Value(0)
                )
            )
        )
        
        stock_map = {}
        for s in sources:
            stock_map[s['material']] = s['stock'] or 0
        for d in destinations:
            mat_id = d['material']
            stock_map[mat_id] = stock_map.get(mat_id, 0) + (d['stock'] or 0)
            
        return sum(1 for qty in stock_map.values() if qty > 0)

class MaterialSerializer(serializers.ModelSerializer):
    marca_nombre = serializers.ReadOnlyField(source='marca.nombre')

    class Meta:
        model = Material
        fields = ['id', 'codigo', 'codigo_barras', 'referencia', 'nombre', 'unidad', 'marca', 'ultimo_precio', 'marca_nombre']

class FacturaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Factura
        fields = '__all__'

class MovimientoSerializer(serializers.ModelSerializer):
    material_info = MaterialSerializer(source='material', read_only=True)
    bodega_info = BodegaSerializer(source='bodega', read_only=True)
    subbodega_info = SubbodegaSerializer(source='subbodega', read_only=True)
    factura_info = FacturaSerializer(source='factura', read_only=True)
    marca_info = MarcaSerializer(source='marca', read_only=True)
    bodega_destino_info = BodegaSerializer(source='bodega_destino', read_only=True)
    subbodega_destino_info = SubbodegaSerializer(source='subbodega_destino', read_only=True)
    usuario_info = UsuarioSerializer(source='usuario', read_only=True)

    class Meta:
        model = Movimiento
        fields = [
            'id', 'material', 'material_info', 'bodega', 'bodega_info', 
            'subbodega', 'subbodega_info',
            'bodega_destino', 'bodega_destino_info',
            'subbodega_destino', 'subbodega_destino_info',
            'factura', 'factura_info', 'factura_manual', 'cantidad', 'precio', 
            'fecha', 'tipo', 'observaciones', 'marca', 'marca_info',
            'usuario', 'usuario_info'
        ]

    def validate(self, data):
        tipo = data.get('tipo', self.instance.tipo if self.instance else None)
        if tipo in ['Salida', 'Traslado']:
            material = data.get('material', self.instance.material if self.instance else None)
            bodega_origen = data.get('bodega', self.instance.bodega if self.instance else None)
            subbodega_origen = data.get('subbodega', self.instance.subbodega if self.instance else None)
            cantidad_solicitada = data.get('cantidad', self.instance.cantidad if self.instance else 0)

            if tipo == 'Traslado':
                bodega_destino = data.get('bodega_destino')
                subbodega_destino = data.get('subbodega_destino')
                if not bodega_destino:
                    raise serializers.ValidationError({"bodega_destino": "Debe seleccionar una bodega de destino para un traslado."})
                if bodega_origen == bodega_destino and subbodega_origen == subbodega_destino:
                    raise serializers.ValidationError({"subbodega_destino": "La ubicación de destino no puede ser la misma que la de origen."})

            # Calculate stock in specific subbodega
            movimientos = Movimiento.objects.filter(material=material).filter(
                Q(bodega=bodega_origen, subbodega=subbodega_origen) | 
                Q(bodega_destino=bodega_origen, subbodega_destino=subbodega_origen)
            )
            
            stock_actual = 0
            for mov in movimientos:
                if self.instance and mov.id == self.instance.id:
                    continue
                
                if mov.tipo in ['Entrada', 'Edicion', 'Ajuste', 'Devolucion']:
                    if mov.bodega_id == bodega_origen.id and mov.subbodega_id == (subbodega_origen.id if subbodega_origen else None):
                        stock_actual += mov.cantidad
                elif mov.tipo == 'Salida':
                    if mov.bodega_id == bodega_origen.id and mov.subbodega_id == (subbodega_origen.id if subbodega_origen else None):
                        stock_actual -= mov.cantidad
                elif mov.tipo == 'Traslado':
                    if mov.bodega_id == bodega_origen.id and mov.subbodega_id == (subbodega_origen.id if subbodega_origen else None):
                        stock_actual -= mov.cantidad
                    if mov.bodega_destino_id == bodega_origen.id and mov.subbodega_destino_id == (subbodega_origen.id if subbodega_origen else None):
                        stock_actual += mov.cantidad
            
            if cantidad_solicitada > stock_actual:
                loc_name = subbodega_origen.nombre if subbodega_origen else "General"
                raise serializers.ValidationError(
                    f"Stock insuficiente en {bodega_origen.nombre} ({loc_name}). Disponible: {stock_actual} {material.unidad}."
                )
        return data
