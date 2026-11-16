"""BUG-3-22: a cascata busca a taxa real no relógio, não no as_of pedido.

Auditoria externa do Gemini sobre 284165f..419f010, achado 5 (11/11/2026): no F3-6c,
`buscar_dados_ticker` passou a repassar o `as_of` às fontes, mas chama `_buscar_taxa_real(dados)`
sem ele, e `_buscar_taxa_real` usa `datetime.now(UTC)`. O registro da taxa sai com o instante
da coleta; o FII compara o `as_of` do registro com o da análise e abstém (BUG-2B-46) quando os
dois diferem. O teste do F3-6c trocava `_buscar_taxa_real` por um `Mock`. Corrige: F3-A-F10.
"""

from types import SimpleNamespace
from unittest.mock import Mock

from test_as_of_cascata import AGORA, AS_OF, Relogio

import market_engine
from sentinela.domain.enums import AssetType


def test_taxa_real_recebe_o_as_of_da_cascata(monkeypatch):
    monkeypatch.setattr(market_engine, "datetime", Relogio)
    pedidos = []
    monkeypatch.setattr(
        market_engine,
        "get_taxa_real",
        lambda *, as_of, janela=None: pedidos.append(as_of) or {},
    )
    m = market_engine.MarketEngine.__new__(market_engine.MarketEngine)
    m.asset_classifier = SimpleNamespace(
        classify=lambda *a: AssetType.STOCK, is_fii=lambda *a: False
    )
    m._aplicar_referencia = lambda t, d: d.update(classe_ativo="STOCK")
    m._buscar_yfinance = lambda t, d: d.update(preco_atual=10, fonte_preco="yfinance")
    m._buscar_brapi = Mock()
    for nome in (
        "_buscar_cvm",
        "_buscar_cvm_fii",
        "_buscar_rendimento_fii",
        "_buscar_proventos_b3",
    ):
        setattr(m, nome, lambda t, d, *, as_of: None)
    m._buscar_ifdata = lambda d, *, as_of: None
    m._buscar_liquidez = Mock()
    m._contexto_janelas = lambda d, instante, *, coletado_em=None: None
    m.buscar_dados_ticker_em("TSTA3", AS_OF)
    assert pedidos == [AS_OF], (pedidos, AGORA)
