from datetime import time, timedelta
from decimal import Decimal

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Espaco, Reserva


class BaseAPITestCase(APITestCase):
    def setUp(self):
        self.espaco = Espaco.objects.create(
            nome='Quadra A', tipo=Espaco.Tipo.QUADRA, capacidade=10,
            preco_hora=Decimal('100.00'), coberto=True,
        )
        self.amanha = timezone.localdate() + timedelta(days=1)
        self.reserva = Reserva.objects.create(
            espaco=self.espaco, cliente_nome='João', cliente_email='joao@email.com',
            data=self.amanha, hora_inicio=time(18, 0), hora_fim=time(19, 0),
        )

    def payload_reserva(self, **extra):
        dados = {
            'espaco_id': self.espaco.id,
            'cliente_nome': 'Maria',
            'cliente_email': 'maria@email.com',
            'data': self.amanha.isoformat(),
            'hora_inicio': '20:00',
            'hora_fim': '21:30',
        }
        dados.update(extra)
        return dados


class EspacoAPITests(BaseAPITestCase):
    def test_listar_paginado(self):
        resp = self.client.get('/api/espacos/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('results', resp.data)
        self.assertEqual(resp.data['count'], 1)

    def test_filtrar_por_tipo_e_preco(self):
        Espaco.objects.create(nome='Piscina', tipo=Espaco.Tipo.PISCINA, capacidade=5, preco_hora=Decimal('300'))
        resp = self.client.get('/api/espacos/', {'tipo': 'PISCINA'})
        self.assertEqual(resp.data['count'], 1)
        resp = self.client.get('/api/espacos/', {'preco_max': 150})
        self.assertEqual([e['nome'] for e in resp.data['results']], ['Quadra A'])

    def test_detalhe_com_reservas_aninhadas(self):
        resp = self.client.get(f'/api/espacos/{self.espaco.id}/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['reservas'][0]['cliente_nome'], 'João')

    def test_detalhe_inexistente_404(self):
        resp = self.client.get('/api/espacos/9999/')
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_criar_201(self):
        resp = self.client.post('/api/espacos/', {
            'nome': 'Campo B', 'tipo': 'CAMPO', 'capacidade': 14, 'preco_hora': '150.00',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data['tipo_display'], 'Campo')

    def test_criar_invalido_400(self):
        resp = self.client.post('/api/espacos/', {'nome': '', 'capacidade': 0}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('nome', resp.data)
        self.assertIn('preco_hora', resp.data)

    def test_horario_fechamento_antes_da_abertura_400(self):
        resp = self.client.patch(f'/api/espacos/{self.espaco.id}/', {'horario_fechamento': '07:00'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_put_substitui_registro(self):
        resp = self.client.put(f'/api/espacos/{self.espaco.id}/', {
            'nome': 'Quadra A Reformada', 'tipo': 'GINASIO', 'capacidade': 50,
            'preco_hora': '200.00',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['tipo'], 'GINASIO')
        self.assertEqual(resp.data['nome'], 'Quadra A Reformada')

    def test_put_incompleto_400(self):
        resp = self.client.put(f'/api/espacos/{self.espaco.id}/', {'nome': 'Só nome'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_patch_parcial(self):
        resp = self.client.patch(f'/api/espacos/{self.espaco.id}/', {'preco_hora': '120.00'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['preco_hora'], '120.00')
        self.assertEqual(resp.data['nome'], 'Quadra A')

    def test_excluir_com_reservas_bloqueado_400(self):
        resp = self.client.delete(f'/api/espacos/{self.espaco.id}/')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(Espaco.objects.filter(pk=self.espaco.id).exists())

    def test_excluir_sem_reservas_204(self):
        self.reserva.delete()
        resp = self.client.delete(f'/api/espacos/{self.espaco.id}/')
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(resp.content, b'')

    def test_disponibilidade(self):
        resp = self.client.get(f'/api/espacos/{self.espaco.id}/disponibilidade/', {'data': self.amanha.isoformat()})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data['horarios_ocupados']), 1)
        resp = self.client.get(f'/api/espacos/{self.espaco.id}/disponibilidade/', {'data': 'abc'})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


class ReservaAPITests(BaseAPITestCase):
    def test_listar_e_filtrar(self):
        resp = self.client.get('/api/reservas/', {'espaco': self.espaco.id, 'status': 'PENDENTE'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['count'], 1)

    def test_detalhe_com_espaco_aninhado(self):
        resp = self.client.get(f'/api/reservas/{self.reserva.id}/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['espaco']['nome'], 'Quadra A')
        self.assertNotIn('reservas', resp.data['espaco'])  # sem ciclo

    def test_criar_calcula_valor_201(self):
        resp = self.client.post('/api/reservas/', self.payload_reserva(), format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data['valor_total'], '150.00')  # 1h30 x R$100

    def test_criar_espaco_inexistente_400(self):
        resp = self.client.post('/api/reservas/', self.payload_reserva(espaco_id=9999), format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('espaco_id', resp.data)

    def test_conflito_de_horario_400(self):
        resp = self.client.post('/api/reservas/', self.payload_reserva(hora_inicio='18:30', hora_fim='19:30'), format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('non_field_errors', resp.data)

    def test_reserva_cancelada_libera_horario(self):
        self.reserva.status = Reserva.Status.CANCELADA
        self.reserva.save()
        resp = self.client.post('/api/reservas/', self.payload_reserva(hora_inicio='18:00', hora_fim='19:00'), format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_fim_antes_do_inicio_400(self):
        resp = self.client.post('/api/reservas/', self.payload_reserva(hora_inicio='21:00', hora_fim='20:00'), format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('hora_fim', resp.data)

    def test_data_passada_400(self):
        ontem = (timezone.localdate() - timedelta(days=1)).isoformat()
        resp = self.client.post('/api/reservas/', self.payload_reserva(data=ontem), format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('data', resp.data)

    def test_fora_do_horario_de_funcionamento_400(self):
        resp = self.client.post('/api/reservas/', self.payload_reserva(hora_inicio='06:00', hora_fim='07:00'), format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_espaco_inativo_400(self):
        self.espaco.ativo = False
        self.espaco.save()
        resp = self.client.post('/api/reservas/', self.payload_reserva(), format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_put_completo(self):
        resp = self.client.put(f'/api/reservas/{self.reserva.id}/', self.payload_reserva(
            cliente_nome='João Pedro', status='CONFIRMADA',
        ), format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['status'], 'CONFIRMADA')
        self.assertEqual(resp.data['hora_inicio'], '20:00:00')

    def test_patch_no_proprio_horario_nao_conflita(self):
        resp = self.client.patch(f'/api/reservas/{self.reserva.id}/', {'hora_fim': '19:30'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['valor_total'], '150.00')

    def test_patch_status_invalido_400(self):
        resp = self.client.patch(f'/api/reservas/{self.reserva.id}/', {'status': 'XYZ'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cancelar(self):
        resp = self.client.post(f'/api/reservas/{self.reserva.id}/cancelar/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['status'], 'CANCELADA')
        resp = self.client.post(f'/api/reservas/{self.reserva.id}/cancelar/')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_excluir_204_e_depois_404(self):
        resp = self.client.delete(f'/api/reservas/{self.reserva.id}/')
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        resp = self.client.get(f'/api/reservas/{self.reserva.id}/')
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)


class ErroInternoTests(APITestCase):
    def test_erro_inesperado_retorna_500_json(self):
        from unittest.mock import patch

        from .views import ReservaViewSet

        with patch.object(ReservaViewSet, 'list', side_effect=RuntimeError('falha')):
            resp = self.client.get('/api/reservas/')
        self.assertEqual(resp.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(resp.data['detail'], 'Erro interno do servidor.')
