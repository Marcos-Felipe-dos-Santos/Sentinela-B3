# Sentinela B3

**Plataforma educacional de análise de ações e FIIs da B3, com dados oficiais da CVM, metodologia transparente e qualidade de dados visível.**

![Python 3.13](https://img.shields.io/badge/Python-3.13-blue)
![pytest](https://img.shields.io/badge/testes-255%20passing-brightgreen)
![Licença MIT](https://img.shields.io/badge/licença-MIT-green)

![Terminal de Análise](docs/screenshot.png)

---

## O que é

O Sentinela B3 é uma aplicação local construída em Python + Streamlit que combina dados oficiais da CVM com metodologias clássicas de valuation (Graham, Bazin, Lynch, Gordon) para apoiar o estudo de ações e FIIs da bolsa brasileira.

O projeto é voltado para investidores individuais e estudantes que querem entender como os indicadores são calculados — com transparência total sobre de onde vêm os dados, qual é a confiança de cada fonte e onde a análise tem limitações.

**Não é** um robô de investimentos, não emite ordens, não constitui consultoria financeira e não recomenda compra ou venda de nenhum ativo.

---

## Funcionalidades principais

- 📊 **Valuation fundamentalista** — Graham, Bazin, Lynch e Gordon com fair value agregado por mediana
- 🏛️ **Dados oficiais da CVM** — DFP/ITR para ações (ROE, margens, dívida, receita) e Informe Mensal para FIIs
- 🔗 **Cascata de fontes resiliente** — CVM → brapi → yfinance → Fundamentus com fallback automático
- 🔍 **Qualidade de dados visível** — badge inline, completude por campo, score de confiança por fonte
- 📡 **Macro context dinâmico** — Selic, CDI, IPCA 12m e yield real NTN-B buscados ao vivo (BCB + Tesouro Direto)
- 📈 **Análise técnica** — RSI, MACD, Bandas de Bollinger, MA50/MA200 com gráfico candlestick interativo
- 🏢 **Engine dedicada para FIIs** — DY isento × Selic líquida (×0,85), P/VP, vacância
- 👥 **Comparação setorial** — P/L, P/VP e DY médios dos peers do mesmo setor
- 🤖 **Veredito IA** — análise em linguagem natural via Groq, Gemini ou Ollama (todos opcionais)
- 💼 **Gestão de carteira** — rastreamento de posições com rentabilidade atualizada

---

## Stack

| Categoria | Tecnologia | Uso |
|-----------|-----------|-----|
| Interface | Streamlit ≥ 1.32 | App web local, dark theme |
| Linguagem | Python 3.13 | Toda a lógica |
| Dados de mercado | yfinance ≥ 0.2.50 | Cotação, histórico OHLC, fundamentos fallback |
| Cotação preferencial | brapi (REST) | Preço e DY para ativos BR |
| Fundamentos oficiais | CVM Dados Abertos | DFP/ITR ZIP (dados.cvm.gov.br) |
| FIIs oficiais | CVM Informe Mensal | Patrimônio líquido e vacância |
| Scraping complementar | Fundamentus | Fallback de múltiplos |
| Macro | BCB SGS API | Selic (série 432), CDI (série 12), IPCA (série 433) |
| Macro | Tesouro Direto JSON | Yield real NTN-B vencimento ≥ 2035 |
| Manipulação de dados | Pandas ≥ 2.2, NumPy | ETL e séries temporais |
| Visualização | Plotly ≥ 5.19 | Candlestick, barras de valuation |
| Persistência | SQLite (WAL mode) | Histórico de análises local |
| IA | Groq / Gemini / Ollama | Veredito em linguagem natural (todos opcionais) |
| Testes | pytest ≥ 8.0 | 255 testes sintéticos, sem rede |

---

## Arquitetura de dados

### Cascata de fontes

```
Ações — fundamentos
  1. CVM Dados Abertos (DFP/ITR)   ← fonte primária, dados auditados
        ROE, margens, receita, dívida, LPA, VPA
  2. brapi                          ← cotação e DY preferencial
        preço_atual, dividendYield, P/L, P/VP
  3. yfinance                       ← fallback geral
        todos os campos quando brapi falha
  4. Fundamentus (scraping)         ← fallback complementar
        múltiplos quando yfinance está incompleto

FIIs — fundamentos
  1. CVM Informe Mensal             ← patrimônio, cotas, tipo de fundo
  2. brapi / yfinance               ← cotação e DY
  3. FII_MANUAL_FALLBACK (config)   ← vacância estimada para fundos sem cobertura

Macro (MacroContext)
  BCB SGS série 432  → Selic anual (cache 24h)
  BCB SGS série 12   → CDI diário → anualizado base 252 (lazy, cache instância)
  BCB SGS série 433  → IPCA mensal → acumulado 12m composto (lazy)
  Tesouro Direto JSON → yield real NTN-B vencimento ≥ 2035 (lazy)
  Hardcoded fallback se qualquer API falhar
```

### Score de confiança por fonte

| Fonte | Score | Dados típicos |
|-------|-------|---------------|
| CVM | 100 | ROE, VPA, LPA, margens, receita, dívida — balanço auditado |
| brapi | 80 | Cotação, DY, P/L, P/VP |
| yfinance | 60 | Fallback geral de mercado |
| Fundamentus | 40 | Fallback de múltiplos via scraping |
| Manual / cache | 20–30 | Estimativas e dados envelhecidos |

O `DataQualityReport` exibe badge inline (🟢 Dados CVM / 🟡 Dados parciais / 🔴 Sem CVM), completude por campo e alertas de consistência (ex.: P/L declarado diverge > 10% de preço/LPA derivado).

---

## Metodologia de valuation

> Todo resultado gerado é educacional. Nenhuma saída constitui recomendação de compra ou venda.

### Graham (valor patrimonial)

Fórmula: `√(22.5 × LPA × VPA)` com piso de P/L em 7× (evita fair value distorcido em cíclicos).
Gates: P/L ≤ 25, P/VP ≤ 3,0 (crescimento) ou ≤ 2,5 (renda), `pl_confiavel=True`.

### Bazin (renda por dividendos)

Fórmula: `(DY × Preço) / max(Selic, 5%)`.
Gate: **DY ≥ 5%** — aplicado apenas a pagadoras consistentes, perfil RENDA.
Taxa mínima usa `max(Selic, 0,05)` para não distorcer em cenários de Selic muito baixa.

### Peter Lynch (crescimento)

Fórmula: `LPA × P/L_justo` onde `P/L_justo = 1,5 × (g × 100)`, cap 35×.
Taxa de crescimento: `g = ROE × (1 − payout)`, cap 25%.
Aplicado apenas a perfil CRESCIMENTO (ROE > 20% e DY < 4%).

### Gordon (fluxo de dividendos descontado)

Fórmula: `Div_próx / (k − g)` onde `k = Selic + 7%` e `g = ROE × retenção`, cap 8%.
Gate: DY > 4%, ROE > 10% e k > g.

### Fair value agregado

`statistics.median(métodos_válidos)`: com 1 método retorna o valor; com 2 retorna a média; com 3 ou mais retorna a **mediana** — não a média aritmética.
Quando os métodos divergem mais de 2× entre si, o risco "Métodos divergentes" é sinalizado e a confiança é penalizada.

### Normalização de DY

Yahoo Finance retorna `dividendYield` de forma inconsistente para ativos brasileiros.
Regra 1: se `DY > 1` → Yahoo retornou como percentual — dividir por 100.
Regra 2: se `DY > 0,25` → dado impossível (> 25%) — descartado como inválido.

### FIIs — engine dedicada

Fórmula: `(Preço × DY_efetivo) / (Selic × 0,85)`.
`DY_efetivo` aplica desconto de vacância quando conhecida para o fundo.
Os limiares de score (bônus/penalidade) usam a Selic líquida (×0,85), não a Selic bruta — porque rendimentos de FII são isentos de IR para pessoa física enquanto renda fixa equivalente paga 15%.

### Decisões metodológicas

**Gate de 5% no Bazin:** aplicá-lo a ações com DY simbólico (1–4%) produziria um "preço justo de renda" para empresas que não são, de fato, pagadoras consistentes — gerando sinais distorcidos.

**Selic líquida no FII (×0,85):** comparar o DY isento do FII com a Selic bruta subestimava o fair value em aproximadamente 17%.

**Mediana no fair value:** Graham avalia patrimônio, Bazin avalia fluxo de dividendos e Gordon avalia crescimento — perspectivas econômicas distintas. Quando divergem expressivamente, a média aritmética produz um número sem interpretação clara. A mediana preserva o valor mais central sem ser distorcida pelos extremos.

**Piso de P/L 7 no Graham:** empresas cíclicas frequentemente apresentam P/L muito baixo no pico do ciclo, o que inflaria artificialmente o LPA ajustado.

**MacroContext como base de cálculo:** todos os parâmetros econômicos (Selic, CDI, IPCA, NTN-B) são buscados ao vivo pelo `MacroContext` em `config.py` e compartilhados por todos os engines via `MACRO` global. Fallbacks hardcoded garantem funcionamento offline.

---

## Instalação

```bash
git clone https://github.com/Marcos-Felipe-dos-Santos/Sentinela-B3.git
cd Sentinela-B3

python -m venv venv

# Windows
venv\Scripts\activate

# Linux / Mac
source venv/bin/activate

pip install -r requirements.txt

# Variáveis de ambiente (todas opcionais — ver seção Configuração)
cp .env.example .env

streamlit run app.py
```

A aplicação abre em `http://localhost:8501`.

---

## Configuração

Todas as chaves são **opcionais**. Sem nenhuma delas, o sistema opera integralmente com fontes abertas (CVM, BCB SGS, yfinance).

| Variável | Uso | Obrigatória? |
|----------|-----|--------------|
| `GROQ_API_KEY` | Veredito IA (Groq — llama-3.3-70b) | Não |
| `GEMINI_API_KEY` | Veredito IA fallback (Gemini 2.0 Flash) | Não |
| `BRAPI_TOKEN` | Aumenta o rate limit da brapi | Não |

Sem chave de IA, a seção "Veredito IA" exibe mensagem informando indisponibilidade mas não bloqueia o valuation.

---

## Testes

```bash
python -m pytest tests/ -v
```

**255 testes** cobrindo, sem tráfego de rede:

| Módulo de teste | O que cobre |
|-----------------|-------------|
| `test_valuation_engine` | Graham, Bazin, Lynch, Gordon, fair value, gates, distressed |
| `test_fii_engine` | Score FII, DY × Selic líquida, P/VP, vacância |
| `test_market_engine` | Cascata de fontes, normalização DY, flags de qualidade |
| `test_cvm_provider` | Download DFP, cálculo de indicadores, cache 7d |
| `test_cvm_fii_provider` | Informe Mensal, cálculo de vacância |
| `test_data_quality` | Completude, score de confiança, badge, validação cruzada |
| `test_macro_context` | Selic, CDI anualizado, IPCA composto, NTN-B, fallbacks |
| `test_technical_engine` | RSI, MACD, Bollinger, tendência |
| `test_peers_engine` | Médias setoriais, filtros de peers |
| `test_backtest_engine` | Backtesting de estratégias por ticker |
| `test_provenance` | FieldProvenance, serialização, prioridade de fonte |

---

## Limitações conhecidas

- **Sem TTM (Trailing Twelve Months):** os dados CVM usam o último DFP anual disponível, não a soma dos últimos 4 ITRs trimestrais — o que pode atrasar indicadores em empresas com sazonalidade forte.
- **Vacância de FIIs:** para fundos sem cobertura na API, a vacância é estimada manualmente em `FII_MANUAL_FALLBACK` — revisar periodicamente.
- **CVM sem mapeamento:** o mapa ticker → CD_CVM (`cvm_ticker_map.py`) cobre os principais ativos; tickers não mapeados caem para brapi/yfinance.
- **Tesouro Direto via JSON:** o endpoint pode retornar 403 dependendo do user-agent; o fallback hardcoded (`NTNB_LONGA_FALLBACK = 7,0%`) é ativado automaticamente.
- **IA opcional:** sem chave de API configurada, o veredito em linguagem natural não é gerado.

---

## Roadmap

| Status | Item |
|--------|------|
| ✅ | Pipeline CVM para fundamentos oficiais (DFP/ITR) |
| ✅ | CVMFIIProvider com Informe Mensal e cálculo de vacância |
| ✅ | MacroContext dinâmico (Selic, CDI, IPCA, NTN-B longa) |
| ✅ | DataQualityReport com completude, score e badge inline |
| ✅ | Correções econômicas: gate Bazin ≥ 5%, Selic líquida no FII, mediana no fair value |
| ✅ | Gráfico de valuation por método com barras horizontais Plotly |
| 🔄 | TTM (Trailing Twelve Months) via soma de ITRs trimestrais |
| 🔄 | NTN-B longa como taxa de desconto no Gordon (em vez de Selic + 7%) |
| 🔄 | Mapeamento CVM especializado para bancos (modelo P/VP justificado) |
| 🔄 | Cobertura automática de todos os tickers via mapa CVM completo |
| 🔄 | Deploy público (Streamlit Community Cloud) |

---

## Aviso legal

Este projeto é **estritamente educacional**. Nenhuma análise, cálculo, recomendação, score ou badge gerado por este sistema constitui consultoria financeira, recomendação de compra ou venda de valores mobiliários, ou qualquer tipo de assessoria de investimento.

Dados de mercado podem estar desatualizados, incompletos ou incorretos. Decisões de investimento devem sempre ser tomadas com o auxílio de um profissional certificado (CFP, CFA ou assessor de investimentos habilitado pela CVM).

---

## Licença

MIT — uso pessoal e educacional.
