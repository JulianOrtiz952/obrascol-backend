from rest_framework import serializers
from django.db.models import Q, Sum
from .models import Bodega, Material, Factura, Movimiento, Marca, UnidadMedida
from usuarios.serializers import UsuarioSerializer

class MarcaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Marca
        fields = ['id', 'nombre', 'activo']

class UnidadMedidaSerializer(serializers.ModelSerializer):
    class Meta:
        model = UnidadMedida
        fields = ['id', 'nombre', 'abreviacion', 'activo']

class BodegaSerializer(serializers.ModelSerializer):
    materiales_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Bodega
        fields = ['id', 'nombre', 'ubicacion', 'activo', 'materiales_count']
    
    def get_materiales_count(self, obj):
        # Count unique materials with stock > 0 in this bodega
        materiales = Material.objects.filter(
            Q(movimientos__bodega=obj) | Q(movimientos__bodega_destino=obj)
        ).distinct()
        
        count = 0
        for mat in materiales:
            # Entrada logic with transfers
            movs = Movimiento.objects.filter(material=mat).filter(
                Q(bodega=obj) | Q(bodega_destino=obj)
            )
            total = 0
            for mov in movs:
                if mov.tipo in ['Entrada', 'Edicion', 'Ajuste', 'Devolucion']:
                    if mov.bodega_id == obj.id:
                        total += mov.cantidad
                elif mov.tipo == 'Salida':
                    if mov.bodega_id == obj.id:
                        total -= mov.cantidad
                elif mov.tipo == 'Traslado':
                    if mov.bodega_id == obj.id:
                        total -= mov.cantidad
                    if mov.bodega_destino_id == obj.id:
                        total += mov.cantidad
            if total > 0:
                count += 1
        return count

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
    factura_info = FacturaSerializer(source='factura', read_only=True)
    marca_info = MarcaSerializer(source='marca', read_only=True)
    bodega_destino_info = BodegaSerializer(source='bodega_destino', read_only=True)
    usuario_info = UsuarioSerializer(source='usuario', read_only=True)

    class Meta:
        model = Movimiento
        fields = [
            'id', 'material', 'material_info', 'bodega', 'bodega_info', 
            'bodega_destino', 'bodega_destino_info',
            'factura', 'factura_info', 'factura_manual', 'cantidad', 'precio', 
            'fecha', 'tipo', 'observaciones', 'marca', 'marca_info',
            'usuario', 'usuario_info'
        ]

    def validate(self, data):
        tipo = data.get('tipo', self.instance.tipo if self.instance else None)
        if tipo in ['Salida', 'Traslado']:
            material = data.get('material', self.instance.material if self.instance else None)
            bodega_origen = data.get('bodega', self.instance.bodega if self.instance else None)
            cantidad_solicitada = data.get('cantidad', self.instance.cantidad if self.instance else 0)

            if tipo == 'Traslado':
                bodega_destino = data.get('bodega_destino')
                if not bodega_destino:
                    raise serializers.ValidationError({"bodega_destino": "Debe seleccionar una bodega de destino para un traslado."})
                if bodega_origen == bodega_destino:
                    raise serializers.ValidationError({"bodega_destino": "La bodega de destino no puede ser la misma que la de origen."})

            movimientos = Movimiento.objects.filter(material=material).filter(
                Q(bodega=bodega_origen) | Q(bodega_destino=bodega_origen)
            )
            
            stock_actual = 0
            for mov in movimientos:
                if self.instance and mov.id == self.instance.id:
                    continue
                
                if mov.tipo in ['Entrada', 'Edicion', 'Ajuste', 'Devolucion']:
                    if mov.bodega_id == bodega_origen.id:
                        stock_actual += mov.cantidad
                elif mov.tipo == 'Salida':
                    if mov.bodega_id == bodega_origen.id:
                        stock_actual -= mov.cantidad
                elif mov.tipo == 'Traslado':
                    if mov.bodega_id == bodega_origen.id:
                        stock_actual -= mov.cantidad
                    if mov.bodega_destino_id == bodega_origen.id:
                        stock_actual += mov.cantidad
            
            if cantidad_solicitada > stock_actual:
                raise serializers.ValidationError(
                    f"Stock insuficiente en la bodega de origen. Disponible: {stock_actual} {material.unidad}."
                )
        return data
