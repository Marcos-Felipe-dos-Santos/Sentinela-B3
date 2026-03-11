# 🦅 Sentinela B3

> Sistema inteligente de análise fundamentalista para ações e FIIs da Bolsa Brasileira (B3)

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.32+-FF4B4B.svg)](https://streamlit.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

![Sentinela B3 Screenshot](docs/screenshot-terminal.png)

---

## 📋 Índice

- [Sobre o Projeto](#-sobre-o-projeto)
- [Features](#-features)
- [Instalação](#-instalação)
- [Uso](#-uso)
- [Arquitetura](#-arquitetura)
- [Metodologias de Valuation](#-metodologias-de-valuation)
- [Roadmap](#-roadmap)
- [Contribuindo](#-contribuindo)
- [Licença](#-licença)

---

## 🎯 Sobre o Projeto

**Sentinela B3** é uma plataforma de análise fundamentalista desenvolvida para investidores da Bolsa Brasileira. Combina múltiplas metodologias de valuation (Graham, Bazin, Peter Lynch, Gordon) com análise técnica e inteligência artificial para fornecer recomendações de investimento baseadas em dados.

### Por que Sentinela B3?

- 🔍 **Análise Multi-Metodologia**: Combina 4 metodologias clássicas de valuation
- 🤖 **IA Integrada**: Análise qualitativa com Groq, Gemini ou Ollama
- 📊 **Análise Técnica**: RSI, médias móveis e identificação de tendências
- 🏢 **FIIs e Ações**: Engines especializados para cada tipo de ativo
- ⚡ **Tempo Real**: Dados atualizados via yfinance e Fundamentus
- 📈 **Otimização de Carteira**: Algoritmo Markowitz para alocação eficiente

---

## ✨ Features

### 🔎 Terminal de Análise
- Valuation automático com Graham, Bazin, Lynch e Gordon
- Detecção inteligente de perfil (Crescimento vs Renda/Valor)
- Fair Value e upside potencial
- Score de investimento (0-100)
- Recomendação: COMPRA FORTE / COMPRA / NEUTRO / VENDA
- Análise IA com contexto fundamentalista

### 💼 Gestão de Carteira
- Acompanhamento de rentabilidade em tempo real
- Preço médio e posição atual
- Otimização Markowitz (risco mínimo / máximo Sharpe)

### 🔬 Análise Técnica
- RSI (14 períodos)
- Médias móveis (50 e 200 dias)
- Identificação de tendência e momento

### 🏢 Análise de FIIs
- Engine especializado para Fundos Imobiliários
- Valuation baseado em DY vs Selic
- Classificação Tijolo vs Papel
- P/VP e análise de desconto/prêmio

### 📊 Comparação Setorial
- Benchmarking com peers do mesmo setor
- Médias de P/L, P/VP e DY setoriais
- 10 setores pré-cadastrados (Bancos, Petróleo, Energia, etc.)

---

## 🚀 Instalação

### Pré-requisitos

- Python 3.10 ou superior
- pip (gerenciador de pacotes Python)

### Passo a Passo

1. **Clone o repositório**
```bash
git clone https://github.com/seu-usuario/sentinela-b3.git
cd sentinela-b3
```

2. **Crie um ambiente virtual** (recomendado)
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

3. **Instale as dependências**
```bash
pip install -r requirements.txt
```

4. **Configure as chaves de API** (opcional)

Crie um arquivo `.env` na raiz do projeto:
```env
GROQ_API_KEY=sua_chave_groq_aqui
GEMINI_API_KEY=sua_chave_gemini_aqui
```

> **Nota:** A IA funciona em modo fallback (Ollama local) mesmo sem chaves.

5. **Inicie o aplicativo**
```bash
streamlit run app.py
```

O navegador abrirá automaticamente em `http://localhost:8501`

---

## 📖 Uso

### Analisando um Ativo

1. Acesse o **Terminal de Análise** no menu lateral
2. Digite o ticker (ex: `PETR4`, `HGLG11`, `WEGE3`)
3. Clique em **Analisar**
4. Veja:
   - Fair Value calculado
   - Upside/downside potencial
   - Recomendação de investimento
   - Score de qualidade
   - Análise IA detalhada

### Gerenciando Carteira

1. Acesse **Carteira** no menu
2. Clique em "Adicionar Ativo"
3. Preencha ticker, quantidade e preço médio
4. Acompanhe a rentabilidade em tempo real

### Otimizando Alocação

1. Adicione pelo menos 2 ativos na carteira
2. Acesse **Gestor** no menu
3. Clique em "Gerar Otimização Markowitz"
4. Veja a alocação sugerida para risco mínimo

---

## 🏗️ Arquitetura

```
sentinela-b3/
├── app.py                      # Interface Streamlit principal
├── config.py                   # Configurações e constantes
├── database.py                 # Gerenciamento SQLite
│
├── Engines de Análise:
│   ├── market_engine.py        # Coleta de dados (yfinance + Fundamentus)
│   ├── valuation_engine.py     # Valuation de ações (Graham, Bazin, Lynch, Gordon)
│   ├── fii_engine.py           # Valuation de FIIs
│   ├── technical_engine.py     # Indicadores técnicos (RSI, MAs)
│   ├── peers_engine.py         # Comparação setorial
│   └── portfolio_engine.py     # Otimização Markowitz
│
├── IA e Scrapers:
│   ├── ai_core.py              # Integração Groq/Gemini/Ollama
│   └── fundamentus_scraper.py  # Scraping Fundamentus.com.br
│
├── Utilitários:
│   ├── auditoria.py            # Auditoria completa do sistema
│   └── limpar_banco.py         # Limpeza de análises corrompidas
│
└── requirements.txt            # Dependências Python
```

### Fluxo de Dados

```
Ticker Input (app.py)
    ↓
MarketEngine → yfinance + Fundamentus
    ↓
FII Detection (FIIS_CONHECIDOS + quote_type)
    ↓
    ├─→ FIIEngine (se FII)
    │       ↓
    │   Bazin FII + Score
    │
    └─→ ValuationEngine (se Ação)
            ↓
        Graham + Bazin + Lynch + Gordon
            ↓
        Fair Value + Upside + Recomendação
            ↓
        AI Core (Groq → Gemini → Ollama)
            ↓
        Database (SQLite) + UI (Streamlit)
```

---

## 📊 Metodologias de Valuation

### 🏛️ Graham (Benjamin Graham)
Fórmula clássica baseada em P/L e P/VP:
```
FV = √(22.5 × LPA × VPA)
```
- Aplicado apenas se: P/L ≤ 25 e P/VP ≤ 2.5 (crescimento) ou 3.0 (valor)
- Ignorado se PL negativo ou > 80 (dados não confiáveis)

### 💎 Bazin (Décio Bazin)
Baseado em dividendos sustentáveis:
```
FV = (DY × Preço) / Taxa_Mínima
Taxa_Mínima = Selic × 0.85
```
- Aplicado apenas para ações de renda (DY > 0)

### 🚀 Peter Lynch (PEG Ratio)
Para empresas de crescimento:
```
FV = LPA × Taxa_Crescimento
Taxa_Crescimento = min(ROE × 100, 30%)
```
- Aplicado se: ROE > 20% e DY < 4%

### 📈 Gordon (Dividend Discount Model)
Modelo de desconto de dividendos:
```
FV = Div_Próximo / (k - g)
g = min(ROE × 0.5, 4%)
k = Selic + 6% (prêmio de risco)
```
- Aplicado se: DY > 4% e ROE > 10%

### 🏢 Bazin FII (Fundos Imobiliários)
Adaptação do Bazin para FIIs:
```
FV = (Preço × DY) / Selic
```
- Método principal para todos os FIIs

---

## 🛣️ Roadmap

### ✅ v14 (Atual)
- [x] FII detection via whitelist
- [x] DY sanity cap (>25% → inválido)
- [x] Threading.Lock no scraper
- [x] pl_confiavel tracking
- [x] Banco limpo (sem análises corrompidas)

### 🔄 v15 (Em breve)
- [ ] Cloudscraper deployment (desbloquear Fundamentus)
- [ ] Timeout Gemini (ThreadPoolExecutor wrapper)
- [ ] Retry 429 com backoff exponencial
- [ ] RotatingFileHandler (logs com limite de tamanho)

### 🔮 Futuro
- [ ] Dashboard com gráficos interativos (Plotly)
- [ ] Backtesting de estratégias
- [ ] Alertas de preço-alvo via email/Telegram
- [ ] Export para Excel/PDF
- [ ] API REST para integração externa
- [ ] Análise de balanços (DRE, Fluxo de Caixa)
- [ ] Screener multi-critério

---

## 🧪 Testes e Auditoria

### Executar Auditoria Completa
```bash
python auditoria.py --modo db-only
```

Gera relatório com:
- Status da taxa Selic
- Análises salvas no banco
- Validação de Fair Values
- Detecção de análises corrompidas

### Limpar Banco de Dados
```bash
# Ver o que será removido
python limpar_banco.py --dry-run

# Executar limpeza
python limpar_banco.py
```

Remove automaticamente:
- Análises com upside > 1000%
- Fair Values > 10× preço atual
- FIIs classificados incorretamente
- Units analisadas como FII

---

## 🤝 Contribuindo

Contribuições são bem-vindas! Para contribuir:

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/MinhaFeature`)
3. Commit suas mudanças (`git commit -m 'Adiciona MinhaFeature'`)
4. Push para a branch (`git push origin feature/MinhaFeature`)
5. Abra um Pull Request

### Diretrizes
- Siga PEP 8 para estilo de código Python
- Adicione docstrings em funções públicas
- Teste suas mudanças antes de submeter
- Atualize o README se adicionar features

---

## 📜 Licença

Este projeto está sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.

---

## ⚠️ Disclaimer

**Este software é fornecido "como está", sem garantias de qualquer tipo.**

- ❌ Não é recomendação de investimento
- ❌ Não substitui análise profissional
- ❌ Dados podem conter erros ou estar desatualizados
- ❌ Investimentos têm riscos — você pode perder dinheiro

**Sempre faça sua própria pesquisa (DYOR) e consulte um profissional certificado antes de investir.**

---

## 👨‍💻 Autor

Desenvolvido como projeto pessoal de análise fundamentalista.

---

## 🙏 Agradecimentos

- [yfinance](https://github.com/ranaroussi/yfinance) - Dados de mercado Yahoo Finance
- [Streamlit](https://streamlit.io) - Framework web interativo
- [Fundamentus](https://fundamentus.com.br) - Dados fundamentalistas brasileiros
- [Groq](https://groq.com) - Inferência LLM de alta velocidade

---

<p align="center">
  Feito com 🦅 para investidores da B3
</p>