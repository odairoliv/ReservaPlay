import logging

from django.db import IntegrityError
from django.db.models import ProtectedError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Estende o handler padrão do DRF (que já trata 400, 404, 405...):

    - ProtectedError  -> 400: tentativa de excluir registro que ainda possui
      dependentes (ex.: espaço com reservas), respeitando a integridade referencial.
    - IntegrityError  -> 400: violação de restrição do banco.
    - Qualquer outro erro não previsto -> 500 com corpo JSON padronizado.
    """
    response = exception_handler(exc, context)
    if response is not None:
        return response

    if isinstance(exc, ProtectedError):
        relacionados = sorted({obj._meta.verbose_name_plural for obj in exc.protected_objects})
        return Response(
            {
                'detail': 'Não é possível excluir este registro pois existem '
                          f'{", ".join(relacionados)} vinculadas a ele.',
                'quantidade_vinculos': len(exc.protected_objects),
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    if isinstance(exc, IntegrityError):
        return Response(
            {'detail': 'A operação viola uma regra de integridade do banco de dados.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    logger.exception('Erro não tratado na API', exc_info=exc)
    return Response(
        {'detail': 'Erro interno do servidor.'},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
