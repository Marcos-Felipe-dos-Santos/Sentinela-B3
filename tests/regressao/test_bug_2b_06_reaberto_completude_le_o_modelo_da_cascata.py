"""BUG-2B-06 (reaberto): a completude lê `modelo`, e a cascata grava `modelo_bpp`.

Auditoria de fechamento da 2B (Codex, 25/10/2026): pela saída real da cascata, um banco com
todos os campos do modelo dele sai com 70%, porque `DataQualityReport.completude` não acha o
modelo e conta os três campos de empresa. A regressão anterior montava `modelo` à mão.
"""

from data_quality import _CAMPOS_ESPERADOS, DataQualityReport
from tests.test_market_engine import _engine
from tests.test_modelo_bpp import _CVMComModelo

INAPLICAVEIS = ("receita_liquida", "margem_liquida", "divida_liq_ebitda")


class _CVMDeBanco(_CVMComModelo):
    def modelo_do_documento(self, cd_cvm, ind):
        return "banco"


def test_banco_completo_pela_cascata_tem_completude_cheia(monkeypatch):
    prov = {"data_entrega": "2026-02-12", "data_coleta": "2026-02-20T18:00:00+00:00"}
    engine = _engine(monkeypatch, info={"currentPrice": 20.0}, cvm=_CVMDeBanco(prov))
    dados = {"cd_cvm": 9, "riscos_dados": []}
    engine._buscar_cvm("TSTB4", dados)
    assert dados["modelo_bpp"] == "banco"  # o que a cascata grava
    campos = {c: 1.0 for c in _CAMPOS_ESPERADOS if c not in INAPLICAVEIS}
    completude = DataQualityReport({**campos, **dados}).completude()
    assert completude["completude_pct"] == 100
    assert completude["completude_do_modelo_determinada"] is True
