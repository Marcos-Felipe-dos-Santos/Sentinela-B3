"""BUG-2A-13: FII sem `cd_cvm` recebe o risco "ticker fora da cobertura da CVM".

`market_engine.MarketEngine._buscar_cvm` registra o risco para qualquer ticker sem CD_CVM,
antes de `_buscar_cvm_fii` consultar o Informe Mensal pelo CNPJ. O FII coberto pelo Informe
sai com um diagnóstico falso. Origem: auditoria externa da Fase 2A (Gemini e Codex,
15/10/2026).
"""

from market_engine import RISCO_FORA_DA_CVM
from tests.test_market_engine import FakeCVM, _engine, _historico
from tests.test_market_engine_fii_cvm import INFO, INFORME, _InformeFalso


def test_fii_coberto_pelo_informe_nao_ganha_risco_de_fora_da_cvm(monkeypatch):
    # FakeCVM injeta o índice dos mapas públicos: HGLG11 tem CNPJ e não tem CD_CVM.
    engine = _engine(monkeypatch, info=INFO, historico=_historico(90.0), cvm=FakeCVM())
    engine.cvm_fii = _InformeFalso(INFORME)
    dados = engine.buscar_dados_ticker("HGLG11")
    assert dados["cvm_disponivel"] is True
    assert RISCO_FORA_DA_CVM not in dados["riscos_dados"]
