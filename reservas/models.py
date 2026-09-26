from datetime import datetime, time
from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models


class Espaco(models.Model):
    """Quadra ou espaço esportivo disponível para reserva."""

    class Tipo(models.TextChoices):
        QUADRA = 'QUADRA', 'Quadra'
        CAMPO = 'CAMPO', 'Campo'
        PISCINA = 'PISCINA', 'Piscina'
        GINASIO = 'GINASIO', 'Ginásio'
        SALAO = 'SALAO', 'Salão'

    nome = models.CharField(max_length=100, unique=True)
    tipo = models.CharField(max_length=10, choices=Tipo.choices, default=Tipo.QUADRA)
    descricao = models.TextField(blank=True)
    capacidade = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    preco_hora = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    coberto = models.BooleanField(default=False)
    ativo = models.BooleanField(default=True)
    horario_abertura = models.TimeField(default=time(8, 0))
    horario_fechamento = models.TimeField(default=time(22, 0))

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['nome']
        verbose_name = 'espaço'
        verbose_name_plural = 'espaços'
        constraints = [
            models.CheckConstraint(
                condition=models.Q(horario_fechamento__gt=models.F('horario_abertura')),
                name='espaco_fechamento_apos_abertura',
            ),
        ]

    def __str__(self):
        return f'{self.nome} ({self.get_tipo_display()})'


class Reserva(models.Model):
    """Reserva de um espaço em uma data e faixa de horário."""

    class Status(models.TextChoices):
        PENDENTE = 'PENDENTE', 'Pendente'
        CONFIRMADA = 'CONFIRMADA', 'Confirmada'
        CANCELADA = 'CANCELADA', 'Cancelada'

    # Relacionamento 1:N — um espaço possui muitas reservas.
    # PROTECT impede apagar um espaço que ainda tem reservas (integridade referencial).
    espaco = models.ForeignKey(Espaco, on_delete=models.PROTECT, related_name='reservas')

    cliente_nome = models.CharField(max_length=120)
    cliente_email = models.EmailField()
    cliente_telefone = models.CharField(max_length=20, blank=True)

    data = models.DateField()
    hora_inicio = models.TimeField()
    hora_fim = models.TimeField()

    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDENTE)
    observacoes = models.TextField(blank=True)

    # Calculado automaticamente no save(): preco_hora do espaço x duração.
    valor_total = models.DecimalField(max_digits=10, decimal_places=2, editable=False, default=Decimal('0.00'))

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-data', 'hora_inicio']
        verbose_name = 'reserva'
        verbose_name_plural = 'reservas'
        constraints = [
            models.CheckConstraint(
                condition=models.Q(hora_fim__gt=models.F('hora_inicio')),
                name='reserva_fim_apos_inicio',
            ),
        ]

    def __str__(self):
        return f'{self.espaco.nome} - {self.data:%d/%m/%Y} {self.hora_inicio:%H:%M}-{self.hora_fim:%H:%M}'

    @property
    def duracao_horas(self):
        inicio = datetime.combine(self.data, self.hora_inicio)
        fim = datetime.combine(self.data, self.hora_fim)
        return Decimal((fim - inicio).total_seconds()) / Decimal(3600)

    def calcular_valor(self):
        return (self.espaco.preco_hora * self.duracao_horas).quantize(Decimal('0.01'))

    def save(self, *args, **kwargs):
        self.valor_total = self.calcular_valor()
        super().save(*args, **kwargs)
