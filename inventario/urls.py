from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    BodegaViewSet, SubbodegaViewSet, MaterialViewSet, 
    FacturaViewSet, MovimientoViewSet,
    MarcaViewSet, ReportesViewSet, UnidadMedidaViewSet
)

router = DefaultRouter()
router.register(r'bodegas', BodegaViewSet, basename='bodegas')
router.register(r'subbodegas', SubbodegaViewSet, basename='subbodegas')
router.register(r'materiales', MaterialViewSet)
router.register(r'facturas', FacturaViewSet)
router.register(r'movimientos', MovimientoViewSet)
router.register(r'marcas', MarcaViewSet)
router.register(r'unidades', UnidadMedidaViewSet)
router.register(r'reportes', ReportesViewSet, basename='reportes')

urlpatterns = [
    path('', include(router.urls)),
]
