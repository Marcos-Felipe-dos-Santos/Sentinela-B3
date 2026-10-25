"""Bazin 2.0.0 no motor de ações: DY da relação B3, avisos e relatório (F2B-31)."""

from unittest.mock import patch

import pytest
from apoio_bazin import enriquecer_bazin
from apoio_escopo import de_empresa
from apoio_gordon import AS_OF_GORDON

from sentinela.methods.bazin import AVISO_PREJUIZO
from valuation_engine import ValuationEngine


def _acao(**kw):
    dados = {
        "ticker": "TST3",
        "preco_atual": 100.0,
        "roe": 0.12,
        "pl": 10.0,
        "pvp": 1.0,
        "dy": 0.08,
        "classe_ativo": "STOCK",
    }
    dados.update(kw)
    return dados


def _processar(dados, selic=0.10):
    with patch("valuation_engine.get_selic_atual", return_value=selic):
        return ValuationEngine().processar(de_empresa(dados), as_of=AS_OF_GORDON)


def _bazin(resultado):
    for parte in str(resultado["metodos_usados"]).split(", "):
        if parte.startswith("Bazin: R$"):
            return float(parte.removeprefix("Bazin: R$"))
    return None


def test_bazin_vale_d_sobre_6_por_cento_com_o_preco_de_referencia():
    # Preço da cascata (100) diferente do fechamento de referência (80): o valor é D ÷ 0,06,
    # e o DY é o de D sobre o fechamento de referência.
    dados = enriquecer_bazin(_acao())  # D = 8
    dados["proventos_b3"]["fechamentos"] = {"2026-10-19": 80.0}
    dados["proventos_b3"]["conferencia_yfinance"] = {"2026-06-11": 8.0}
    r = _processar(dados)
    assert _bazin(r) == pytest.approx(133.33, abs=0.01)
    assert dados["bazin_proventos"]["d_bruto_12m"] == pytest.approx(8.0)
    assert "bazin_diagnostico" not in dados


@pytest.mark.parametrize("selic", [0.02, 0.1475, 0.30])
def test_selic_nao_muda_o_bazin(selic):
    assert _bazin(_processar(enriquecer_bazin(_acao()), selic)) == pytest.approx(
        133.33, abs=0.01
    )


def test_sem_relacao_b3_o_bazin_abstem_com_o_motivo():
    dados = _acao()
    r = _processar(dados)
    assert _bazin(r) is None
    assert dados["bazin_diagnostico"] == "insumo ausente: relação de proventos da B3"
    # o DY da cascata não substitui a relação B3
    enriquecido = enriquecer_bazin(_acao())
    _processar(enriquecido)
    enriquecido["proventos_b3"] = {"abstencao": "fora do escopo do Bazin: modelo banco"}
    _processar(enriquecido)
    assert "bazin_proventos" not in enriquecido
    assert enriquecido["bazin_diagnostico"] == "fora do escopo do Bazin: modelo banco"


def test_dy_da_b3_acima_de_25_por_cento_nao_e_confiavel():
    dados = enriquecer_bazin(_acao(dy=0.30))
    dados["dy"] = 0.08  # o DY da cascata é outro: vale o da B3
    assert _bazin(_processar(dados)) is None


def test_perfil_pelo_dy_da_b3():
    # ROE alto com DY da cascata baixo daria perfil crescimento; o DY da B3 (8%) é renda.
    dados = enriquecer_bazin(_acao(roe=0.30))
    dados["dy"] = 0.01
    assert _bazin(_processar(dados)) == pytest.approx(133.33, abs=0.01)
    baixo = enriquecer_bazin(_acao(roe=0.30, dy=0.03))
    assert _bazin(_processar(baixo)) is None


def test_avisos_da_conferencia_e_do_prejuizo_vao_para_os_riscos():
    dados = enriquecer_bazin(_acao(lpa=-1.0))
    dados["proventos_b3"]["conferencia_yfinance"] = {"2026-06-11": 7.0}
    r = _processar(dados)
    assert AVISO_PREJUIZO in r["riscos"]
    assert any(a.startswith("proventos de 12 meses divergem") for a in r["riscos"])
    assert _bazin(r) == pytest.approx(133.33, abs=0.01)


def test_lpa_da_cascata_invalido_nao_gera_aviso():
    for lpa in (float("nan"), "x", True, None):
        r = _processar(enriquecer_bazin(_acao(lpa=lpa)))
        assert AVISO_PREJUIZO not in r["riscos"]


def test_aviso_nao_se_repete_nem_entra_sem_o_bazin():
    dados = enriquecer_bazin(_acao(dy=0.03))
    dados["proventos_b3"]["conferencia_yfinance"] = None
    r = _processar(dados)
    assert "conferência dos proventos no yfinance indisponível" not in r["riscos"]


def test_relatorio_mostra_a_fonte_ou_o_motivo():
    from sentinela.reports.rastreabilidade import _texto_proventos_bazin

    dados = enriquecer_bazin(_acao())
    _processar(dados)
    assert _texto_proventos_bazin(dados) == (
        "R$ 8,000000 brutos por papel em 12 meses, datas ex de 2025-10-19 (exclusive) "
        "a 2026-10-19, 1 eventos; critério fixo de 6% (ficha Bazin 1.0)"
    )
    assert _texto_proventos_bazin({"bazin_diagnostico": "x"}) == "não calculado: x"
    assert _texto_proventos_bazin({}) == "não calculado: sem relação B3"
