"""Relatório estático de rastreabilidade v0 (F1-12): dados de fixture, sem rede."""

from datetime import date
from unittest.mock import patch

import pytest

from fii_engine import FIIEngine
from sentinela.reports import rastreabilidade
from valuation_engine import ValuationEngine

HOJE = date(2026, 10, 2)
PROIBIDAS = ("recomendação", "recomendacao", "compra", "venda", "alocação sugerida")


def _prov(fonte, aviso=()):
    return {"source": fonte, "confidence": 0.9, "warnings": list(aviso)}


def _acao(**kw):
    dados = {
        "ticker": "TST3",
        "preco_atual": 100.0,
        "roe": 0.15,
        "pl": 10.0,
        "pvp": 1.5,
        "dy": 0.08,
        "divida_liq_ebitda": 1.2,
        "fonte_preco": "yfinance",
        "fonte_fundamentos": "CVM",
        "field_provenance": {
            "preco_atual": {
                "name": "preco_atual",
                "value": 100.0,
                "unit": "BRL",
                "provenance": _prov("yfinance"),
            },
            "dy": {
                "name": "dy",
                "value": 0.08,
                "unit": "ratio",
                "provenance": _prov("brapi"),
            },
            "pl": {
                "name": "pl",
                "value": 10.0,
                "unit": "ratio",
                "provenance": _prov("CVM"),
            },
            "pvp": {
                "name": "pvp",
                "value": 1.5,
                "unit": "ratio",
                "provenance": _prov("CVM"),
            },
            "roe": {
                "name": "roe",
                "value": 0.15,
                "unit": "ratio",
                "provenance": _prov("CVM"),
            },
        },
    }
    dados.update(kw)
    return dados


def _fii(**kw):
    dados = {
        "ticker": "TST11",
        "preco_atual": 100.0,
        "dy": 0.10,
        "pvp": 0.9,
        "tipo": "Tijolo",
        "fonte_preco": "yfinance",
        "fonte_fundamentos": "brapi",
        "field_provenance": {},
    }
    dados.update(kw)
    return dados


def _contexto(dados, eh_fii=False, selic=0.145):
    with (
        patch("valuation_engine.get_selic_atual", return_value=selic),
        patch("fii_engine.get_selic_atual", return_value=selic),
    ):
        return rastreabilidade.construir_contexto(
            dados, eh_fii, HOJE, ValuationEngine(), FIIEngine()
        )


def _html(dados, eh_fii=False):
    return rastreabilidade.renderizar(_contexto(dados, eh_fii))


def test_relatorio_mostra_cada_metodo_com_versao():
    html = _html(_acao())
    for nome in ("Graham", "Bazin", "Lynch", "Gordon"):
        assert nome in html
    assert html.count("versão 1.0.0") == 4
    assert "SEM_TAXA" in html and "NOMINAL" in html
    # premissas, parâmetros e resultado de um método que calculou
    assert "raiz de 22,5" in html
    assert "<td><code>pl_limite</code></td><td>25.0</td>" in html
    assert "R$ 122,47" in html
    # a Selic usada e a síntese
    assert "14,50%" in html
    assert "Mediana" in html and "Score" in html


def test_relatorio_do_fii_mostra_rendimento_e_lente_de_pvp():
    html = _html(_fii(pvp=0.8), eh_fii=True)
    assert "Bazin FII" in html and "P/VP do FII" in html
    assert html.count("versão 1.0.0") == 2
    assert "desconto sobre o patrimônio" in html
    assert "fator_ir" in html


def test_relatorio_mostra_motivo_da_abstencao():
    html = _html(_acao())
    # perfil renda: o Lynch se abstém
    assert "Lynch" in html
    assert "Abstenção" in html
    assert "perfil renda" in html


def test_relatorio_mostra_insumo_ausente_e_metodo_nao_calculado():
    html = _html(_fii(dy=None), eh_fii=True)
    assert "DY ausente ou inválido" in html
    assert "não calculado" in html


def test_proveniencia_dos_cinco_campos_e_heranca_dos_demais():
    html = _html(_acao())
    assert "yfinance" in html
    assert "brapi" in html
    assert "herdada de fonte_fundamentos: CVM" in html
    assert "sem proveniência registrada" in html  # a Selic (E-6)


def test_relatorio_declara_os_limites_conhecidos_e_o_aviso():
    html = _html(_acao())
    assert "E-6" in html and "E-1" in html
    assert "revisão metodológica" in html
    assert "Não é consultoria financeira" in html


def test_relatorio_escapa_html():
    html = _html(_acao(fonte_fundamentos="<script>alert(1)</script>", ticker="TST3"))
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


@pytest.mark.parametrize(
    "dados_eh_fii",
    [(_acao(), False), (_fii(), True), (_acao(roe=0.25, dy=0.02), False)],
)
def test_relatorio_sem_vocabulario_proibido(dados_eh_fii):
    dados, eh_fii = dados_eh_fii
    html = _html(dados, eh_fii).lower()
    for palavra in PROIBIDAS:
        assert palavra not in html


def test_relatorio_nao_mostra_o_rotulo_de_classificacao_da_v1():
    html = _html(_acao())
    for rotulo in ("COMPRA", "NEUTRO", "VENDA", "QUALIDADE"):
        assert rotulo not in html


def test_gravar_cria_o_arquivo_em_outputs_por_ticker_e_data(tmp_path):
    caminho = rastreabilidade.gravar("<html></html>", "TST3", HOJE, tmp_path)
    assert caminho == tmp_path / "rastreabilidade" / "TST3-2026-10-02.html"
    assert caminho.read_text(encoding="utf-8") == "<html></html>"


@pytest.mark.parametrize("ruim", ["", "../x", "TST3/..", "tst 3", "T" * 12, "TST3;rm"])
def test_ticker_invalido_e_recusado(ruim):
    with pytest.raises(ValueError, match="ticker"):
        rastreabilidade.validar_ticker(ruim)


def test_ticker_valido_e_normalizado():
    assert rastreabilidade.validar_ticker(" tst3 ") == "TST3"
    assert rastreabilidade.validar_ticker("HGLG11") == "HGLG11"


def test_variacao_sobre_o_preco_esta_em_pontos_percentuais():
    # Mediana 55,17 sobre preço 100: o motor já devolve o upside em pontos percentuais
    html = _html(_acao())
    assert "<th>Variação sobre o preço</th><td>-44,80%</td>" in html
    assert "4.480" not in html


def test_variacao_do_fii_esta_em_pontos_percentuais():
    html = _html(_fii(), eh_fii=True)
    assert "<th>Variação sobre o preço</th><td>-18,90%</td>" in html


def test_dy_normalizado_aparece_ao_lado_do_bruto():
    html = _html(_acao(dy=8.0))  # percentual bruto: o motor normaliza para 0,08
    assert "<td>8,0000</td>" in html
    assert "dy (normalizado)" in html
    assert "<td>0,0800</td>" in html


def test_dy_invalido_zerado_pelo_motor_fica_visivel():
    html = _html(_acao(dy=0.3))
    assert "dy (normalizado)" in html
    assert "<td>0,0000</td>" in html


def test_ticker_em_situacao_especial_nao_acusa_valor_nao_finito():
    with patch("valuation_engine.DISTRESSED_TICKERS", frozenset({"TST3"})):
        html = _html(_acao())
    assert "guarda de situação especial" in html
    assert "valor não finito" not in html


def test_sintese_sem_metodo_nao_chama_o_preco_de_mediana():
    html = _html(_acao(pl=0.0, pvp=0.0, dy=0.0, roe=0.0))
    assert "Nenhum método calculou" in html
    assert "Mediana dos métodos calculados" not in html


def test_pvp_ausente_do_fii_e_sinalizado():
    html = _html(_fii(pvp=None), eh_fii=True)
    assert "o motor usa P/VP = 1,0" in html


def test_captura_nao_deixa_os_motores_instrumentados():
    import valuation_engine

    _html(_acao())
    assert "calcular" not in valuation_engine._GRAHAM.__dict__


def test_captura_desfaz_mesmo_se_um_metodo_levantar_excecao():
    import valuation_engine
    from sentinela.methods.graham import Graham

    with patch.object(Graham, "_calcular", side_effect=RuntimeError("falha simulada")):
        with pytest.raises(RuntimeError, match="falha simulada"):
            _contexto(_acao())
    assert "calcular" not in valuation_engine._GRAHAM.__dict__
    assert "calcular" not in valuation_engine._BAZIN.__dict__


def test_analise_vazia_vira_erro_claro():
    with pytest.raises(ValueError, match="dados insuficientes"):
        _contexto(_acao(preco_atual=0))


def test_sintese_do_fii_sem_dy_nao_chama_o_preco_de_preco_justo():
    html = _html(_fii(dy=None), eh_fii=True)
    assert "Nenhum método calculou" in html
    assert "Preço justo do rendimento" not in html


def test_dy_bruto_nao_e_rotulado_como_razao():
    html = _html(_acao(dy=8.0))
    assert "<td>8,0000</td><td>como veio da fonte</td>" in html
