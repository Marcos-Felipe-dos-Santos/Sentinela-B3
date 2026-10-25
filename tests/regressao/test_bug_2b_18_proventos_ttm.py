"""F2B-48: ausência comprovada difere de leitura inválida em série e TTM."""

from datetime import date

import pytest

from cvm_provider import CVMProvider
from sentinela.data import series_cvm as s
from sentinela.data.contas_cvm import MOTIVO_LINHA_AUSENTE, MOTIVO_VALOR_INVALIDO
from tests.test_cvm_series import CD_CVM, _ind, _zip


@pytest.mark.parametrize(
    "motivo,esperado", [(MOTIVO_LINHA_AUSENTE, 10.0), (MOTIVO_VALOR_INVALIDO, None)]
)
def test_ttm_preserva_rubrica_so_com_ausencia_comprovada(motivo, esperado):
    acumulados = [
        s.Acumulado(
            "ITR" if i < 4 else "DFP",
            fim,
            1,
            date(2025, 1, 1),
            date.fromisoformat(fim),
            {"dividendos": 2.5 * i, "jcp": None},
            {"jcp": motivo},
        )
        for i, fim in enumerate(
            ["2025-03-31", "2025-06-30", "2025-09-30", "2025-12-31"], 1
        )
    ]
    assert s.ttm(acumulados, date(2026, 1, 1))["valores"]["proventos"] == esperado


@pytest.mark.parametrize(
    "motivos", [None, {}, {"jcp": "desconhecido"}, {"jcp": MOTIVO_LINHA_AUSENTE + "x"}]
)
def test_proventos_nao_inventa_nao_ocorrencia(motivos):
    assert s.proventos(10.0, None, motivos=motivos) is None


def test_duas_rubricas_ausentes_iguais_na_serie_e_ttm(tmp_path):
    dre = []
    dva = []
    for fim in ["2025-03-31", "2025-06-30", "2025-09-30", "2025-12-31"]:
        dre.append(
            (
                fim,
                "1",
                "ÚLTIMO",
                "2025-01-01",
                fim,
                "3.11",
                "Lucro/Prejuízo Consolidado do Período",
                10,
            )
        )
        dva.append((fim, "1", "ÚLTIMO", "2025-01-01", fim, "7.01", "Receitas", 50))
    itr = _zip(tmp_path / "itr.zip", "itr", 2025, dre[:3], dva[:3])
    dfp = _zip(tmp_path / "dfp.zip", "dfp", 2025, dre[3:], dva[3:])
    p = CVMProvider(str(tmp_path / "cache"))
    anual = p.proventos_do_documento(dfp, CD_CVM, "2025-12-31", "1")
    serie = s.exercicio(2025, {**_ind(2025), **anual})
    ttm = s.ttm(
        p._acumulados_do_arquivo(itr, "ITR", CD_CVM, "empresa")
        + p._acumulados_do_arquivo(dfp, "DFP", CD_CVM, "empresa"),
        date(2026, 1, 1),
    )
    assert tuple(
        ttm["valores"][c] for c in ("dividendos", "jcp", "proventos")
    ) == tuple(serie[c] for c in ("dividendos", "jcp", "proventos"))
