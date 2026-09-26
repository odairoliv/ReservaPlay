import django_filters

from .models import Espaco, Reserva


class EspacoFilter(django_filters.FilterSet):
    """Ex.: /api/espacos/?tipo=QUADRA&coberto=true&preco_max=100"""

    preco_min = django_filters.NumberFilter(field_name='preco_hora', lookup_expr='gte')
    preco_max = django_filters.NumberFilter(field_name='preco_hora', lookup_expr='lte')
    capacidade_min = django_filters.NumberFilter(field_name='capacidade', lookup_expr='gte')

    class Meta:
        model = Espaco
        fields = ['tipo', 'coberto', 'ativo']


class ReservaFilter(django_filters.FilterSet):
    """Ex.: /api/reservas/?espaco=1&status=CONFIRMADA&data_inicio=2026-10-01&data_fim=2026-10-31"""

    data_inicio = django_filters.DateFilter(field_name='data', lookup_expr='gte')
    data_fim = django_filters.DateFilter(field_name='data', lookup_expr='lte')
    cliente_email = django_filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = Reserva
        fields = ['espaco', 'status', 'data']
