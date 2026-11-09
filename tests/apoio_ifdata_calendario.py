"""Premissa SINTÉTICA de publicação para testes; não é calendário efetivo do BCB."""

from datetime import date

from sentinela.data import proveniencia
from sentinela.data.providers.ifdata import CalendarioPublicacoes


def calendario_sintetico(data_base: str = "202606") -> CalendarioPublicacoes:
    publicada = date(2026, 10, 1) if data_base == "202609" else date(2026, 8, 31)
    coleta = (
        "2026-10-02T12:00:00+00:00"
        if data_base == "202609"
        else "2026-09-01T12:00:00+00:00"
    )
    return CalendarioPublicacoes(
        {data_base: publicada},
        proveniencia.Proveniencia(
            periodo_referencia=data_base,
            data_entrega=publicada.isoformat(),
            motivo_sem_entrega=None,
            data_coleta=coleta,
            documento="IF.data",
            versao="cenário sintético de teste",
            fonte="https://www3.bcb.gov.br/ifdata/calendario-sintetico-nao-coletado",
            hash_sha256="a" * 64,
        ),
    )
