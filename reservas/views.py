from django.utils.dateparse import parse_date
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .filters import EspacoFilter, ReservaFilter
from .models import Espaco, Reserva
from .serializers import (
    EspacoDetalheSerializer,
    EspacoSerializer,
    ReservaSerializer,
)


class EspacoViewSet(viewsets.ModelViewSet):
    """
    CRUD de espaços esportivos.

    GET    /api/espacos/        lista paginada (filtros: tipo, coberto, ativo, preco_min,
                                preco_max, capacidade_min; ?search=; ?ordering=)
    GET    /api/espacos/<id>/   detalhe com as reservas aninhadas
    POST   /api/espacos/        cria
    PUT    /api/espacos/<id>/   atualização completa
    PATCH  /api/espacos/<id>/   atualização parcial
    DELETE /api/espacos/<id>/   remove (bloqueado se houver reservas -> 400)
    """

    queryset = Espaco.objects.all()
    filterset_class = EspacoFilter
    search_fields = ['nome', 'descricao']
    ordering_fields = ['nome', 'preco_hora', 'capacidade', 'criado_em']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return EspacoDetalheSerializer
        return EspacoSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        if self.action == 'retrieve':
            qs = qs.prefetch_related('reservas')
        return qs

    @action(detail=True, methods=['get'])
    def disponibilidade(self, request, pk=None):
        """GET /api/espacos/<id>/disponibilidade/?data=AAAA-MM-DD — horários já ocupados no dia."""
        espaco = self.get_object()
        try:
            data = parse_date(request.query_params.get('data', ''))
        except ValueError:
            data = None
        if data is None:
            return Response({'data': 'Informe uma data válida: ?data=AAAA-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)

        ocupados = (
            espaco.reservas.filter(data=data)
            .exclude(status=Reserva.Status.CANCELADA)
            .order_by('hora_inicio')
            .values('id', 'hora_inicio', 'hora_fim', 'status')
        )
        return Response({
            'espaco': espaco.nome,
            'data': data,
            'horario_funcionamento': {
                'abertura': espaco.horario_abertura,
                'fechamento': espaco.horario_fechamento,
            },
            'horarios_ocupados': list(ocupados),
        })


class ReservaViewSet(viewsets.ModelViewSet):
    """
    CRUD de reservas.

    GET    /api/reservas/        lista paginada (filtros: espaco, status, data, data_inicio,
                                 data_fim, cliente_email; ?search=; ?ordering=)
    GET    /api/reservas/<id>/   detalhe com o espaço aninhado
    POST   /api/reservas/        cria (valida horário, funcionamento e conflitos)
    PUT    /api/reservas/<id>/   atualização completa
    PATCH  /api/reservas/<id>/   atualização parcial
    DELETE /api/reservas/<id>/   remove
    POST   /api/reservas/<id>/cancelar/   muda o status para CANCELADA
    """

    queryset = Reserva.objects.select_related('espaco')
    serializer_class = ReservaSerializer
    filterset_class = ReservaFilter
    search_fields = ['cliente_nome', 'cliente_email', 'espaco__nome']
    ordering_fields = ['data', 'hora_inicio', 'valor_total', 'criado_em']

    @action(detail=True, methods=['post'])
    def cancelar(self, request, pk=None):
        reserva = self.get_object()
        if reserva.status == Reserva.Status.CANCELADA:
            return Response({'detail': 'Esta reserva já está cancelada.'}, status=status.HTTP_400_BAD_REQUEST)
        reserva.status = Reserva.Status.CANCELADA
        reserva.save(update_fields=['status', 'atualizado_em'])
        return Response(self.get_serializer(reserva).data)
