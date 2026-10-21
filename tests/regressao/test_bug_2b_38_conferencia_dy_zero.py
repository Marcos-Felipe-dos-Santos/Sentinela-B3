"""BUG-2B-38: com D = 0 pela B3 e nenhum dividendo no yfinance, a conferência diz "indisponível".

Achado da revisão final do F2B-53 (21/10/2026): `market_engine` grava `{}` quando o histórico
do yfinance tem a coluna de dividendos sem nenhum pagamento, e `conferencia_yfinance` trata
`{}` como falta de conferência. As duas fontes concordam (zero); só a falta da coluna (`None`)
é conferência indisponível.
"""


from sentinela.data import proventos_b3 as pb

SERIE = {
    "inicio_exclusivo": "2025-09-30",
    "referencia": "2026-09-30",
    "d_bruto_12m": 0.0,
    "componentes": {"ON": 1},
    "eventos": [],
}


def test_zero_nas_duas_fontes_confere():
    assert pb.conferencia_yfinance(SERIE, {}) == []


def test_sem_coluna_de_dividendos_continua_indisponivel():
    assert pb.conferencia_yfinance(SERIE, None) == [pb.AVISO_SEM_CONFERENCIA]
