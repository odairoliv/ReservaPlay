from django.utils import timezone
from rest_framework import serializers

from .models import Espaco, Reserva


# ---------------------------------------------------------------------------
# Serializers "resumo" — usados apenas para aninhar dentro de outra entidade.
# Eles NÃO aninham de volta, evitando o ciclo Espaco -> Reserva -> Espaco...
# ---------------------------------------------------------------------------
class EspacoResumoSerializer(serializers.ModelSerializer):
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)

    class Meta:
        model = Espaco
        fields = ['id', 'nome', 'tipo', 'tipo_display', 'preco_hora', 'coberto']


class ReservaResumoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reserva
        fields = ['id', 'cliente_nome', 'data', 'hora_inicio', 'hora_fim', 'status', 'valor_total']


# ---------------------------------------------------------------------------
# Espaço
# ---------------------------------------------------------------------------
class EspacoSerializer(serializers.ModelSerializer):
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)

    class Meta:
        model = Espaco
        fields = [
            'id', 'nome', 'tipo', 'tipo_display', 'descricao', 'capacidade',
            'preco_hora', 'coberto', 'ativo', 'horario_abertura', 'horario_fechamento',
            'criado_em', 'atualizado_em',
        ]
        read_only_fields = ['criado_em', 'atualizado_em']

    def validate(self, attrs):
        abertura = attrs.get('horario_abertura', getattr(self.instance, 'horario_abertura', None))
        fechamento = attrs.get('horario_fechamento', getattr(self.instance, 'horario_fechamento', None))
        if abertura and fechamento and fechamento <= abertura:
            raise serializers.ValidationError(
                {'horario_fechamento': 'O horário de fechamento deve ser posterior ao de abertura.'}
            )
        return attrs


class EspacoDetalheSerializer(EspacoSerializer):
    """Usado no GET /api/espacos/<id>/: inclui as reservas do espaço aninhadas."""

    reservas = ReservaResumoSerializer(many=True, read_only=True)

    class Meta(EspacoSerializer.Meta):
        fields = EspacoSerializer.Meta.fields + ['reservas']


# ---------------------------------------------------------------------------
# Reserva
# ---------------------------------------------------------------------------
class ReservaSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    # Leitura: dados do espaço aninhados.
    espaco = EspacoResumoSerializer(read_only=True)
    # Escrita: o cliente envia apenas o ID do espaço (chave estrangeira).
    espaco_id = serializers.PrimaryKeyRelatedField(
        queryset=Espaco.objects.all(),
        write_only=True,
        source='espaco',
    )

    class Meta:
        model = Reserva
        fields = [
            'id', 'espaco', 'espaco_id', 'cliente_nome', 'cliente_email', 'cliente_telefone',
            'data', 'hora_inicio', 'hora_fim', 'status', 'status_display', 'observacoes',
            'valor_total', 'criado_em', 'atualizado_em',
        ]
        read_only_fields = ['valor_total', 'criado_em', 'atualizado_em']

    def _valor(self, attrs, campo):
        """Valor enviado no payload ou, em PATCH, o valor atual do registro."""
        if campo in attrs:
            return attrs[campo]
        return getattr(self.instance, campo, None)

    def validate(self, attrs):
        espaco = self._valor(attrs, 'espaco')
        data = self._valor(attrs, 'data')
        inicio = self._valor(attrs, 'hora_inicio')
        fim = self._valor(attrs, 'hora_fim')
        status = self._valor(attrs, 'status') or Reserva.Status.PENDENTE

        erros = {}

        if inicio and fim and fim <= inicio:
            erros['hora_fim'] = 'O horário de término deve ser posterior ao horário de início.'

        # Só valida data passada quando a data está sendo definida/alterada.
        if 'data' in attrs and data < timezone.localdate():
            erros['data'] = 'Não é possível reservar em uma data passada.'

        if espaco is not None:
            if not espaco.ativo and status != Reserva.Status.CANCELADA:
                erros['espaco_id'] = 'Este espaço está inativo e não aceita reservas.'
            elif inicio and fim and (inicio < espaco.horario_abertura or fim > espaco.horario_fechamento):
                erros['hora_inicio'] = (
                    f'O espaço funciona das {espaco.horario_abertura:%H:%M} '
                    f'às {espaco.horario_fechamento:%H:%M}.'
                )

        if erros:
            raise serializers.ValidationError(erros)

        # Conflito de horário: outra reserva ativa no mesmo espaço/data com sobreposição.
        if status != Reserva.Status.CANCELADA and espaco and data and inicio and fim:
            conflitos = Reserva.objects.filter(
                espaco=espaco,
                data=data,
                hora_inicio__lt=fim,
                hora_fim__gt=inicio,
            ).exclude(status=Reserva.Status.CANCELADA)
            if self.instance is not None:
                conflitos = conflitos.exclude(pk=self.instance.pk)
            if conflitos.exists():
                c = conflitos.first()
                raise serializers.ValidationError({
                    'non_field_errors': [
                        f'Horário indisponível: já existe a reserva #{c.pk} '
                        f'das {c.hora_inicio:%H:%M} às {c.hora_fim:%H:%M} neste espaço.'
                    ]
                })

        return attrs
