"""BUG-2B-52: o caminho DISTRESSED do motor de ações devolve o preço como valor justo.

`valuation_engine.processar`, na guarda de `DISTRESSED_TICKERS`, devolve
`fair_value = preço` e `upside = 0`: nenhum método calculou, e os dois números parecem
resultado. É a mesma família do BUG-2B-50 (FII), mas o caminho distressed não é ausência de
insumo e ficou fora da decisão 2 do F2B-69 (card "Valor Justo"; auditoria rápida do
fechamento, "Ficam para o Marcos").
Registrado pós-fechamento da 2B, 25/10/2026; a forma da saída é decidida no F2C-49.
"""

from unittest.mock import patch

from apoio_escopo import de_empresa

from valuation_engine import ValuationEngine


def test_distressed_nao_apresenta_o_preco_como_valor_justo():
    dados = de_empresa(
        {
            "ticker": "TSTC3",
            "preco_atual": 100.0,
            "roe": 0.15,
            "pl": 10.0,
            "pvp": 1.5,
            "dy": 0.08,
        }
    )
    with patch("valuation_engine.DISTRESSED_TICKERS", {"TSTC3"}):
        r = ValuationEngine().processar(dados)
    assert r["perfil"] == "DISTRESSED"
    assert r.get("fair_value") is None, r
    assert r.get("upside") is None, r
