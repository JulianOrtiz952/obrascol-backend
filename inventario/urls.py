from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    BodegaViewSet, MaterialViewSet, 
    FacturaViewSet, MovimientoViewSet,
    MarcaViewSet, ReportesViewSet
)

router = DefaultRouter()
router.register(r'bodegas', BodegaViewSet, basename='bodegas')
router.register(r'materiales', MaterialViewSet)
router.register(r'facturas', FacturaViewSet)
router.register(r'movimientos', MovimientoViewSet)
router.register(r'marcas', MarcaViewSet)
router.register(r'reportes', ReportesViewSet, basename='reportes')

urlpatterns = [
    path('', include(router.urls)),
]
