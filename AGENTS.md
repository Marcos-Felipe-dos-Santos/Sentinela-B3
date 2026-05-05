# Seção 1 — Visão geral do projeto

Sentinela B3 é uma aplicação pessoal e educacional de análise de ativos da bolsa brasileira, cobrindo ações e FIIs. O README descreve o foco em valuation, análise técnica e suporte à decisão, com aviso explícito de que não constitui recomendação de investimento.

A interface é Streamlit em `app.py`, com quatro modos no menu lateral: Terminal, Carteira, Gestor e Config. A página usa `APP_VERSION` de `config.py` em `app.py:17`. O README não declara uma versão numérica; ele descreve o projeto como Sentinela B3 e lista a stack.

Stack técnica lida no código e no README: Python, Streamlit, SQLite, pandas, numpy, scipy, Plotly, yfinance, requests, BeautifulSoup, python-dotenv, Groq, Gemini e Ollama. A persistência local fica em SQLite via `database.py`; preço e histórico vêm preferencialmente do yfinance via `market_engine.py`; fundamentos vêm preferencialmente da Brapi quando `BRAPI_TOKEN` está disponível; Fundamentus é fallback/complemento; cache de fundamentos válidos fica em SQLite. Valuation de ações fica em `valuation_engine.py`; valuation de FIIs fica em `fii_engine.py`; técnica fica em `technical_engine.py`; otimização de carteira em `portfolio_engine.py`; comparação setorial em `peers_engine.py`; IA em `ai_core.py`; auditoria operacional atual em `auditar_recomendacoes.py`. `auditoria.py` permanece como diagnóstico legado/profundo.

Arquivos principais:

- `app.py`: interface Streamlit, roteamento entre ações/FIIs via `AssetClassifier`, cache curto de dados, renderização de valuation, IA, técnica, peers, gráfico e carteira.
- `config.py`: modelos de IA, parâmetros globais, listas de FIIs e Units conhecidas, tickers distressed, Selic dinâmica com cache manual.
- `market_engine.py`: consolida preço/histórico do yfinance, fundamentos preferenciais da Brapi, fallback Fundamentus, fallback manual de FIIs, cache de fundamentos e classificação FII/Unit via `AssetClassifier`.
- `sentinela/services/asset_classifier.py`: classificador central de ações, FIIs e Units; preserva `FIIS_CONHECIDOS`, `UNITS_CONHECIDAS` e a regra de segurança de que Unit conhecida não deve virar FII mesmo com `quote_type == "MUTUALFUND"`.
- `valuation_engine.py`: calcula fair value de ações por Graham, Bazin, Lynch e Gordon, score, riscos, confiança e recomendação.
- `fii_engine.py`: calcula fair value de FIIs via Bazin adaptado com DY, Selic, P/VP e vacância conhecida.
- `database.py`: cria e acessa tabelas `analises` e `carteira_real` no SQLite local.
- `ai_core.py`: fallback de IA Groq -> Gemini -> Ollama.
- `data_quality.py`: valida qualidade de dados para revisão manual/backtesting, com score, alertas e recomendação de uso.
- `auditar_recomendacoes.py`: script operacional atual de auditoria de recomendações; mede qualidade/falha geral e falha operacional sem penalizar tickers fora do universo analisável.
- `auditoria.py`: script legado de diagnóstico profundo que consulta Selic, banco, scraper, valuation, técnica, prompt e referência do Fundamentus; usar apenas quando a tarefa pedir diagnóstico detalhado ou comparação histórica.

# Seção 2 — Arquitetura e fluxo de dados

No modo Terminal, o usuário digita um ticker em `app.py` e, ao clicar em Analisar, a UI chama `MarketEngine.buscar_dados_ticker()` diretamente. O helper `buscar_dados_ticker_cached()` segue disponível com cache curto de 300 segundos e é usado em fluxos como Carteira/Gestor para reduzir chamadas externas repetidas.

O `MarketEngine` normaliza o ticker e monta um dicionário com flags de fonte e qualidade: `fonte_preco`, `fonte_fundamentos`, `erro_scraper`, `dados_parciais`, `campos_faltantes`, `dados_cache`, `dados_manual` e `riscos_dados`. Primeiro tenta yfinance em `_buscar_yfinance()` para preço, histórico de 1 ano e fundamentos parciais de fallback. Depois tenta Brapi em `_buscar_brapi()`, que é a fonte preferencial de fundamentos e pode sobrescrever fundamentos parciais do yfinance. Fundamentus entra em `_buscar_fundamentus()` apenas como fallback/complemento quando Brapi está indisponível ou incompleta. Se ainda faltarem fundamentos obrigatórios, o engine tenta `fundamentals_cache` em SQLite e, para FIIs conhecidos, fallback manual controlado.

O `FundamentusScraper` monta uma sessão com cloudscraper quando disponível, ou `requests.Session` como fallback. Ele limita requisições com lock e intervalo mínimo, baixa a página `detalhes.php?papel={ticker}`, extrai pares de tabela, limpa números brasileiros em `_limpar_valor()` e converte percentuais para decimal.

Depois de coletar dados, `app.py` decide se o ticker é FII por meio de `AssetClassifier.is_fii(ticker, dados)`. A regra central preserva `FIIS_CONHECIDOS`, `UNITS_CONHECIDAS`, `quote_type == "MUTUALFUND"` e fallback por sufixo `11`, mantendo a invariante de segurança de que Units conhecidas como `SANB11`, `TAEE11` e `KLBN11` não devem seguir para `FIIEngine`. FIIs seguem para `FIIEngine.analisar()`; ações seguem para `ValuationEngine.processar()` e para `PeersEngine.comparar()`.

Para ações, `ValuationEngine` normaliza DY, calcula LPA/VPA, consulta `get_selic_atual()`, classifica perfil crescimento versus renda/valor, aplica os métodos disponíveis, calcula média simples dos valores válidos, score sigmoid ajustado por qualidade, riscos, confiança e recomendação. Para FIIs, `FIIEngine` normaliza DY, ajusta por vacância conhecida, usa Selic para preço justo, ajusta score por DY versus Selic e P/VP, e define compra/venda por upside.

O `TechnicalEngine` calcula RSI, médias móveis, MACD, bandas de Bollinger, momento e tendência a partir do histórico. O `PeersEngine` busca peers setoriais com `ThreadPoolExecutor`, calcula médias de P/L, P/VP e DY e devolve o setor e peers utilizados. O `SentinelaAI` formata o dicionário de dados sem campos volumosos, gera um prompt e tenta Groq, Gemini com timeout de 15 segundos, e Ollama local.

Por fim, `app.py` mescla `dados.update(analise)`, adiciona técnica e resposta de IA, remove `historico` antes de persistir e chama `DatabaseManager.salvar_analise()`. A UI mostra métricas principais, expander de Qualidade dos Dados, abas de Valuation & IA, Técnica & Peers e Gráfico. A aba Carteira lê `database.py`, atualiza preços com cache curto e calcula valor atual e rentabilidade. A aba Gestor monta históricos de carteira e chama `PortfolioEngine.otimizar()`.

# Seção 3 — Convenções obrigatórias

Convenções observadas no projeto:

- Variáveis de domínio financeiro usam português ou termos financeiros já estabelecidos: `preco_atual`, `fair_value`, `upside`, `dy`, `roe`, `pl`, `pvp`, `carteira`, `rentabilidade`, `retencao`, `confianca`, `riscos`.
- Variáveis de infraestrutura costumam usar inglês: `logger`, `clients`, `future`, `executor`, `timeout`, `cache`, `session`.
- Módulos principais usam `logger = logging.getLogger(...)`; exemplos: `config.py:18`, `valuation_engine.py:5`, `fii_engine.py:4`, `market_engine.py:9`, `ai_core.py:11`, `database.py:7`, `peers_engine.py:4`, `fundamentus_scraper.py:8`.
- Tratamento de erro externo registra contexto com `logger.warning()` ou `logger.error()` em engines e integrações; exemplos: yfinance em `market_engine.py:126`, Brapi em `market_engine.py:194`, Gemini em `ai_core.py:88`, Ollama em `ai_core.py:106`, banco em `database.py:102`, Fundamentus em `fundamentus_scraper.py:191`.
- Funções públicas novas devem manter type hints e docstrings quando possível; o código atual é inconsistente, mas há exemplos já tipados em `market_engine.py:18`, `fii_engine.py:11`, `peers_engine.py:30`, `config.py:77`, `app.py:53`.
- Não quebrar assinaturas existentes sem atualizar chamadores; `app.py` instancia e chama diretamente todos os engines.
- Dados externos são tratados como não confiáveis: há flags `erro_scraper`, `dados_parciais`, `pl_confiavel`, `dy_confiavel`, `confianca` e `riscos`.
- Evitar persistir objetos pesados no banco; `app.py:122` remove `historico` antes de salvar.
- Manter compatibilidade local e pessoal: SQLite em arquivo, Streamlit local e fallback local via Ollama.

# Seção 4 — Mapa de dependências entre arquivos

- `config.py`
  - Importa: `logging` (`config.py:1`), `os` (`config.py:2`), `time` (`config.py:3`), `requests` (`config.py:5`), `dotenv.load_dotenv` (`config.py:6`).
  - É importado por: `ai_core.py`, `app.py`, `auditoria.py`, `fii_engine.py`, `limpar_banco.py`, `market_engine.py`, `portfolio_engine.py`, `valuation_engine.py` e pelo `AssetClassifier`. `FIIS_CONHECIDOS` e `UNITS_CONHECIDAS` devem ser consumidos pelo classificador central, não por novas regras duplicadas.

- `valuation_engine.py`
  - Importa: `logging`, `math`, `get_selic_atual` e `DISTRESSED_TICKERS` de `config`, além de `DataQualityValidator` de `data_quality`.
  - É importado por: `app.py`, `auditar_recomendacoes.py` e testes.

- `fii_engine.py`
  - Importa: `logging` (`fii_engine.py:1`), `get_selic_atual` de `config` (`fii_engine.py:2`).
  - É importado por: `app.py:10`, `auditar_recomendacoes.py:22`, `auditoria.py:859`.

- `market_engine.py`
  - Importa: `logging`, `math`, `Any`, `Dict`, `Optional`, `yfinance`, `pandas`, `BrapiProvider`, `FII_MANUAL_FALLBACK` de `config`, `DatabaseManager`, `FundamentusScraper` e `AssetClassifier`.
  - É importado por: `app.py`, `auditar_recomendacoes.py`, `auditoria.py` e testes.

- `brapi_provider.py`
  - Importa: `logging`, `os`, `Any`, `Dict`, `Optional` e `requests`.
  - É importado por: `market_engine.py` e testes de provider.

- `app.py`
  - Importa: `time`, `Any`, `Dict`, `Optional`, `pandas`, `plotly.graph_objects`, `streamlit`, `DatabaseManager`, `MarketEngine`, `ValuationEngine`, `FIIEngine`, `TechnicalEngine`, `PortfolioEngine`, `PeersEngine`, `SentinelaAI`, `APP_VERSION` e `AssetClassifier`.
  - É importado por: nenhum arquivo encontrado por busca textual.

- `ai_core.py`
  - Importa: `ThreadPoolExecutor` e `FuturesTimeout` (`ai_core.py:1`), `logging` (`ai_core.py:2`), `os` (`ai_core.py:3`), `requests` (`ai_core.py:5`), constantes de `config` (`ai_core.py:7`), `google.genai` dinamicamente (`ai_core.py:23`), `Groq` dinamicamente (`ai_core.py:33`).
  - É importado por: `app.py:14`.

- `database.py`
  - Importa: `sqlite3`, `json`, `logging`, `datetime`, `timedelta`, `closing` e `os` dentro de `reset_db()`.
  - Cria/acessa `analises`, `carteira_real` e `fundamentals_cache`.
  - É importado por: `app.py`, `market_engine.py` e utilitários locais.

- `technical_engine.py`
  - Importa: `pandas` (`technical_engine.py:1`), `numpy` (`technical_engine.py:2`).
  - É importado por: `app.py:11`, `auditar_recomendacoes.py:23`.

- `data_quality.py`
  - Importa: `logging`, `datetime` e `Dict`.
  - É importado por: `valuation_engine.py` e testes.

- `portfolio_engine.py`
  - Importa: `numpy`, `pandas`, `minimize` de `scipy.optimize`, `get_selic_atual` de `config` e `AssetClassifier`.
  - É importado por: `app.py:12`.

- `peers_engine.py`
  - Importa: `logging` (`peers_engine.py:1`), `ThreadPoolExecutor` e `as_completed` (`peers_engine.py:2`), `MAX_WORKERS` de `config` (`peers_engine.py:4`).
  - É importado por: `app.py:13`.

- `fundamentus_scraper.py`
  - Importa: `logging` (`fundamentus_scraper.py:1`), `threading` (`fundamentus_scraper.py:2`), `time` (`fundamentus_scraper.py:3`), `requests` (`fundamentus_scraper.py:5`), `BeautifulSoup` (`fundamentus_scraper.py:6`), `cloudscraper` opcional (`fundamentus_scraper.py:14`).
  - É importado por: `market_engine.py:6`.

- `auditar_recomendacoes.py`
  - Importa: `logging`, `os`, `sys`, `datetime`, `StringIO`, tipagens, `pandas`, `MarketEngine`, `ValuationEngine`, `FIIEngine`, `TechnicalEngine` e `AssetClassifier`.
  - É o script operacional atual de auditoria de recomendações e qualidade de dados.

- `auditoria.py`
  - Importa: `sys` (`auditoria.py:18`), `os` (`auditoria.py:19`), `re` (`auditoria.py:20`), `io` (`auditoria.py:21`), `json` (`auditoria.py:22`), `math` (`auditoria.py:23`), `sqlite3` (`auditoria.py:24`), `datetime` (`auditoria.py:25`), `requests` dentro da auditoria Selic (`auditoria.py:78`), `MarketEngine` (`auditoria.py:145`), `numpy` (`auditoria.py:220` e `auditoria.py:527`), `get_selic_atual` (`auditoria.py:252`), `APP_VERSION` (`auditoria.py:820`), `FIIS_CONHECIDOS` e `UNITS_CONHECIDAS` (`auditoria.py:859`), `FIIEngine` (`auditoria.py:878`).
  - É importado por: nenhum arquivo encontrado por busca textual.
  - Status: legado/diagnóstico profundo; não é o script operacional padrão.

- `requirements.txt`
  - Importa: não se aplica.
  - É importado por: não se aplica.

- `README.md`
  - Importa: não se aplica.
  - É importado por: não se aplica.

# Seção 5 — Histórico arquivado de bugs resolvidos

Esta seção registra problemas já corrigidos em fases anteriores. Ela não é uma lista de trabalho pendente, e os trechos marcados como código antigo são evidências históricas do estado pré-correção. Não use esta seção para reabrir alterações sem antes verificar o código e os testes atuais.

**[RESOLVIDO — Fase 2] Bug 1 — Recomendação de venda depende indevidamente de técnico negativo**

Arquivo: `valuation_engine.py`, linhas 195-210.

Código antigo (pré-correção):

```python
rec = "NEUTRO"
tecnico_negativo = dados.get('tecnico_negativo', False)
if tecnico_negativo:
    riscos.append("Técnico negativo")
    confianca -= 10

if upside > 0.15 and score >= 60 and confianca >= 50:
    rec = "COMPRA"
    if score >= 75 and confianca >= 70:
        rec = "COMPRA FORTE"
elif score >= 75 and upside <= 0:
    rec = "QUALIDADE — AGUARDAR"
elif upside < -0.15 and tecnico_negativo:
    rec = "VENDA"
else:
    rec = "NEUTRO"
```

Descrição: `VENDA` só é emitida quando `upside < -0.15` e `tecnico_negativo` é verdadeiro. Como o código lido não define `tecnico_negativo` em `app.py` nem em `technical_engine.py`, um ativo caro por valuation pode ficar `NEUTRO` se esse campo não chegar no dicionário.

**[RESOLVIDO — Fase 2] Bug 2 — Auditoria usa fórmula de Bazin diferente da produção**

Arquivo de produção: `valuation_engine.py`, linhas 106-111.

Código antigo da produção (pré-correção):

```python
if not is_growth and dy > 0 and dy_confiavel:
    if dy > 0.15:
        riscos.append("DY muito alto (possível armadilha)")
        confianca -= 10
    taxa_minima = max(selic, 0.05)
    metodos['Bazin'] = (dy * p) / taxa_minima
```

Arquivo de auditoria: `auditoria.py`, linhas 365-369.

Código antigo da auditoria (pré-correção):

```python
else:
    taxa_b = selic * 0.85
    b_val  = (dy * p) / taxa_b
    div_anual = dy * p
    metodos['Bazin'] = b_val
```

Descrição: o relatório de auditoria calcula Bazin com `selic * 0.85`, mas a engine de produção usa `max(selic, 0.05)`. Isso faz a auditoria validar valores diferentes dos exibidos pelo app.

**[RESOLVIDO — Fase 2] Bug 3 — Auditoria usa fórmula de Lynch diferente da produção**

Arquivo de produção: `valuation_engine.py`, linhas 115-122.

Código antigo da produção (pré-correção):

```python
if is_growth and pl > 0 and dy_confiavel and lpa > 0 and roe > 0:
    payout_ratio = min((dy * p) / lpa, 0.95)
    retencao = 1 - payout_ratio
    g = roe * retencao
    g = min(g, 0.25)
    pl_justo = 1.5 * (g * 100)
    pl_justo = min(pl_justo, 35)
    metodos['Lynch'] = lpa * pl_justo
```

Arquivo de auditoria: `auditoria.py`, linhas 397-402.

Código antigo da auditoria (pré-correção):

```python
lpa_l = p / pl
payout_ratio = min((dy * p) / lpa_l, 0.95) if lpa_l > 0 else 0.5
retencao = 1 - payout_ratio
taxa_l = min(roe * retencao * 100, 30)
l_val = lpa_l * taxa_l
metodos['Lynch'] = l_val
```

Descrição: produção aplica multiplicador `1.5 * crescimento` com teto de P/L justo em 35, enquanto auditoria usa `lpa * taxa_l` com teto de 30. O script de auditoria pode aprovar ou reprovar fair values que não correspondem ao app.

**[RESOLVIDO — Fase 2] Bug 4 — Auditoria usa fórmula de Gordon diferente da produção**

Arquivo de produção: `valuation_engine.py`, linhas 126-134.

Código antigo da produção (pré-correção):

```python
if dy_confiavel and dy > 0.04 and roe > 0.10:
    payout_ratio_g = min((dy * p) / lpa, 0.95) if lpa > 0 else 0.5
    retencao_g = 1 - payout_ratio_g
    g = roe * retencao_g
    g = min(g, 0.08)
    k = selic + 0.04
    if k > g:
        div_prox = (dy * p) * (1 + g)
        metodos['Gordon'] = div_prox / (k - g)
```

Arquivo de auditoria: `auditoria.py`, linhas 431-440.

Código antigo da auditoria (pré-correção):

```python
g_cr  = min(roe * 0.5, 0.04)
k_cr  = selic + 0.06
if k_cr <= g_cr:
    r = "k <= g: modelo instável — IGNORADO"
    print(f"  {err(r)}")
    metodos_log['Gordon'] = {"status": "IGNORADO", "motivo": r}
else:
    div_prox = (dy * p) * (1 + g_cr)
    go_val   = div_prox / (k_cr - g_cr)
    metodos['Gordon'] = go_val
```

Descrição: produção usa retenção calculada por payout, teto de crescimento de 8% e `k = selic + 0.04`; auditoria usa `roe * 0.5`, teto de 4% e `k = selic + 0.06`.

**[RESOLVIDO — Fase 2] Bug 5 — Auditoria roteia FIIs diferente do app**

Arquivo de produção: `app.py`, linhas 85-95.

Código antigo da produção (pré-correção):

```python
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
```

Arquivo de auditoria: `auditoria.py`, linhas 847-852.

Código antigo da auditoria (pré-correção):

```python
# Roteamento FII vs Ação — idêntico ao app.py
qt = dados.get('quote_type', '')
is_fii = (
    qt == 'MUTUALFUND'
    or (not qt and '11' in ticker and 'SA' not in ticker)
)
```

Descrição: o comentário diz que o roteamento é idêntico ao app, mas a auditoria não usa `FIIS_CONHECIDOS` nem exclui `UNITS_CONHECIDAS`. Units como `SANB11` ou `TAEE11` podem ser roteadas de forma diferente na auditoria e no app.

**[RESOLVIDO — Fase 2] Bug 6 — Otimizador classifica FIIs apenas por sufixo 11**

Arquivo: `portfolio_engine.py`, linhas 57-65.

Código antigo (pré-correção):

```python
try:
    fiis = [c for c in df.columns if c.endswith('11')]
    stocks = [c for c in df.columns if not c.endswith('11')]

    if fiis and stocks:
        pesos_fiis = otimizar_grupo(fiis)
        pesos_stocks = otimizar_grupo(stocks)
        resultado = {col: round(p * 40, 1) for col, p in pesos_fiis.items()}
        resultado.update({col: round(p * 60, 1) for col, p in pesos_stocks.items()})
```

Descrição: `config.py:55-58` mantém uma lista de Units conhecidas com sufixo `11` que não são FIIs. O otimizador ignora essa lista e pode tratar Units como FIIs na alocação 40/60.

# Seção 6 — Histórico arquivado de melhorias

Esta seção registra melhorias já implementadas ou levantadas em ciclos anteriores. O roadmap ativo está na Seção 8; não trate os itens abaixo como ordem de execução atual.

**[IMPLEMENTADO — Fase 2] Melhoria 1 — Tornar o gráfico responsivo à largura do container**

Arquivo: `app.py`, linha 189.

Código antigo (pré-implementação):

```python
st.plotly_chart(fig)
```

O que deve mudar e por quê: usar `st.plotly_chart(fig, use_container_width=True)` para manter o gráfico Candlestick consistente com layout wide e colunas responsivas do Streamlit.

**[IMPLEMENTADO — Fase 2] Melhoria 2 — Alinhar metadados de versão**

Arquivo: `app.py`, linha 17.

Código antigo (pré-implementação):

```python
st.set_page_config(page_title="Sentinela B3 v12.1", layout="wide", page_icon="🦅")
```

Arquivo: `auditoria.py`, linhas 811-814.

Código antigo (pré-implementação):

```python
_rel['meta'] = {
    "timestamp":  datetime.now().isoformat(),
    "versao":     "Sentinela B3 v13",
    "db_path":    DB_PATH,
```

O que deve mudar e por quê: centralizar a versão ou atualizar os metadados para evitar que UI e auditoria reportem versões diferentes. O README não traz versão numérica.

**[IMPLEMENTADO — Fase 2] Melhoria 3 — Fechar executor do Gemini de forma explícita**

Arquivo: `ai_core.py`, linhas 13-17.

Código antigo (pré-implementação):

```python
class SentinelaAI:
    def __init__(self):
        self.clients = {}
        self._gemini_executor = ThreadPoolExecutor(max_workers=1)
        self._setup()
```

O que deve mudar e por quê: adicionar método de encerramento ou gerenciamento explícito do executor para evitar thread persistente em ciclos longos do Streamlit. Verificar a melhor integração com `st.cache_resource` antes de alterar.

**[IMPLEMENTADO — Fase 2] Melhoria 4 — Completar type hints/docstrings em métodos públicos**

Arquivo: `database.py`, linhas 48-85.

Código antigo (pré-implementação):

```python
def adicionar_posicao(self, ticker, qtd, preco):
```

```python
def listar_carteira(self):
```

```python
def salvar_analise(self, dados):
```

O que deve mudar e por quê: métodos públicos ainda não têm type hints nem docstrings, embora o projeto já use hints em partes novas. Padronizar isso reduz ambiguidade de chamadas de `app.py`.

**Melhoria 5 — Evitar uma chamada externa por peer sem cache no comparador**

Arquivo: `peers_engine.py`, linhas 44-46.

Código antigo (pré-implementação):

```python
with ThreadPoolExecutor(max_workers=4) as executor:
    futures = {executor.submit(self.market.buscar_dados_ticker, p): p
               for p in target_peers}
```

O que deve mudar e por quê: `app.py` usa `buscar_dados_ticker_cached()`, mas `PeersEngine` chama `self.market.buscar_dados_ticker` diretamente. Isso pode repetir yfinance/Fundamentus fora do cache do app. Verificar uma estratégia de cache no engine ou injeção de função cached.

**[IMPLEMENTADO — Fase 3] Melhoria 6 — Remover ativo da carteira**

Arquivo: `database.py`, linha 87; `app.py`, linha 246.

Implementado: `DatabaseManager.remover_posicao()` remove uma posição pelo ticker e a aba Carteira expõe um expander com `remover_ticker` e `btn_remover`.

**[IMPLEMENTADO — Fase 3] Melhoria 7 — Métricas da otimização Markowitz**

Arquivo: `portfolio_engine.py`, linhas 39-60; `app.py`, linhas 291-309.

Implementado: `PortfolioEngine.otimizar()` retorna `_sharpe_otimizado`, `_retorno_anual` e `_volatilidade_anual`; o Gestor exibe as três métricas e filtra metadados antes do gráfico.

**[IMPLEMENTADO — Fase 3] Melhoria 8 — ATR na análise técnica**

Arquivo: `technical_engine.py`, linhas 12, 62-73 e 102.

Implementado: `TechnicalEngine.calcular_indicadores()` retorna `atr` no fallback e no cálculo normal, usando `High`, `Low` e `Close` quando disponíveis.

**[IMPLEMENTADO — Fase 3] Melhoria 9 — Limpezas de configuração e paralelismo**

Arquivo: `config.py`, linhas 42, 50 e 110; `peers_engine.py`, linhas 4 e 46.

Implementado: duplicatas de `HGLG11` e `BTLG11` removidas de `FIIS_CONHECIDOS`; `PeersEngine` usa `MAX_WORKERS`; `RISK_FREE_RATE` foi renomeado para `RISK_FREE_RATE_FALLBACK`.

# Seção 7 — O que NÃO alterar

- Não alterar o schema do SQLite em `database.py` a menos que a tarefa peça explicitamente migração ou histórico append-only. As tabelas atuais incluem `analises`, `carteira_real` e `fundamentals_cache`.
- Não modificar `app.py` durante a refatoração da Fase 1. A Fase 1 deve introduzir modelos dataclass e `AnalysisService` mantendo a interface Streamlit intacta.
- Não salvar `historico` no banco: `app.py:122` remove esse campo antes de `db.salvar_analise()`.
- Não remover a cadeia de fallback Groq -> Gemini -> Ollama em `ai_core.py:66`, `ai_core.py:78` e `ai_core.py:94`.
- Não remover o timeout do Gemini em `ai_core.py:86-90`.
- Não remover o cache curto de dados de mercado em `app.py:52-62`.
- Não remover o gráfico Candlestick com MA50 e MA200 em `app.py:166-189`.
- Não remover a whitelist de FIIs nem a lista de Units conhecidas de `config.py:39-58`.
- Não alterar a lógica de distressed tickers em `valuation_engine.py:19-33` sem teste específico.
- Não remover flags de qualidade (`erro_scraper`, `dados_parciais`, `pl_confiavel`, `dy_confiavel`, `confianca`, `riscos`), porque elas controlam recomendação e transparência.
- Não remover o lock/rate-limit do Fundamentus em `fundamentus_scraper.py:91-97`.
- Não alterar `auditar_recomendacoes.py`, `auditoria.py` e `limpar_banco.py` como parte de correções financeiras sem validar que a auditoria operacional e, quando aplicável, o diagnóstico legado continuam batendo com produção.

# Seção 8 — Roadmap de refatoração atual

Este é o roadmap ativo para próximos agentes. A antiga ordem de correções financeiras foi arquivada porque os bugs listados já foram resolvidos.

1. Fase 1 — modelos dataclass + `AnalysisService`, com `app.py` intocado.
   - Criar modelos explícitos para dados de mercado, análise de ação/FII, qualidade/proveniência básica e resposta de serviço.
   - Introduzir `AnalysisService` como orquestrador testável entre `MarketEngine`, `ValuationEngine`, `FIIEngine`, `TechnicalEngine`, `PeersEngine`, `SentinelaAI` e persistência.
   - Não modificar `app.py` nesta fase; a UI deve continuar chamando os engines atuais até uma fase posterior.

2. Fase 2 — `AnalysisRepository` append-only.
   - Introduzir repositório para histórico de análises sem perder o snapshot anterior.
   - Alteração de schema só é permitida se a tarefa pedir migração ou histórico append-only.
   - Preservar compatibilidade com a leitura atual de `analises` enquanto o app não for migrado.

3. Fase 3 — `AssetClassifier` central.
   - Implementado nos fluxos ativos: `sentinela/services/analyze_asset.py`, `auditar_recomendacoes.py`, `portfolio_engine.py`, `app.py` e `market_engine.py`.
   - Não reintroduzir regras locais duplicadas para FII/Unit nesses caminhos; use `AssetClassifier`.
   - Restam apenas cópias intencionais em `tests/test_asset_classifier_equivalence.py`, documentação/histórico, utilitário de manutenção (`limpar_banco.py`) e diagnóstico legado (`auditoria.py`).
   - A regra central preserva `FIIS_CONHECIDOS`, `UNITS_CONHECIDAS` e a invariante de segurança de Units conhecidas não virarem FIIs.

4. Fase 4 — proveniência por campo.
   - Evoluir de `fonte_fundamentos` agregada para origem por campo financeiro.
   - Registrar fonte, idade, uso de cache/manual e riscos por campo quando possível.
   - Manter a UI de Qualidade dos Dados coerente com os novos metadados.

5. Fase 5 — melhorias de FIIs, proventos e total return.
   - Melhorar cálculo de FIIs com proventos, consistência de DY, histórico de distribuições e retorno total.
   - Separar retorno por preço de retorno com proventos quando houver dados suficientes.
   - Manter avisos explícitos quando dados de proventos forem parciais, manuais ou derivados.

# Seção 9 — Auditoria e validação atuais

- `auditar_recomendacoes.py` é o script operacional atual de auditoria. Ele analisa a cesta fixa de tickers, gera `logs/auditoria_recomendacoes.txt`, calcula métrica geral de falha de dados e métrica operacional de falha excluindo casos não analisáveis, como delisted/distressed bloqueados.
- `auditoria.py` é legado/diagnóstico profundo. Use quando precisar investigar Selic, banco, scraper, valuation, técnica, prompt ou referência Fundamentus com mais detalhe; não trate como auditoria operacional padrão.
- Baseline atual conhecido após a migração do `AssetClassifier`: 147 testes passando. Para mudanças de código, validar com `python -m pytest -q`; para mudanças de recomendação/dados, rodar também `python auditar_recomendacoes.py`.
- Para mudanças apenas em `AGENTS.md` ou documentação, testes automatizados não são obrigatórios, mas o diff deve confirmar que nenhum source/test foi alterado.

# Seção 10 — Estado atual do projeto

- 147 testes passando no baseline atual conhecido.
- `AssetClassifier` é o classificador central nos caminhos ativos: `AnalysisService`, `auditar_recomendacoes.py`, `portfolio_engine.py`, `app.py` e `market_engine.py`.
- Brapi é a fonte preferencial de fundamentos quando `BRAPI_TOKEN` está configurado.
- yfinance permanece responsável preferencial por preço atual e histórico.
- Fundamentus é fallback/complemento para fundamentos quando Brapi está indisponível ou incompleta.
- `fundamentals_cache` guarda os últimos fundamentos válidos em SQLite e pode preencher campos faltantes com flag `dados_cache`.
- A auditoria operacional mede falha geral e falha operacional, evitando penalizar tickers que não pertencem ao universo analisável.
- A UI expõe Qualidade dos Dados com fonte de preço, fonte de fundamentos, dados parciais, erro de scraper, uso de cache/manual, campos faltantes e riscos de dados.
