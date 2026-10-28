"""BUG-2C-28: média aritmética com prejuízo não é comparação P/L demonstrada."""

from unittest.mock import Mock

from peers_engine import PeersEngine


def test_pl_negativo_nao_entra_tacitamente_na_media():
    market = Mock()
    market.buscar_dados_ticker.side_effect = lambda ticker: {
        "ticker": ticker,
        "preco_atual": 10,
        "pl": -2,
        "modelo_bpp": "empresa",
    }
    from sentinela.data.referencia.registro import Indice, Registro

    market.referencia.indice.return_value = Indice(
        "2026-10-27",
        {},
        {
            t: Registro(t, "STOCK", "teste", {}, especie="ON", setor="teste", cnpj=t)
            for t in ("PETR4", "TSTB3")
        },
    )
    resultado = PeersEngine(market).comparar("PETR4")
    assert resultado["PL_Media_Peers"] is None
    assert resultado.get("Motivo_PL")
