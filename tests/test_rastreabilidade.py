"""Relatório estático de rastreabilidade v0 (F1-12): dados de fixture, sem rede."""

from datetime import date
from unittest.mock import patch

import pytest
from apoio_bazin import enriquecer_bazin
from apoio_escopo import de_empresa
from apoio_fii import enriquecer_fii
from apoio_gordon import AS_OF_GORDON, DiaGordon, enriquecer_gordon

from fii_engine import FIIEngine
from sentinela.methods import registry
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
    enriquecidos = enriquecer_bazin(enriquecer_gordon(de_empresa(dados)))
    if "taxa_real" in kw:
        enriquecidos["taxa_real"] = kw["taxa_real"]
    return enriquecidos


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
    return enriquecer_fii(dados)  # F2B-2: Informe e B3 sintéticos


def _contexto(dados, eh_fii=False, selic=0.145):
    motor = ValuationEngine()
    original = motor.processar
    motor.processar = lambda dados: original(dados, as_of=AS_OF_GORDON)
    motor_fii = FIIEngine()
    analisar = motor_fii.analisar
    motor_fii.analisar = lambda dados: analisar(dados, as_of=AS_OF_GORDON)
    with (
        patch("valuation_engine.date", DiaGordon),
        patch("fii_engine.get_selic_atual", return_value=selic),
    ):
        return rastreabilidade.construir_contexto(dados, eh_fii, HOJE, motor, motor_fii)


def _html(dados, eh_fii=False):
    return rastreabilidade.renderizar(_contexto(dados, eh_fii))


def test_relatorio_mostra_cada_metodo_com_versao():
    html = _html(_acao())
    for nome in ("Graham", "Bazin", "Lynch", "Gordon"):
        assert nome in html
    for nome in ("Graham", "Bazin", "Lynch", "Gordon"):
        assert f"{nome} <small>versão {registry.obter(nome).version}" in html
    assert "SEM_TAXA" in html and "NOMINAL" in html
    # premissas, parâmetros e resultado de um método que calculou
    assert "raiz de 22,5" in html
    assert "<td><code>pl_limite</code></td><td>25.0</td>" not in html
    assert "lpa_medio_normalizado" in html
    assert "Janela, fonte e cobertura" in html
    assert "R$ 122,47" in html
    # F2B-31: nenhum método de ação usa a Selic; a taxa do Bazin e a fonte dos proventos
    assert "<h2>Selic usada</h2>" not in html
    assert "<tr><td>taxa_aplicada</td><td>6,00%</td></tr>" in html
    assert "Proventos do Bazin (relação B3, F2B-31)" in html
    assert "critério fixo de 6% (ficha Bazin 1.0)" in html
    assert "Mediana" in html and "Score" not in html
    assert "Distância ao preço" in html


def test_relatorio_do_fii_mostra_rendimento_e_lente_de_pvp():
    html = _html(_fii(pvp=0.8), eh_fii=True)
    assert "Rendimento do FII" in html and "P/VP do FII" in html
    assert (
        "Rendimento do FII <small>versão 2.1.0" in html
        and "P/VP do FII <small>versão 1.2.0" in html
    )
    assert "desconto sobre o patrimônio" not in html
    assert "P/VP descritivo" in html
    # F2B-2: o spread datado e a NTN-B real formam a taxa; a Selic é só contexto
    assert "<td><code>spread</code></td>" in html
    assert "Taxa da lente do FII (F2B-2)" in html
    assert "a Selic não forma o preço justo" in html
    assert "selic_liquida (contexto)" in html


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
    # a Selic (E-6), que só o relatório do FII mostra desde o F2B-31
    assert "sem proveniência registrada" in _html(_fii(), eh_fii=True)


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
    assert rastreabilidade.validar_ticker(" tste3 ") == "TSTE3"
    assert rastreabilidade.validar_ticker("HGLG11") == "HGLG11"


def test_variacao_sobre_o_preco_esta_em_pontos_percentuais():
    # Mediana 122,47 (Graham; Bazin 133,33 a 6% desde o F2B-31; Gordon 30,60) sobre preço
    # 100: o motor já devolve o upside em pontos percentuais
    html = _html(_acao())
    assert "<th>Variação sobre o preço</th><td>22,50%</td>" in html
    assert "2.250" not in html


def test_variacao_do_fii_esta_em_pontos_percentuais():
    # F2B-2: 10 ÷ (7% + spread calibrado de 3,51%) = 95,19 contra o preço de 100.
    html = _html(_fii(), eh_fii=True)
    assert "<th>Variação sobre o preço</th><td>-4,80%</td>" in html


def test_dy_normalizado_aparece_ao_lado_do_bruto():
    # F2A-4: o DY chega em razão; o motor só aplica o invariante, e o texto diz isso.
    html = _html(_acao(dy=0.08))
    assert "<td>0,0800</td>" in html
    assert "dy (normalizado)" in html
    assert "a conversão de percentual é da fronteira do provedor (F2A-4)" in html


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
    # F2A-44: desde o F2A-11 a lente se abstém; o 1,0 e o provedor injetado saíram.
    html = _html(_fii(pvp=None), eh_fii=True)
    assert "ausente: a lente de P/VP se abstém e não pontua (F2A-11)" in html


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
    # F2B-62 (BUG-2B-50): a abstenção do FII aparece como tal, sem o preço como valor.
    assert "Abstenção da lente" in html
    assert "Nenhum método calculou" not in html
    assert "Preço justo do rendimento" not in html


def test_dy_bruto_nao_e_rotulado_como_razao():
    html = _html(_acao(dy=8.0))
    assert "<td>8,0000</td><td>como veio da fonte</td>" in html


def _proveniencia_do_insumo(contexto, campo):
    return next(i["proveniencia"] for i in contexto["insumos"] if i["campo"] == campo)


def test_alavancagem_ausente_aparece_como_nao_avaliada():
    # F2A-8: sem o dado, o motor não penaliza (o 0,0 interno); o relatório diz por quê.
    dados = _acao(
        divida_liq_ebitda=None,
        alavancagem_cvm={
            "regime": "pós-IFRS 16, arrendamento incluído na dívida",
            "motivos": {"divida_liq_ebitda": "EBITDA ≤ 0"},
        },
    )
    texto = _proveniencia_do_insumo(_contexto(dados), "divida_liq_ebitda")
    assert "alavancagem não avaliada (EBITDA ≤ 0)" in texto
    assert "não aplica a penalidade" in texto
    # Fora da CVM (sem o bloco), o motivo é a ausência na cascata.
    sem_cvm = _proveniencia_do_insumo(
        _contexto(_acao(divida_liq_ebitda=None)), "divida_liq_ebitda"
    )
    assert "alavancagem não avaliada (sem dado na cascata)" in sem_cvm
    # Com o dado, nada de "não avaliada".
    com_dado = _proveniencia_do_insumo(_contexto(_acao()), "divida_liq_ebitda")
    assert "não avaliada" not in com_dado


def test_regime_da_divida_e_declarado():
    dados = _acao(
        alavancagem_cvm={
            "regime": "pós-IFRS 16, arrendamento incluído na dívida",
            "motivos": {},
        }
    )
    texto = _proveniencia_do_insumo(_contexto(dados), "divida_liq_ebitda")
    assert "regime da dívida: pós-IFRS 16, arrendamento incluído na dívida" in texto


def test_relatorio_mostra_a_taxa_real_e_a_fonte():
    registro = {
        "ntnb": 0.07,
        "custo_capital_real": 0.12,
        "premio": 0.05,
        "vertice": "vencimentos ≥2035",
        "data_base": "2026-10-15",
        "fonte": "Tesouro Transparente",
        "inflacao": {
            "valor": 0.0426,
            "inicio": "2025-01-01",
            "fim": "2025-12-31",
            "proveniencia": {"fonte": "IBGE SIDRA 1737"},
        },
    }
    html = _html(_acao(taxa_real=registro))
    for texto in (
        "Taxa real",
        "7,00%",
        "12,00%",
        "5,00%",
        "Tesouro Transparente",
        "2026-10-15",
        "2035",
        "4,26%",
        "2025-01-01",
        "IBGE SIDRA 1737",
    ):
        assert texto in html

    assert "<h2>Taxa real</h2>" in html
    assert "Selic usada" not in html
    assert "os métodos de ação não usam Selic" in html


def test_gordon_real_exibe_versao_intermediarios_e_dva():
    d = _acao()
    d["gordon_cvm"]["proveniencia"] = {"fonte": "CVM DFP/DVA", "hash_sha256": "a" * 64}
    d["taxa_real"]["fonte"] = "Tesouro Transparente"
    html = _html(d)
    for texto in (
        "2.1.0",
        "Gordon",
        "REAL",
        "12,00%",
        "2,00%",
        "CVM DFP/DVA",
        "Tesouro Transparente",
    ):
        assert texto in html
