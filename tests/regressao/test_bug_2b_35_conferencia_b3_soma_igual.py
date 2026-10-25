"""BUG-2B-35: a conferência no yfinance só compara a soma da janela.

Achado da 2ª auditoria FASE do Codex (20/10/2026): um evento B3 em junho e um do yfinance em
julho, ambos de R$ 1, não davam aviso. A ficha Bazin, §2, pede conferência por evento (valor
e data ex), preservando o cálculo pela B3.
"""

import pytest

from sentinela.data import proventos_b3 as pb


def _serie(eventos, componentes=None):
    componentes = componentes or {"ON": 1}
    return {
        "inicio_exclusivo": "2025-09-30",
        "referencia": "2026-09-30",
        "d_bruto_12m": sum(v * componentes[e] for e, _, v in eventos),
        "componentes": componentes,
        "eventos": [
            {
                "especie": especie,
                "natureza": "dividendo",
                "valor": valor,
                "data_com": data_com,
                "aprovacao": "2025-01-01",
            }
            for especie, data_com, valor in eventos
        ],
    }


@pytest.mark.parametrize(
    ("eventos", "dividendos"),
    [
        # mesmo valor, meses diferentes
        ([("ON", "2026-06-10", 1.0)], {"2026-07-11": 1.0}),
        # diferenças que se compensam na soma
        (
            [("ON", "2025-12-10", 0.40), ("ON", "2026-06-10", 0.60)],
            {"2025-12-11": 0.60, "2026-06-11": 0.40},
        ),
    ],
)
def test_divergencia_por_evento_com_soma_igual_gera_aviso(eventos, dividendos):
    avisos = pb.conferencia_yfinance(_serie(eventos), dividendos)
    assert avisos and avisos[0].startswith("proventos divergem do yfinance por evento")


def test_eventos_iguais_nao_geram_aviso():
    serie = _serie([("ON", "2025-12-10", 0.40), ("ON", "2026-06-10", 0.60)])
    assert (
        pb.conferencia_yfinance(serie, {"2025-12-11": 0.40, "2026-06-11": 0.60}) == []
    )


def test_unit_soma_os_componentes_do_mesmo_evento():
    serie = _serie(
        [("ON", "2026-06-10", 0.10), ("PN", "2026-06-10", 0.10)],
        {"ON": 1, "PN": 2},
    )
    assert pb.conferencia_yfinance(serie, {"2026-06-11": 0.30}) == []
