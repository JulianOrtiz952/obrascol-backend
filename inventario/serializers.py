from rest_framework import serializers
from .models import Bodega, Material, Factura, Movimiento, Marca

class MarcaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Marca
        fields = ['id', 'nombre', 'activo']

class BodegaSerializer(serializers.ModelSerializer):
    materiales_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Bodega
        fields = ['id', 'nombre', 'ubicacion', 'activo', 'materiales_count']
    
    def get_materiales_count(self, obj):
        # Count unique materials with stock > 0 in this bodega
        from django.db.models import Q, Sum
        materiales = Material.objects.filter(
            movimientos__bodega=obj
        ).distinct()
        
        count = 0
        for mat in materiales:
            movs = Movimiento.objects.filter(material=mat, bodega=obj)
            total = 0
            for mov in movs:
                if mov.tipo in ['Entrada', 'Edicion', 'Ajuste', 'Devolucion']:
                    total += mov.cantidad
                elif mov.tipo == 'Salida':
                    total -= mov.cantidad
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

    class Meta:
        model = Movimiento
        fields = [
            'id', 'material', 'material_info', 'bodega', 'bodega_info', 
            'factura', 'factura_info', 'factura_manual', 'cantidad', 'precio', 
            'fecha', 'tipo', 'observaciones', 'marca', 'marca_info'
        ]

    def validate(self, data):
        tipo = data.get('tipo', self.instance.tipo if self.instance else None)
        if tipo == 'Salida':
            material = data.get('material', self.instance.material if self.instance else None)
            bodega = data.get('bodega', self.instance.bodega if self.instance else None)
            cantidad_solicitada = data.get('cantidad', self.instance.cantidad if self.instance else 0)

            # Calculate current stock in that specific warehouse
            movimientos = Movimiento.objects.filter(material=material, bodega=bodega)
            stock_actual = 0
            for mov in movimientos:
                if self.instance and mov.id == self.instance.id:
                    continue
                
                if mov.tipo in ['Entrada', 'Edicion', 'Ajuste', 'Devolucion']:
                    stock_actual += mov.cantidad
                elif mov.tipo == 'Salida':
                    stock_actual -= mov.cantidad
            
            if cantidad_solicitada > stock_actual:
                from rest_framework import serializers
                raise serializers.ValidationError(
                    f"Stock insuficiente en esta bodega. Disponible: {stock_actual} {material.unidad}."
                )
        return data
