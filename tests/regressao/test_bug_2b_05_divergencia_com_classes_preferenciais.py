"""BUG-2B-05: a divergência de ações compara a classe do yfinance com o total da espécie.

Numa companhia com mais de uma classe preferencial (PNA e PNB no FCA), a Composição do Capital
só traz o total das preferenciais; `acoes_cvm.divergencia_acoes` compara esse total com a
`sharesOutstanding` da classe (USIM5, BRSR5, BRSR6). A comparação não tem a mesma base.
Origem: F2B-21, pergunta 8 (auditoria externa da 2A, correção 6).
"""

import pytest

from tests.test_market_engine_acoes_cvm import _banrisul, _por_classe


@pytest.mark.xfail(
    strict=True,
    reason="BUG-2B-05 · divergência de ações da classe contra o total da espécie · corrige: F2C-15",
)
def test_classe_preferencial_com_varias_classes_nao_e_comparada(monkeypatch):
    dados = _por_classe(
        monkeypatch,
        "TSTB5",
        {"ON": [2.1], "PNA": [2.3]},
        registro=_banrisul("TSTB5", "PN", "PNA"),
    )
    assert dados.get("divergencia_acoes") is None
