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
* Score automático do ativo
* Classificação (valor, renda ou crescimento)

### 📈 Análise Técnica

* RSI (Índice de Força Relativa)
* Médias móveis (MA50 / MA200)
* Identificação de tendência

### 🏢 FIIs (Fundos Imobiliários)

* Engine dedicada para FIIs
* Avaliação baseada em:

  * Dividend Yield
  * P/VP
  * Comparação com Selic

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
git clone https://github.com/SEU-USUARIO/Sentinela-B3.git
cd Sentinela-B3

python -m venv venv
venv\Scripts\activate  # Windows
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
├── app.py
├── valuation_engine.py
├── technical_engine.py
├── fii_engine.py
├── market_engine.py
├── database.py
├── ai_core.py
├── fundamentus_scraper.py
├── auditoria.py
├── limpar_banco.py
└── requirements.txt
```

---

## ⚠️ Limitações

* Dependência de dados externos (Yahoo Finance / Fundamentus)
* Possíveis inconsistências em scraping
* Não otimizado para alta escala
* Uso estritamente pessoal

---

## 📌 Próximos Passos

* [ ] Melhorar cobertura de testes
* [ ] Cache inteligente de dados
* [ ] Deploy em ambiente cloud
* [ ] Dashboard mais avançado
* [ ] Backtesting de estratégias

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
