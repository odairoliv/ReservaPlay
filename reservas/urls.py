from rest_framework.routers import DefaultRouter

from .views import EspacoViewSet, ReservaViewSet

# O DefaultRouter gera automaticamente as rotas de lista (/recurso/) e
# detalhe (/recurso/<id>/) para cada ViewSet, além da raiz navegável /api/.
router = DefaultRouter()
router.register('espacos', EspacoViewSet, basename='espaco')
router.register('reservas', ReservaViewSet, basename='reserva')

urlpatterns = router.urls
