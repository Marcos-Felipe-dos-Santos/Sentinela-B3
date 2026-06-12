# 🧠 Sentinela B3

Plataforma pessoal de análise de ativos da bolsa brasileira (**ações e FIIs**) com foco em valuation, análise técnica e suporte à decisão.

> ⚠️ **Projeto educacional e de uso pessoal. Não constitui recomendação de investimento.**

---

## 🚀 Visão Geral

O **Sentinela B3** é uma aplicação construída em Python que integra múltiplas fontes de dados e metodologias de análise para gerar insights sobre ativos da B3.

O projeto foi desenvolvido com foco em:

* aprendizado prático de engenharia de software
* construção de portfólio técnico
* suporte a decisões pessoais de investimento

---

## ✨ Funcionalidades

### 📊 Análise Fundamentalista

* Valuation baseado em:

  * Graham
  * Bazin
  * Gordon
  * Lynch
* Cálculo de Confiança da IA e sinalização de Riscos
* Score automático do ativo
* Classificação (valor, renda ou crescimento)

### 📈 Análise Técnica

* RSI (Índice de Força Relativa)
* MACD (Convergência e Divergência de Médias Móveis)
* Bandas de Bollinger
* Médias móveis (MA50 / MA200)
* Identificação de tendência

### 🏢 FIIs (Fundos Imobiliários)

* Engine dedicada para FIIs
* Avaliação baseada em:

  * Dividend Yield
  * P/VP
  * Ajuste de vacância em FIIs
  * Comparação com a Selic líquida de IR (Selic × 0.85), já que rendimentos de FII são isentos para pessoa física

### 💼 Otimização de Portfólio

* Otimização baseada em Teoria de Markowitz (Máximo Sharpe Ratio)
* Portfólio segmentado ações/FIIs (60/40) automaticamente

### 🤖 IA (Assistente)

* Integração com modelos de IA para gerar análises resumidas
* Fallback automático entre provedores

### 🗄️ Banco de Dados

* Armazenamento local com SQLite
* Histórico de análises
* Ferramentas de auditoria e limpeza

### 📉 Visualização

* Gráficos interativos com Plotly
* Candlestick com médias móveis
* Interface via Streamlit

---

## 🛠️ Stack Tecnológica

* **Python 3.11+**
* **Streamlit** — interface web
* **Pandas / NumPy** — manipulação de dados
* **Plotly** — visualização
* **SQLite** — persistência local
* **yfinance / scraping Fundamentus** — dados de mercado
* **APIs de IA (Gemini / Groq / Ollama)**

---

## 📦 Instalação

```bash
git clone https://github.com/Marcos-Felipe-dos-Santos/Sentinela-B3.git
cd Sentinela-B3

python -m venv venv
.\venv\Scripts\Activate.ps1  # Windows
# source venv/bin/activate  # Linux/Mac

pip install -r requirements.txt
```

---

## ▶️ Execução

```bash
streamlit run app.py
```

---

## 🧪 Estrutura do Projeto

```txt
.
├── app.py                          # Interface Streamlit
├── market_engine.py                # Dados de mercado e cache
├── valuation_engine.py             # Análise de ações
├── fii_engine.py                   # Análise de FIIs
├── technical_engine.py             # Indicadores técnicos
├── portfolio_engine.py             # Otimização de portfólio
├── peers_engine.py                 # Comparação com pares
├── database.py                     # Persistência SQLite
├── ai_core.py                      # Camada de IA
├── config.py                       # Configurações e constantes
├── fundamentus_scraper.py          # Scraper Fundamentus
├── brapi_provider.py               # Provedor Brapi
├── auditar_recomendacoes.py        # Auditoria operacional
├── auditoria.py                    # Diagnóstico legado
├── limpar_banco.py                 # Utilitário de limpeza
├── requirements.txt
├── sentinela/                      # Pacote de domínio
│   ├── domain/                     # Modelos e enums
│   ├── services/                   # Classificador e serviços
│   └── repositories/               # Repositório de análises
├── backtesting/                    # Motor de backtesting
├── tests/                          # Testes automatizados (pytest)
└── docs/                           # Documentação técnica
```

---

## 📐 Metodologia de valuation

> Todo resultado gerado é educacional. Nenhuma saída constitui recomendação de compra ou venda.

### Graham (valor patrimonial)

Fórmula: `√(22.5 × LPA × VPA)` onde LPA = preço / P/L e VPA = preço / P/VP.
Piso de P/L em 7× (evita fair value absurdo em cíclicos com P/L muito baixo).
Gates de aplicação: P/L ≤ 25, P/VP ≤ 3.0 (crescimento) ou ≤ 2.5 (renda), `pl_confiavel=True`.

### Bazin (renda por dividendos)

Fórmula: `(DY × Preço) / max(Selic, 5%)`.
Gate: **DY ≥ 5%** — aplicado apenas a pagadoras consistentes, perfil RENDA.
Taxa mínima usa `max(Selic, 0.05)` para não distorcer em cenários de Selic muito baixa.

### Peter Lynch (crescimento)

Fórmula: `LPA × P/L_justo` onde `P/L_justo = 1.5 × (g × 100)`, cap 35.
Taxa de crescimento: `g = ROE × (1 − payout)`, cap 25%.
Aplicado apenas a perfil CRESCIMENTO (ROE > 20% e DY < 4%).

### Gordon (fluxo de dividendos descontado)

Fórmula: `Div_próx / (k − g)` onde `k = Selic + 7%` e `g = ROE × retenção`, cap 8%.
Gate: DY > 4%, ROE > 10% e k > g.

### Fair value agregado

`statistics.median(métodos_válidos)`: com 1 método retorna o valor; com 2 retorna a média; com 3 ou mais retorna a mediana.
Quando os métodos divergem mais de 2× entre si, o risco "Métodos divergentes" é sinalizado e a confiança é penalizada.

### Normalização de DY

Yahoo Finance retorna `dividendYield` de forma inconsistente para ativos brasileiros.
Regra 1: se `DY > 1` → Yahoo retornou como percentual — dividir por 100.
Regra 2: se `DY > 0.25` → dado impossível (> 25%) — descartado como inválido.

### FIIs — engine dedicada

Fórmula: `(Preço × DY_efetivo) / (Selic × 0.85)`.
`DY_efetivo` aplica desconto de vacância quando conhecida para o fundo.
Os limiares de score (bônus/penalidade) usam igualmente a Selic líquida.

---

### Decisões metodológicas

**Gate de 5% no Bazin**: o modelo de Décio Bazin foi desenvolvido para empresas que distribuem dividendos de forma consistente. Aplicá-lo a ações com DY simbólico (1–4%) produziria um "preço justo de renda" para empresas que não são, de fato, pagadoras — gerando sinais distorcidos.

**Selic líquida no FII (× 0.85)**: rendimentos distribuídos por FIIs são isentos de Imposto de Renda para pessoa física, enquanto a renda fixa equivalente (CDB, Tesouro) sofre tributação de 15% no prazo longo. Comparar o DY isento com a Selic bruta subestimava o fair value do FII em aproximadamente 17%.

**Mediana no fair value**: Graham avalia patrimônio, Bazin avalia fluxo de dividendos e Gordon avalia crescimento futuro — são perspectivas econômicas distintas. Quando divergem expressivamente, a média aritmética produz um número sem interpretação clara. A mediana preserva o valor mais central sem ser distorcida pelos extremos.

**Piso de P/L 7 no Graham**: empresas cíclicas frequentemente apresentam P/L muito baixo no pico do ciclo, o que inflaria artificialmente o LPA ajustado. O piso de 7× ancora o cálculo num mínimo razoável de avaliação de mercado, reduzindo ruído em dados de entrada de baixa qualidade.

---

## ⚠️ Limitações

* Dependência de dados externos (Yahoo Finance / Fundamentus)
* Possíveis inconsistências em scraping
* Não otimizado para alta escala
* Uso estritamente pessoal

---

## 🧪 Testes Automatizados

O projeto conta com uma suíte de **180 testes automatizados** utilizando `pytest` para garantir a estabilidade do sistema contra edge-cases de dados e regras financeiras sem realizar requisições à internet.

```bash
# Executar a suíte de testes
python -m pytest -q
```

Para mais informações, consulte a documentação da suíte de testes em `tests/README.md`.

---

## 📌 Próximos Passos

* [ ] Melhorar cobertura de testes
* [ ] Cache inteligente de dados
* [ ] Deploy em ambiente cloud
* [ ] Dashboard mais avançado
* [x] Backtesting de estratégias

---

## 👨‍💻 Autor

**Marcos Felipe dos Santos**

Projeto desenvolvido como parte de aprendizado em:

* engenharia de software
* análise de dados financeiros
* integração com APIs

---

## ⭐ Destaque para Recrutadores

Este projeto demonstra:

* organização de código em múltiplos módulos
* aplicação de conceitos de valuation financeiro
* integração de APIs externas
* tratamento de erros e edge cases
* uso de IA em aplicações reais
* versionamento com commits estruturados

---

## 📄 Licença

Uso pessoal e educacional.
