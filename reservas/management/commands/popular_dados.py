from datetime import time, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from reservas.models import Espaco, Reserva


class Command(BaseCommand):
    help = 'Popula o banco com espaços e reservas de exemplo.'

    def add_arguments(self, parser):
        parser.add_argument('--limpar', action='store_true', help='Apaga os dados existentes antes de popular.')

    @transaction.atomic
    def handle(self, *args, **options):
        if options['limpar']:
            Reserva.objects.all().delete()
            Espaco.objects.all().delete()
            self.stdout.write('Dados anteriores removidos.')

        espacos_dados = [
            {
                'nome': 'Quadra Poliesportiva Central', 'tipo': Espaco.Tipo.QUADRA, 'capacidade': 20,
                'preco_hora': Decimal('90.00'), 'coberto': True,
                'descricao': 'Quadra coberta com piso emborrachado e iluminação LED.',
            },
            {
                'nome': 'Campo Society Arena', 'tipo': Espaco.Tipo.CAMPO, 'capacidade': 16,
                'preco_hora': Decimal('150.00'), 'coberto': False,
                'horario_abertura': time(7, 0), 'horario_fechamento': time(23, 0),
                'descricao': 'Campo de grama sintética com vestiário.',
            },
            {
                'nome': 'Quadra de Areia Sol', 'tipo': Espaco.Tipo.QUADRA, 'capacidade': 8,
                'preco_hora': Decimal('70.00'), 'coberto': False,
                'descricao': 'Quadra de areia para beach tennis e vôlei de praia.',
            },
            {
                'nome': 'Quadra de Tênis Saibro', 'tipo': Espaco.Tipo.QUADRA, 'capacidade': 4,
                'preco_hora': Decimal('80.00'), 'coberto': False,
            },
            {
                'nome': 'Piscina Semiolímpica', 'tipo': Espaco.Tipo.PISCINA, 'capacidade': 30,
                'preco_hora': Decimal('120.00'), 'coberto': True,
                'horario_abertura': time(6, 0), 'horario_fechamento': time(21, 0),
            },
        ]

        espacos = {}
        for dados in espacos_dados:
            espaco, _ = Espaco.objects.update_or_create(nome=dados['nome'], defaults=dados)
            espacos[espaco.nome] = espaco

        hoje = timezone.localdate()
        reservas_dados = [
            ('Quadra Poliesportiva Central', 'Carlos Silva', 'carlos@email.com', 1, time(19, 0), time(21, 0), Reserva.Status.CONFIRMADA),
            ('Quadra Poliesportiva Central', 'Ana Souza', 'ana@email.com', 1, time(21, 0), time(22, 0), Reserva.Status.PENDENTE),
            ('Campo Society Arena', 'Pedro Lima', 'pedro@email.com', 2, time(20, 0), time(22, 0), Reserva.Status.CONFIRMADA),
            ('Quadra de Areia Sol', 'Mariana Costa', 'mariana@email.com', 3, time(9, 0), time(10, 30), Reserva.Status.PENDENTE),
            ('Quadra de Tênis Saibro', 'Rafael Alves', 'rafael@email.com', 5, time(8, 0), time(9, 0), Reserva.Status.CANCELADA),
        ]
        criadas = 0
        for nome_espaco, cliente, email, dias, inicio, fim, status in reservas_dados:
            _, criada = Reserva.objects.get_or_create(
                espaco=espacos[nome_espaco],
                data=hoje + timedelta(days=dias),
                hora_inicio=inicio,
                defaults={
                    'cliente_nome': cliente, 'cliente_email': email,
                    'hora_fim': fim, 'status': status,
                },
            )
            criadas += criada

        self.stdout.write(self.style.SUCCESS(
            f'{Espaco.objects.count()} espaços '
            f'e {Reserva.objects.count()} reservas no banco ({criadas} reservas novas).'
        ))
