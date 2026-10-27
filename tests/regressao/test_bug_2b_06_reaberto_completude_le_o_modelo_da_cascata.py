"""BUG-2B-06 (reaberto): a completude lê `modelo`, e a cascata grava `modelo_bpp`.

Auditoria de fechamento da 2B (Codex, 25/10/2026): pela saída real da cascata, um banco com
todos os campos do modelo dele sai com 70%, porque `DataQualityReport.completude` não acha o
modelo e conta os três campos de empresa. A regressão anterior montava `modelo` à mão.
"""

import pytest

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
    campos = {c: 1.0 for c in _CAMPOS_ESPERADOS if c not in INAPLICAVEIS}
    dados = {"cd_cvm": 9, "riscos_dados": [], **campos}
    engine._buscar_cvm("TSTB4", dados)
    assert dados["modelo_bpp"] == "banco"  # o que a cascata grava
    completude = DataQualityReport(dados).completude()
    assert completude["completude_pct"] == 100
    assert completude["completude_do_modelo_determinada"] is True


def test_banco_completo_pela_cascata_inteira_sem_sobrepor_campos(monkeypatch):
    from tests.test_market_engine_acoes_cvm import _ind
    from tests.test_market_engine_referencia import FakeReferencia, _indice, _registro

    class BancoCompleto(_CVMDeBanco):
        def __init__(self, proveniencia):
            super().__init__(proveniencia)
            self.consultas = []

        def calcular_indicadores(self, cd_cvm, anos=1, **kwargs):
            self.consultas.append(cd_cvm)
            return _ind(
                proveniencia=self.proveniencia,
                receita_liquida=None,
                margem_liquida=None,
                divida_liq_ebitda=None,
                lpa_divulgado={"especie": "ON", "conta": "3.99.01.01", "valor": 2.0},
            )

    prov = {"data_entrega": "2026-02-12", "data_coleta": "2026-02-20T18:00:00+00:00"}
    cvm = BancoCompleto(prov)
    engine = _engine(
        monkeypatch, info={"currentPrice": 20.0, "dividendYield": 4.0}, cvm=cvm
    )
    engine.referencia = FakeReferencia(
        _indice(_registro("TSTB3", cd_cvm=9, setor="Bancos"))
    )
    # Dublê do provedor da taxa, sem substituir etapas da cascata nem coletar rede.
    monkeypatch.setattr(
        "market_engine.get_taxa_real",
        lambda **kwargs: {"abstencao": "fonte sintética sem cesta"},
    )
    dados = engine.buscar_dados_ticker("TSTB3")
    assert cvm.consultas == [9]
    assert dados["modelo_bpp"] == "banco"
    assert dados["modelo_bpp_proveniencia"] == prov
    assert {
        c: dados[c] for c in _CAMPOS_ESPERADOS if c not in INAPLICAVEIS
    } == pytest.approx(
        {
            "preco_atual": 20.0,
            "dy": 0.04,
            "pl": 10.0,
            "pvp": 2.0,
            "roe": 0.2,
            "lpa": 2.0,
            "vpa": 10.0,
        }
    )
    assert all(dados.get(c) is None for c in INAPLICAVEIS)
    completude = DataQualityReport(dados).completude()
    assert completude["completude_pct"] == 100
    assert completude["completude_do_modelo_determinada"] is True
