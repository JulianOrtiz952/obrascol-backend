from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    BodegaViewSet, MaterialViewSet, 
    FacturaViewSet, MovimientoViewSet
)

router = DefaultRouter()
router.register(r'bodegas', BodegaViewSet, basename='bodegas')
router.register(r'materiales', MaterialViewSet)
router.register(r'facturas', FacturaViewSet)
router.register(r'movimientos', MovimientoViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
