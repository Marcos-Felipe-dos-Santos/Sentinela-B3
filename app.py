import time
from typing import Any, Dict, Optional

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from database import DatabaseManager
from market_engine import MarketEngine
from valuation_engine import ValuationEngine
from fii_engine import FIIEngine
from technical_engine import TechnicalEngine
from portfolio_engine import PortfolioEngine
from peers_engine import PeersEngine
from ai_core import SentinelaAI
from config import APP_VERSION, FIIS_CONHECIDOS, UNITS_CONHECIDAS

st.set_page_config(page_title=f"Sentinela B3 {APP_VERSION}", layout="wide", page_icon="🦅")


def _safe_df_for_display(df: pd.DataFrame) -> pd.DataFrame:
    """Converte colunas object/mixed para str, evitando ArrowInvalid no Streamlit.

    Arrow serialization falha quando uma coluna mistura float e str
    (ex: tech_data transposto com 'Neutro' e 50.0 na mesma coluna).
    Apenas colunas object são convertidas — numéricas permanecem intactas.
    """
    df = df.copy()
    for col in df.columns:
        if df[col].dtype == "object":
            df[col] = df[col].astype(str)
    return df

@st.cache_resource
def load_engines():
    try:
        db = DatabaseManager()
        market = MarketEngine()
        val = ValuationEngine()
        fii = FIIEngine()
        tech = TechnicalEngine()
        port = PortfolioEngine()
        peers = PeersEngine(market)
        ai = SentinelaAI()
        return db, market, val, fii, tech, port, peers, ai
    except Exception as e:
        st.error(f"Erro Init: {e}")
        st.stop()

db, market, val_engine, fii_engine, tech_engine, port_engine, peers_engine, ai_engine = load_engines()


@st.cache_data(ttl=300)
def buscar_dados_ticker_cached(ticker: str) -> Optional[Dict[str, Any]]:
    """Busca dados de mercado com cache curto para reduzir chamadas externas.

    Args:
        ticker: Código do ativo na B3.

    Returns:
        Dados fundamentalistas e histórico do ativo, quando disponíveis.
    """
    return market.buscar_dados_ticker(ticker)


st.sidebar.title("🦅 Sentinela B3")
modo = st.sidebar.radio("Menu", ["Terminal", "Carteira", "Gestor", "Config"])

# ==========================================
# 1. TERMINAL
# ==========================================
if modo == "Terminal":
    st.title("🔎 Terminal de Análise")
    ticker = st.text_input("Ticker:").upper().strip()
    
    if st.button("Analisar") and ticker:
        with st.spinner(f"Analisando {ticker}..."):
            # A. Dados Básicos
            dados = buscar_dados_ticker_cached(ticker)
            if not dados or 'erro' in dados:
                st.error("Ativo não encontrado."); st.stop()
            
            # B. Detecção FII
            # CORRIGIDO: Yahoo retorna quote_type='EQUITY' para FIIs BR (não MUTUALFUND)
            # Usar whitelist como critério primário + fallback de sufixo 11
            is_fii = (
                ticker in FIIS_CONHECIDOS  # whitelist de FIIs conhecidos
                or (
                    dados.get('quote_type') == 'MUTUALFUND'  # reforço se Yahoo funcionar
                    or (
                        "11" in ticker
                        and "SA" not in ticker
                        and ticker not in UNITS_CONHECIDAS  # excluir units
                    )
                )
            )
            
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
            dados.update(analise)
            dados['tech'] = tech_data
            
            ia_resp = ai_engine.analisar(ticker, dados)
            dados['analise_ia'] = ia_resp['content']
            
            # CORREÇÃO: Não salvar histórico pesado no banco
            dados_salvar = {k: v for k, v in dados.items() if k != 'historico'}
            db.salvar_analise(dados_salvar)
            
            # --- RENDERIZAÇÃO ---
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Preço", f"R$ {dados.get('preco_atual', 0):.2f}")
            k2.metric("Valor Justo", f"R$ {analise.get('fair_value', 0):.2f}")
            k3.metric("Recomendação", analise.get('recomendacao', '-'))
            k4.metric("Score", f"{analise.get('score_final', 0)}/100")
            
            t1, t2, t3 = st.tabs(["Valuation & IA", "Técnica & Peers", "Gráfico"])
            
            with t1:
                st.info(f"Perfil: {analise.get('perfil', 'N/A')}")
                st.write(f"**Métodos:** {analise.get('metodos_usados', '-')}")
                st.divider()
                st.subheader("Veredito IA")
                st.write(dados['analise_ia'])
                st.caption(f"Modelo: {ia_resp.get('model', '-')}")
                
            with t2:
                c1, c2 = st.columns(2)
                with c1:
                    st.subheader("Análise Técnica")
                    st.dataframe(_safe_df_for_display(pd.DataFrame([tech_data]).T))
                with c2:
                    st.subheader("Comparação Setorial")
                    if 'erro' not in peers_data:
                        st.write(f"Setor: {peers_data.get('Setor', '-')}")
                        st.json(peers_data)
                    else:
                        st.warning("Sem peers.")
            
            with t3:
                # CORREÇÃO CRÍTICA v12.1: Crash Fix (None.empty)
                if hist is not None and not hist.empty:
                    required_columns = {'Open', 'High', 'Low', 'Close'}
                    missing_columns = required_columns.difference(hist.columns)
                    if missing_columns:
                        st.warning(
                            "Dados históricos incompletos para gráfico: "
                            f"colunas ausentes {', '.join(sorted(missing_columns))}."
                        )
                    else:
                        fig = go.Figure(data=[
                            go.Candlestick(
                                x=hist.index,
                                open=hist['Open'],
                                high=hist['High'],
                                low=hist['Low'],
                                close=hist['Close'],
                                name='OHLC',
                            ),
                            go.Scatter(
                                x=hist.index,
                                y=hist['Close'].rolling(50).mean(),
                                line=dict(color='orange', width=1),
                                name='MA50',
                            ),
                            go.Scatter(
                                x=hist.index,
                                y=hist['Close'].rolling(200).mean(),
                                line=dict(color='blue', width=1),
                                name='MA200',
                            ),
                        ])
                        fig.update_layout(xaxis_rangeslider_visible=False, height=400)
                        st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("Sem dados históricos para gráfico.")

# ==========================================
# 2. CARTEIRA (RESTAURADA v12.1)
# ==========================================
elif modo == "Carteira":
    st.title("💰 Minha Carteira")
    
    with st.expander("Adicionar Ativo"):
        with st.form("add_ativo"):
            c1, c2, c3 = st.columns(3)
            t = c1.text_input("Ticker").upper()
            q = c2.number_input("Qtd", min_value=1, step=1)
            p = c3.number_input("Preço", min_value=0.01)
            if st.form_submit_button("Salvar"):
                db.adicionar_posicao(t, q, p)
                st.success("Salvo!")
                time.sleep(0.5)
                st.rerun()
    
    carteira = db.listar_carteira()
    if carteira:
        df = pd.DataFrame(carteira)
        
        # Atualização em tempo real
        precos_atuais = {}
        with st.spinner("Atualizando cotações..."):
            for ticker in df['ticker']:
                d = buscar_dados_ticker_cached(ticker)
                p = d.get('preco_atual', 0) if d else 0
                precos_atuais[ticker] = p
        
        df['Preço Atual'] = df['ticker'].map(precos_atuais)
        df['Total Investido'] = df['quantidade'] * df['preco_medio']
        df['Valor Atual'] = df['quantidade'] * df['Preço Atual']
        
        df['Rentabilidade %'] = df.apply(
            lambda x: ((x['Preço Atual'] / x['preco_medio']) - 1) * 100 if x['preco_medio'] > 0 else 0, 
            axis=1
        )

        st.dataframe(
            _safe_df_for_display(df[['ticker', 'quantidade', 'preco_medio', 'Preço Atual', 'Valor Atual', 'Rentabilidade %']]),
            column_config={
                "preco_medio": st.column_config.NumberColumn("PM", format="R$ %.2f"),
                "Preço Atual": st.column_config.NumberColumn("Preço Atual", format="R$ %.2f"),
                "Valor Atual": st.column_config.NumberColumn("Valor Total", format="R$ %.2f"),
                "Rentabilidade %": st.column_config.NumberColumn("Rentab.", format="%.2f%%"),
            },
            hide_index=True
        )
        
        total = df['Valor Atual'].sum()
        st.metric("Patrimônio Total", f"R$ {total:,.2f}")

        with st.expander("🗑️ Remover Ativo da Carteira"):
            ticker_remover = st.text_input(
                "Ticker para remover:",
                key="remover_ticker"
            ).upper().strip()
            if st.button("Remover", key="btn_remover"):
                if ticker_remover:
                    db.remover_posicao(ticker_remover)
                    st.success(f"{ticker_remover} removido da carteira.")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.warning("Digite o ticker antes de remover.")
        
    else:
        st.info("Carteira vazia.")

# ==========================================
# 3. GESTOR
# ==========================================
elif modo == "Gestor":
    st.title("⚖️ Otimizador de Carteira")
    carteira = db.listar_carteira()
    if not carteira:
        st.warning("Adicione ativos à carteira primeiro.")
    else:
        if st.button("Gerar Otimização Markowitz"):
            with st.spinner("Otimizando fronteira eficiente..."):
                df_hist = pd.DataFrame()
                tickers = [c['ticker'] for c in carteira]
                
                # Busca histórico em batch
                for t in tickers:
                    d = buscar_dados_ticker_cached(t)
                    if d and 'historico' in d and not d['historico'].empty:
                        df_hist[t] = d['historico']['Close']
                
                res = port_engine.otimizar(df_hist)
                
                if not res or "erro" in res:
                    st.error(res.get('erro', 'Erro desconhecido'))
                else:
                    st.success("Otimização Concluída!")
                    sharpe = res.get('_sharpe_otimizado', 0)
                    retorno = res.get('_retorno_anual', 0)
                    vol = res.get('_volatilidade_anual', 0)

                    col1, col2, col3 = st.columns(3)
                    col1.metric(
                        "Sharpe Otimizado", f"{sharpe:.2f}",
                        help="Retorno ajustado ao risco. Acima de 1.0 é considerado bom."
                    )
                    col2.metric(
                        "Retorno Anual Est.", f"{retorno:.1f}%",
                        help="Retorno anual esperado com base no histórico de 1 ano."
                    )
                    col3.metric(
                        "Volatilidade Anual", f"{vol:.1f}%",
                        help="Desvio padrão anualizado dos retornos da carteira otimizada."
                    )

                    st.subheader("Alocação Sugerida (Máximo Sharpe)")
                    pesos = {k: v for k, v in res.items() if not k.startswith('_')}
                    st.bar_chart(pd.Series(pesos, name="Alocação %"))

# ==========================================
# 4. CONFIG (RESTAURADA v12.1)
# ==========================================
elif modo == "Config":
    st.title("⚙️ Sistema")
    
    st.write("---")
    st.subheader("Zona de Perigo")
    
    # Confirmação em dois passos restaurada
    if st.button("⚠️ RESETAR BANCO DE DADOS", type="primary"):
        st.session_state['reset_confirm'] = True
        
    if st.session_state.get('reset_confirm'):
        st.warning("Tem certeza? Isso apaga TODO o histórico e carteira. Irreversível.")
        c1, c2 = st.columns(2)
        if c1.button("Sim, apagar tudo"):
            db.reset_db()
            st.success("Sistema resetado.")
            st.session_state.clear()
            st.rerun()
        if c2.button("Cancelar"):
            st.session_state['reset_confirm'] = False
            st.rerun()
