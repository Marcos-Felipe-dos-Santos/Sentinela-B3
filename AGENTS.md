# AGENTS.md — Sentinela B3

> Arquivo de contexto para agentes de IA (OpenAI Codex, Claude Code, Copilot Workspace).
> Coloque este arquivo na raiz do repositório antes de iniciar qualquer sessão.

---

## Visão geral do projeto

**Sentinela B3** é uma plataforma de análise fundamentalista de ações e FIIs da Bolsa Brasileira (B3),
desenvolvida para uso pessoal e portfólio profissional de um estudante de Ciência da Computação.

- **Interface:** Streamlit (`app.py`)
- **Banco de dados:** SQLite local via `database.py` (uso pessoal, não precisa de deploy em cloud)
- **IA:** Fallback chain Groq → Gemini → Ollama (`ai_core.py`)
- **Dados de mercado:** yfinance + Fundamentus scraper (`market_engine.py`, `fundamentus_scraper.py`)
- **Linguagem:** Python 3.10+
- **Versão atual:** v14

---

## Estrutura de arquivos

```
sentinela-b3/
├── app.py                  # Interface Streamlit — 4 abas: Terminal, Carteira, Gestor, Config
├── config.py               # Constantes, SELIC hardcoded, lista de FIIs e Units conhecidos
├── database.py             # SQLite: tabelas analises + carteira
├── ai_core.py              # Integração LLM: Groq (primário) → Gemini → Ollama (fallback)
├── market_engine.py        # Busca dados via yfinance + Fundamentus
├── valuation_engine.py     # 4 métodos: Graham, Bazin, Peter Lynch, Gordon
├── fii_engine.py           # Valuation específico para FIIs (Bazin adaptado)
├── technical_engine.py     # RSI (14 períodos), MA50, MA200
├── portfolio_engine.py     # Otimização Markowitz via scipy.optimize
├── peers_engine.py         # Benchmarking setorial com 10 setores pré-cadastrados
├── fundamentus_scraper.py  # Scraping do Fundamentus.com.br
├── auditoria.py            # Auditoria do banco e validação de Fair Values
├── limpar_banco.py         # Remove análises corrompidas do banco
└── requirements.txt        # Dependências pinadas com ranges de versão
```

---

## Convenções de código obrigatórias

- **Estilo:** PEP 8. Sem exceções.
- **Type hints:** Obrigatório em todas as funções públicas. Usar `Optional[T]`, `List[T]`, `Dict[str, Any]`.
- **Docstrings:** Google style em todas as funções públicas.
- **Logging:** Usar `logger = logging.getLogger(__name__)` — nunca `print()` em módulos.
- **Tratamento de erros:** Nunca deixar exceção genérica sem log. Sempre `logger.warning()` ou `logger.error()` com contexto.
- **Constantes:** Maiúsculas no `config.py`. Nunca hardcoded espalhado pelo código.
- **Nomes em português:** Variáveis de domínio financeiro ficam em português (ex: `preco_atual`, `fair_value`, `upside`). Variáveis de infraestrutura ficam em inglês (ex: `logger`, `cache_key`, `retry_count`).
- **Sem quebrar interfaces existentes:** Qualquer alteração em assinaturas de funções deve manter backward compatibility ou atualizar TODOS os chamadores.

---

## Bugs confirmados para corrigir (por prioridade)

### Bug 1 — CRÍTICO: COMPRA FORTE sobrescreve VENDA sem checar upside
**Arquivo:** `valuation_engine.py`, método `processar()`, seção de recomendação.

**Problema atual:**
```python
rec = "NEUTRO"
if upside > 0.15 or (is_growth and upside > 0.05): rec = "COMPRA"
if upside < -0.15: rec = "VENDA"
if score >= 75: rec = "COMPRA FORTE"  # BUG: sobrescreve VENDA
```

**Comportamento errado:** Uma ação com upside de -20% (cara) mas ROE de 25% (ajuste +10 no score)
pode atingir score 75 e receber COMPRA FORTE mesmo estando cara.

**Correção esperada:**
```python
rec = "NEUTRO"
if upside > 0.15 or (is_growth and upside > 0.05): rec = "COMPRA"
if upside < -0.15: rec = "VENDA"
# COMPRA FORTE só quando há upside real E qualidade alta
if score >= 75 and upside > 0.05: rec = "COMPRA FORTE"
# Reconhecer empresa boa mas cara — não recomendar compra
if score >= 75 and upside <= 0: rec = "QUALIDADE — AGUARDAR"
```

---

### Bug 2 — IMPORTANTE: P/VP não entra no score de FII
**Arquivo:** `fii_engine.py`

**Problema:** O score de FII é baseado exclusivamente no DY vs Selic.
P/VP é o segundo indicador mais importante para FII e está ausente do score.

**Correção esperada:** Após o cálculo do score atual, adicionar:
```python
pvp = float(dados.get('pvp', 1.0) or 1.0)
if pvp > 1.15: score -= 15   # pagando prêmio excessivo sobre o patrimônio
elif pvp > 1.05: score -= 7  # prêmio moderado
elif pvp < 0.85: score += 10 # desconto relevante = margem de segurança
score = max(0, min(100, score))
```

---

### Bug 3 — IMPORTANTE: Lynch não desconta payout ratio
**Arquivo:** `valuation_engine.py`, seção Lynch.

**Problema atual:**
```python
taxa_crescimento = min(roe * 100, 30)
metodos['Lynch'] = lpa * taxa_crescimento
```
Usa ROE como proxy de crescimento, assumindo payout = 0% (100% de retenção). Superestima FV.

**Correção esperada:**
```python
# Taxa de crescimento sustentável real = ROE × retenção
payout_ratio = min((dy * p) / lpa, 0.95) if lpa > 0 else 0.5
retencao = 1 - payout_ratio
g_real = min(roe * retencao * 100, 30)
metodos['Lynch'] = lpa * g_real
```

---

### Bug 4 — MODERADO: Selic hardcoded em config.py
**Arquivo:** `config.py` e `valuation_engine.py`

**Problema:** Selic definida como constante. Afeta Bazin (taxa_minima) e Gordon (k = Selic + 0.06).
Se a Selic mudar, todos os Fair Values ficam errados silenciosamente.

**Correção esperada:** Criar função em `config.py`:
```python
import requests
import streamlit as st

@st.cache_data(ttl=86400)  # cache de 24 horas
def get_selic_atual() -> float:
    """Busca a Selic diária atual via API do Banco Central do Brasil."""
    try:
        url = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados/ultimos/1?formato=json"
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        valor_diario = float(resp.json()[0]['valor'])
        selic_anual = (1 + valor_diario / 100) ** 252 - 1
        logger.info(f"Selic atual: {selic_anual:.4f} ({selic_anual*100:.2f}% a.a.)")
        return selic_anual
    except Exception as e:
        logger.warning(f"Falha ao buscar Selic do BCB: {e}. Usando fallback hardcoded.")
        return SELIC_FALLBACK  # constante de segurança em config.py
```

---

## Melhorias de qualidade (sem alterar lógica financeira)

### Cache de dados de mercado
**Arquivo:** `app.py` e `market_engine.py`

O método `buscar_dados_ticker()` é chamado sem cache. Na aba Carteira, cada reload
faz N chamadas ao yfinance (uma por ativo). Adicionar cache:

```python
@st.cache_data(ttl=300)  # 5 minutos
def buscar_dados_ticker_cached(ticker: str) -> dict:
    return market.buscar_dados_ticker(ticker)
```

### Gráfico Candlestick com Plotly
**Arquivo:** `app.py`, aba "Gráfico" no Terminal.

O `st.line_chart(hist['Close'])` deve ser substituído por:
```python
import plotly.graph_objects as go

fig = go.Figure(data=[
    go.Candlestick(x=hist.index, open=hist['Open'], high=hist['High'],
                   low=hist['Low'], close=hist['Close'], name='OHLC'),
    go.Scatter(x=hist.index, y=hist['Close'].rolling(50).mean(),
               line=dict(color='orange', width=1), name='MA50'),
    go.Scatter(x=hist.index, y=hist['Close'].rolling(200).mean(),
               line=dict(color='blue', width=1), name='MA200'),
])
fig.update_layout(xaxis_rangeslider_visible=False, height=400)
st.plotly_chart(fig, use_container_width=True)
```

### Timeout no Gemini (ai_core.py)
Adicionar timeout via `concurrent.futures.ThreadPoolExecutor`:
```python
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout

with ThreadPoolExecutor(max_workers=1) as executor:
    future = executor.submit(
        self.clients['gemini'].models.generate_content,
        model=GEMINI_MODEL, contents=prompt
    )
    try:
        resp = future.result(timeout=15)
        return {"content": resp.text, "model": "Gemini"}
    except FuturesTimeout:
        logger.warning("Gemini timeout (15s). Falling back to Ollama.")
```

---

## Testes a criar

Criar arquivo `tests/test_valuation_engine.py` com os seguintes casos:

1. `test_dy_normalization_percentual()` — DY de 12.47 deve virar 0.1247
2. `test_dy_invalido_acima_25pct()` — DY de 0.45 deve ser zerado e `dy_confiavel = False`
3. `test_recomendacao_compra_forte_exige_upside()` — score 80 + upside -0.20 NÃO deve retornar COMPRA FORTE
4. `test_recomendacao_qualidade_aguardar()` — score 80 + upside -0.10 deve retornar "QUALIDADE — AGUARDAR"
5. `test_graham_ignorado_pl_negativo()` — pl_confiavel=False deve excluir Graham dos metodos_usados
6. `test_lynch_desconta_payout()` — empresa com ROE 25% e payout 40% deve ter g_real ≈ 15%, não 25%
7. `test_fii_score_penaliza_pvp_alto()` — FII com P/VP 1.2 deve ter score menor que FII com P/VP 0.95

---

## O que NÃO alterar

- Estrutura do SQLite e `database.py` — uso pessoal local, não precisa migrar para cloud
- Lógica de detecção de FII (whitelist + fallback de sufixo) — está funcionando corretamente
- Fallback chain Groq → Gemini → Ollama — estrutura correta, só adicionar timeout no Gemini
- Arquivos `auditoria.py` e `limpar_banco.py` — ferramentas de manutenção ok
- `requirements.txt` — dependências já pinadas com ranges corretos

---

## Contexto financeiro (para o agente entender o domínio)

- **LPA** = Lucro Por Ação = `preço / P/L`
- **VPA** = Valor Patrimonial Por Ação = `preço / P/VP`
- **DY** = Dividend Yield = dividendos anuais / preço (retornado como decimal pelo yfinance após normalização)
- **ROE** = Return on Equity = lucro líquido / patrimônio líquido (retornado como decimal)
- **Selic** = taxa básica de juros brasileira, benchmark de risco-zero no Brasil
- **P/VP** = Preço / Valor Patrimonial — para FIIs, o indicador mais importante junto com DY
- **Upside** = (Fair Value / Preço atual) - 1, em decimal
- **FII** = Fundo de Investimento Imobiliário — ativo similar a REIT americano
- **Unit** = ação composta (ex: ITSA4) — não é FII, não usar engine de FII
- **Perfil CRESCIMENTO**: ROE > 20% AND DY < 4% — usar Lynch
- **Perfil RENDA/VALOR**: tudo o mais — usar Bazin e Gordon

---

## Prioridade de execução para o agente

1. Bug 1 (COMPRA FORTE sobrescrevendo VENDA) — `valuation_engine.py`
2. Bug 2 (P/VP no score de FII) — `fii_engine.py`
3. Bug 3 (Lynch sem payout) — `valuation_engine.py`
4. Bug 4 (Selic dinâmica) — `config.py` + todos os chamadores de `get_selic_atual()`
5. Cache de dados de mercado — `app.py`
6. Candlestick Plotly — `app.py`
7. Timeout Gemini — `ai_core.py`
8. Testes pytest — criar `tests/test_valuation_engine.py`

**Regra:** Executar nessa ordem. Não pular etapas. Commitar separadamente por bug/feature.
