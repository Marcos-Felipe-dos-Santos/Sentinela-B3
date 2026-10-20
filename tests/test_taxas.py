"""Ficha taxa-real 1.1: contas independentes, sem fonte implícita."""

from datetime import UTC, date, datetime

import pytest

from sentinela.data import taxas
from sentinela.data.providers.tesouro import TituloTesouro, selecionar_ofertas
from sentinela.domain.units import RateReal

AS_OF = datetime(2026, 10, 20, 15, tzinfo=UTC)


def _titulo(taxa, vencimento=date(2035, 1, 1), base=date(2026, 10, 15), tipo="NTN-B"):
    return TituloTesouro(
        "fonte", tipo, vencimento, base, RateReal(taxa), RateReal(taxa), 100, 100
    )


def _calendario():
    return taxas.Calendario(
        date(2026, 1, 1),
        date(2026, 12, 31),
        frozenset({date(2026, 10, 12)}),
        {"fonte": "ANBIMA", "hash_sha256": "a" * 64},
    )


def _calcular(titulos=None, **kw):
    return taxas.calcular(
        selecionar_ofertas(titulos or (_titulo(0.06), _titulo(0.08, date(2045, 1, 1)))),
        as_of=AS_OF,
        calendario=_calendario(),
        proveniencia={"fonte": "Tesouro Transparente"},
        **kw,
    )


def test_vertice_pela_regra_da_ficha():
    titulos = (
        _titulo(0.06),
        _titulo(0.08, date(2045, 1, 1)),
        _titulo(0.5, date(2034, 12, 31)),
        _titulo(0.9, tipo="prefixado"),
        _titulo(0.2, base=date(2026, 10, 14)),
    )
    registro = _calcular(titulos)
    assert registro["ntnb"] == pytest.approx(0.07)
    assert registro["quantidade"] == 2
    assert registro["data_base"] == "2026-10-15"
    assert registro["dias_uteis"] == 3
    assert registro["proveniencia"]["fonte"] == "Tesouro Transparente"


def test_ntnb_alem_da_defasagem_abstem():
    resultado = _calcular((_titulo(0.06, base=date(2026, 10, 8)),))
    assert isinstance(resultado, taxas.Abstencao)
    assert "5 dias úteis" in resultado.motivo


def test_custo_de_capital_e_ntnb_mais_premio():
    registro = _calcular()
    assert registro["premio"] == 0.05
    assert registro["custo_capital_real"] == pytest.approx(0.12)
    assert (
        registro["composicao"]
        == "NTN-B integral + 5 pp das ações; risco Brasil já no título"
    )


def test_sem_valor_de_contingencia():
    resultado = taxas.calcular(
        selecionar_ofertas(()), as_of=AS_OF, calendario=_calendario(), proveniencia={}
    )
    assert isinstance(resultado, taxas.Abstencao)
    assert "cesta vazia" in resultado.motivo


def test_sem_calendario_comprovado_nao_atesta_idade():
    resultado = taxas.calcular(
        selecionar_ofertas((_titulo(0.06),)),
        as_of=AS_OF,
        calendario=None,
        proveniencia={},
    )
    assert isinstance(resultado, taxas.Abstencao)
    assert "calendário" in resultado.motivo


@pytest.mark.parametrize(
    "as_of,motivo",
    [
        (datetime(2026, 10, 20, tzinfo=UTC).replace(tzinfo=None), "fuso"),
        (datetime(2026, 10, 15, 15, tzinfo=UTC), "fim do dia"),
    ],
)
def test_corte_temporal_explicito(as_of, motivo):
    r = taxas.calcular(
        selecionar_ofertas((_titulo(0.06),)),
        as_of=as_of,
        calendario=_calendario(),
        proveniencia={"fonte": "Tesouro"},
    )
    assert isinstance(r, taxas.Abstencao) and motivo in r.motivo


def test_fronteira_cinco_dias_uteis_e_calendario_sem_cobertura():
    r = _calcular((_titulo(0.06, base=date(2026, 10, 13)),))
    assert r["dias_uteis"] == 5
    calendario = taxas.Calendario(
        date(2026, 10, 16), date(2026, 12, 31), frozenset(), {"fonte": "calendário"}
    )
    r = taxas.calcular(
        selecionar_ofertas((_titulo(0.06),)),
        as_of=AS_OF,
        calendario=calendario,
        proveniencia={"fonte": "Tesouro"},
    )
    assert isinstance(r, taxas.Abstencao) and "cobertura" in r.motivo
    r = taxas.calcular(
        selecionar_ofertas((_titulo(0.06),)),
        as_of=AS_OF,
        calendario=_calendario(),
        proveniencia={},
    )
    assert r.motivo == "proveniência ausente"


def test_registro_completo_sem_arredondamento():
    r = _calcular()
    assert r["fonte"] == "Tesouro Transparente"
    assert r["as_of"] == AS_OF.isoformat()
    assert (
        r["vertice"]
        == "NTN-B e NTN-B Principal, vencimentos a partir de 2035, pesos iguais"
    )
    assert r["proveniencia"]["excluidos_sem_oferta"] == 0
    assert r["proveniencia"]["calendario"] == _calendario().proveniencia
    assert r["proveniencia"]["data_base"] == "2026-10-15"


def test_calendario_limites_e_feriado_na_contagem():
    calendario = _calendario()
    assert calendario.dias_uteis(date(2026, 10, 9), date(2026, 10, 13)) == 1
    assert calendario.dias_uteis(date(2026, 10, 20), date(2026, 10, 20)) == 0
    for inicio, fim in [
        (date(2025, 12, 31), date(2026, 1, 2)),
        (date(2026, 12, 30), date(2027, 1, 1)),
        (date(2026, 10, 21), date(2026, 10, 20)),
    ]:
        with pytest.raises(ValueError):
            calendario.dias_uteis(inicio, fim)
