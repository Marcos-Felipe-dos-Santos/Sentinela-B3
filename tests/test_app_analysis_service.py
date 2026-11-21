"""F3-6b: mesma interface do Terminal, com uma única execução pelo serviço.

A referência anterior é congelada pelo hash AST do bloco do HEAD 917994e.
AppTest compara dados/tabelas/textos/gráficos com esse fluxo retido; todos os
ativos e valores abaixo são sintéticos, para caracterização da apresentação.
"""

import ast
import hashlib
import json
import sqlite3
import textwrap
from contextlib import closing
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, create_autospec
from zoneinfo import ZoneInfo

import pandas as pd
import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from market_engine import MarketEngine
from sentinela.services.analyze_asset import AnalysisService as ServicoReal

APP = Path(__file__).resolve().parents[1] / "app.py"
AST_ANTERIOR = "a53439c2bf6c8b34d778754e7d3a81cccd0cb1fd5fcdb8fc9bfa110605590b4f"
# Gemini D1: Config sem reset destrutivo; trecho anterior à Config preservado.
RENDER_ANTERIOR = "0d71cf7445382ebd0c387ee571d829f96b7fa44cf3b975162009b441f66c5b46"


ORQUESTRACAO_ANTERIOR = """
# A. Dados Básicos
dados = market.buscar_dados_ticker(ticker)
if not dados or 'erro' in dados:
    st.error("Ativo não encontrado."); st.stop()

# B. Detecção FII
# CORRIGIDO: Yahoo retorna quote_type='EQUITY' para FIIs BR (não MUTUALFUND)
# Usar whitelist como critério primário + fallback de sufixo 11
is_fii = asset_classifier.is_fii(ticker, dados)

# C. Motores Específicos
if is_fii:
    analise = fii_engine.analisar(dados)
    # CORRIGIDO: guard para None (fii_engine pode retornar None se sem dados)
    if analise is None:
        st.error("FII sem dados suficientes para análise.")
        st.stop()
    peers_data = {}
else:
    analise = val_engine.processar(dados)
    if analise is None: st.error("Erro Valuation"); st.stop()
    peers_data = peers_engine.comparar(ticker)

# D. Análise Técnica
hist = dados.get('historico', pd.DataFrame())
tech_data = tech_engine.calcular_indicadores(hist)

# E. IA e Persistência
from sentinela.domain.apresentacao import mesclar_analise

dados = mesclar_analise(dados, analise)
dados["tech"] = tech_data

ia_resp = ai_engine.analisar(ticker, dados)
dados['analise_ia'] = ia_resp['content']

# CORREÇÃO: Não salvar histórico pesado no banco
dados_salvar = {k: v for k, v in dados.items() if k != 'historico'}
db.salvar_analise(dados_salvar)
"""


def _preparar(monkeypatch, tmp_path, *, fii=False, falha=None):
    dados = {
        "ticker": "TSTF11" if fii else "TSTA3",
        "classe_ativo": "FII" if fii else "STOCK",
        "modelo_bpp": "empresa",
        "preco_atual": 10.0,
        "pl": 10,
        "pvp": 1,
        "roe": 0.12,
        "dy": 0.05,
        "lpa": 1,
        "vpa": 10,
        "historico": pd.DataFrame(),
        "fonte_preco": "fonte sintética",
        "data_preco": "2026-11-09",
    }
    lente = {
        "versao": "2.1.0",
        "valor": 20.0,
        "abstencao": None,
        "regime": "nominal",
        "janela": {"inicio": "2021", "fim": "2025"},
        "premissas": ["hipótese sintética"],
        "distancia_ao_preco_pct": 100.0,
        "as_of": "2026-11-10T15:00:00+00:00",
        "fonte_preco": "fonte sintética",
        "data_preco": "2026-11-09",
    }
    analise = {
        "apresentacao_versao": "1.0",
        "perfil": "DESCRITIVO",
        "lentes": {"Lente": lente},
    }
    # Achado 10: o dublê tem a interface do MarketEngine, para o serviço seguir o caminho de
    # produção (`buscar_dados_ticker_em`); o oráculo legado congelado usa `buscar_dados_ticker`.
    mercado = create_autospec(MarketEngine, instance=True)
    val, fundo, tecnica, pares, ia = (Mock() for _ in range(5))

    def _buscar(ticker, as_of=None):
        return deepcopy(dados) if falha != "dados" else {"erro": "indisponível"}

    mercado.buscar_dados_ticker_em.side_effect = _buscar
    mercado.buscar_dados_ticker.side_effect = _buscar
    val.processar.side_effect = lambda *a, **k: (
        None if falha == "motor" else deepcopy(analise)
    )
    fundo.analisar.side_effect = val.processar.side_effect
    tecnica.calcular_indicadores.return_value = {"rsi": 55, "tendencia": "Neutro"}
    pares.comparar.return_value = {"Setor": "sintético", "PL_Media_Peers": 11.0}
    ia.analisar.return_value = {
        "content": "Hipóteses do estudo sintético.",
        "model": "modelo-sintético",
    }
    monkeypatch.setattr("market_engine.MarketEngine", lambda: mercado)
    monkeypatch.setattr("valuation_engine.ValuationEngine", lambda: val)
    monkeypatch.setattr("fii_engine.FIIEngine", lambda: fundo)
    monkeypatch.setattr("technical_engine.TechnicalEngine", lambda: tecnica)
    monkeypatch.setattr("peers_engine.PeersEngine", lambda market: pares)
    monkeypatch.setattr("ai_core.SentinelaAI", lambda: ia)
    chamadas = []

    class ServicoObservado(ServicoReal):
        def analisar(self, ticker, as_of, **opcoes):
            chamadas.append((ticker, as_of, self.hoje))
            return super().analisar(ticker, as_of, **opcoes)

    monkeypatch.setattr(
        "sentinela.services.analyze_asset.AnalysisService", ServicoObservado
    )
    pasta = tmp_path / "execucao"
    pasta.mkdir()
    monkeypatch.chdir(pasta)
    return chamadas, (mercado, val, fundo, tecnica, pares, ia), pasta


def _rodar(fonte, ticker="TSTA3"):
    st.cache_resource.clear()
    st.cache_data.clear()
    at = AppTest.from_string(fonte, default_timeout=60).run()
    assert not at.exception
    at.text_input[0].set_value(ticker)
    at.button[0].click().run()
    assert not at.exception
    return at


def _interface(at):
    saida = {
        tipo: [e.value for e in getattr(at, tipo)]
        for tipo in (
            "title",
            "subheader",
            "markdown",
            "caption",
            "info",
            "warning",
            "success",
            "error",
        )
    }
    saida["metric"] = [(e.label, e.value, e.delta) for e in at.metric]
    saida["dataframe"] = [e.value.to_dict(orient="split") for e in at.dataframe]
    saida["plotly"] = [json.loads(e.proto.spec) for e in at.get("plotly_chart")]
    return saida


def _fonte_legada(fonte):
    referencia = (
        "def _referencia_terminal_anterior(ticker):\n"
        + textwrap.indent(ORQUESTRACAO_ANTERIOR.strip() + "\n", "    ")
        + "    return dados, is_fii, analise, peers_data, hist, tech_data, ia_resp\n\n\n"
    )
    fonte = fonte.replace("st.sidebar.title(", referencia + "st.sidebar.title(", 1)
    arvore = ast.parse(fonte)
    inicio = next(
        n.lineno
        for n in ast.walk(arvore)
        if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "as_of" for t in n.targets)
    )
    fim = next(
        n.end_lineno
        for n in ast.walk(arvore)
        if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "ia_resp" for t in n.targets)
        and n.lineno >= inicio
    )
    linhas = fonte.splitlines(keepends=True)
    linhas[inicio - 1 : fim] = [
        "            dados, is_fii, analise, peers_data, hist, tech_data, ia_resp = _referencia_terminal_anterior(ticker)\n"
    ]
    return "".join(linhas)


def test_corpo_legado_e_renderizacao_conservam_referencia_anterior():
    fonte = APP.read_text()
    arvore = ast.parse(fonte)
    referencia = ast.parse(ORQUESTRACAO_ANTERIOR)
    assert (
        hashlib.sha256(
            ast.dump(referencia, include_attributes=False).encode()
        ).hexdigest()
        == AST_ANTERIOR
    )
    # A retenção em produção só dura até F3-9a. O oráculo dos testes é independente.
    legados = [
        n
        for n in arvore.body
        if isinstance(n, ast.FunctionDef) and n.name == "_orquestrar_analise_legada"
    ]
    assert len(legados) <= 1
    for legado in legados:
        assert isinstance(legado.body[-1], ast.Return)
        corpo = ast.Module(body=legado.body[:-1], type_ignores=[])
        assert (
            hashlib.sha256(
                ast.dump(corpo, include_attributes=False).encode()
            ).hexdigest()
            == AST_ANTERIOR
        )
    assert not [
        n
        for n in ast.walk(arvore)
        if isinstance(n, ast.Call)
        and isinstance(n.func, ast.Name)
        and n.func.id == "_orquestrar_analise_legada"
    ]
    render = fonte[fonte.index("            # --- RENDERIZAÇÃO ---") :]
    assert hashlib.sha256(render.encode()).hexdigest() == RENDER_ANTERIOR


@pytest.mark.parametrize(
    "fii,falha",
    [(False, None), (True, None), (False, "dados"), (False, "motor"), (True, "motor")],
)
def test_terminal_preserva_interface_do_fluxo_anterior(
    monkeypatch, tmp_path, fii, falha
):
    chamadas, _, pasta = _preparar(monkeypatch, tmp_path, fii=fii, falha=falha)
    fonte = APP.read_text()
    ticker = "TSTF11" if fii else "TSTA3"
    atual = _interface(_rodar(fonte, ticker))
    assert len(chamadas) == 1
    assert chamadas[0][0] == ticker
    # Oráculo congelado só nos testes, sem criar chamador da função legada do app.
    antiga = pasta / "anterior"
    antiga.mkdir()
    monkeypatch.chdir(antiga)
    anterior = _interface(_rodar(_fonte_legada(fonte), ticker))
    assert atual == anterior
    st.cache_resource.clear()
    st.cache_data.clear()


def test_terminal_chama_entrada_temporal_e_persiste_uma_vez(monkeypatch, tmp_path):
    chamadas, motores, pasta = _preparar(monkeypatch, tmp_path)
    at = _rodar(APP.read_text())
    assert len(chamadas) == 1
    ticker, as_of, hoje = chamadas[0]
    assert ticker == "TSTA3"
    assert isinstance(as_of, datetime) and as_of.utcoffset() is not None
    assert hoje == as_of.astimezone(ZoneInfo("America/Sao_Paulo")).date()
    mercado, val, fundo, tecnica, pares, ia = motores
    mercado.buscar_dados_ticker_em.assert_called_once_with("TSTA3", as_of)
    mercado.buscar_dados_ticker.assert_not_called()
    val.processar.assert_called_once()
    assert val.processar.call_args.kwargs == {"as_of": as_of}
    fundo.analisar.assert_not_called()
    tecnica.calcular_indicadores.assert_called_once()
    pares.comparar.assert_called_once_with("TSTA3")
    ia.analisar.assert_called_once()
    with closing(sqlite3.connect(pasta / "sentinela_store.db")) as conn:
        assert conn.execute(
            "SELECT tipo, metodo, versao FROM resultados_analise"
        ).fetchall() == [("original", "Lente", "2.1.0")]
        assert conn.execute("SELECT COUNT(*) FROM analises").fetchone() == (0,)
    assert "Modelo: modelo-sintético" in [e.value for e in at.caption]
    st.cache_resource.clear()
    st.cache_data.clear()
