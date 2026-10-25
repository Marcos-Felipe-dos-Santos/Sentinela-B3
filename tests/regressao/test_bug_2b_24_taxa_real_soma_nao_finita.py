"""Matriz taxa-real §4: intermediário não finito abstém sem exceção."""

from datetime import UTC, date, datetime

from sentinela.data import taxas
from sentinela.data.providers.tesouro import TituloTesouro, selecionar_ofertas
from sentinela.domain.units import RateReal


def test_soma_de_taxas_finitas_nao_transborda_a_interface():
    titulos = tuple(
        TituloTesouro(
            "Tesouro IPCA+",
            "NTN-B Principal",
            date(ano, 1, 1),
            date(2026, 10, 15),
            RateReal(1e308),
            None,
            100,
            100,
        )
        for ano in (2035, 2045)
    )
    calendario = taxas.Calendario(
        date(2026, 1, 1), date(2026, 12, 31), frozenset(), {"fonte": "ANBIMA"}
    )
    resultado = taxas.calcular(
        selecionar_ofertas(titulos),
        as_of=datetime(2026, 10, 20, 15, tzinfo=UTC),
        calendario=calendario,
        proveniencia={"fonte": "Tesouro"},
    )
    assert isinstance(resultado, taxas.Abstencao)
    assert resultado.motivo == "resultado não finito: soma das taxas"
