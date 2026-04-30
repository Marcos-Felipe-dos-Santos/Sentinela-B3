# Seção 1 — Visão geral do projeto

Sentinela B3 é uma aplicação pessoal e educacional de análise de ativos da bolsa brasileira, cobrindo ações e FIIs. O README descreve o foco em valuation, análise técnica e suporte à decisão, com aviso explícito de que não constitui recomendação de investimento.

A interface é Streamlit em `app.py`, com quatro modos no menu lateral: Terminal, Carteira, Gestor e Config. A página é configurada em `app.py:17` como `Sentinela B3 v12.1`. O README não declara uma versão numérica; ele descreve o projeto como Sentinela B3 e lista a stack.

Stack técnica lida no código e no README: Python, Streamlit, SQLite, pandas, numpy, scipy, Plotly, yfinance, requests, BeautifulSoup, python-dotenv, Groq, Gemini e Ollama. A persistência local fica em SQLite via `database.py`; dados de mercado entram por yfinance, Fundamentus e Brapi opcional via `market_engine.py`; valuation de ações fica em `valuation_engine.py`; valuation de FIIs fica em `fii_engine.py`; técnica fica em `technical_engine.py`; otimização de carteira em `portfolio_engine.py`; comparação setorial em `peers_engine.py`; IA em `ai_core.py`; auditoria operacional em `auditoria.py`.

Arquivos principais:

- `app.py`: interface Streamlit, roteamento entre ações/FIIs, cache curto de dados, renderização de valuation, IA, técnica, peers, gráfico e carteira.
- `config.py`: modelos de IA, parâmetros globais, listas de FIIs e Units conhecidas, tickers distressed, Selic dinâmica com cache manual.
- `market_engine.py`: consolida dados de yfinance, Fundamentus e Brapi.
- `valuation_engine.py`: calcula fair value de ações por Graham, Bazin, Lynch e Gordon, score, riscos, confiança e recomendação.
- `fii_engine.py`: calcula fair value de FIIs via Bazin adaptado com DY, Selic, P/VP e vacância conhecida.
- `database.py`: cria e acessa tabelas `analises` e `carteira_real` no SQLite local.
- `ai_core.py`: fallback de IA Groq -> Gemini -> Ollama.
- `auditoria.py`: script de diagnóstico que consulta Selic, banco, scraper, valuation, técnica, prompt e referência do Fundamentus.

# Seção 2 — Arquitetura e fluxo de dados

No modo Terminal, o usuário digita um ticker em `app.py:73`. Ao clicar em Analisar, `app.py:78` chama `buscar_dados_ticker_cached()`, que usa `MarketEngine.buscar_dados_ticker()` com cache de 300 segundos.

O `MarketEngine` normaliza o ticker em `market_engine.py:33` e monta um dicionário com flags de fonte e qualidade em `market_engine.py:36`. Primeiro tenta yfinance em `_buscar_yfinance()`: coleta histórico de 1 ano, preço atual, `pl`, `pvp`, `dy`, `roe`, `quote_type` e `pl_confiavel`. Depois tenta Fundamentus em `_buscar_fundamentus()`, que chama `FundamentusScraper.buscar_dados()` e, quando obtém dados válidos, sobrescreve campos fundamentalistas do yfinance mantendo preço/histórico. Se Fundamentus falhar e Brapi estiver disponível, `_buscar_brapi()` preenche campos ausentes.

O `FundamentusScraper` monta uma sessão com cloudscraper quando disponível, ou `requests.Session` como fallback. Ele limita requisições com lock e intervalo mínimo, baixa a página `detalhes.php?papel={ticker}`, extrai pares de tabela, limpa números brasileiros em `_limpar_valor()` e converte percentuais para decimal.

Depois de coletar dados, `app.py:85` decide se o ticker é FII usando whitelist (`FIIS_CONHECIDOS`), `quote_type == 'MUTUALFUND'`, sufixo `11` e exclusão de `UNITS_CONHECIDAS`. FIIs seguem para `FIIEngine.analisar()`; ações seguem para `ValuationEngine.processar()` e para `PeersEngine.comparar()`.

Para ações, `ValuationEngine` normaliza DY, calcula LPA/VPA, consulta `get_selic_atual()`, classifica perfil crescimento versus renda/valor, aplica os métodos disponíveis, calcula média simples dos valores válidos, score sigmoid ajustado por qualidade, riscos, confiança e recomendação. Para FIIs, `FIIEngine` normaliza DY, ajusta por vacância conhecida, usa Selic para preço justo, ajusta score por DY versus Selic e P/VP, e define compra/venda por upside.

O `TechnicalEngine` calcula RSI, médias móveis, MACD, bandas de Bollinger, momento e tendência a partir do histórico. O `PeersEngine` busca peers setoriais com `ThreadPoolExecutor`, calcula médias de P/L, P/VP e DY e devolve o setor e peers utilizados. O `SentinelaAI` formata o dicionário de dados sem campos volumosos, gera um prompt e tenta Groq, Gemini com timeout de 15 segundos, e Ollama local.

Por fim, `app.py` mescla `dados.update(analise)`, adiciona técnica e resposta de IA, remove `historico` antes de persistir e chama `DatabaseManager.salvar_analise()`. A UI mostra métricas principais, abas de Valuation & IA, Técnica & Peers e Gráfico. A aba Carteira lê `database.py`, atualiza preços com o mesmo cache e calcula valor atual e rentabilidade. A aba Gestor monta históricos de carteira e chama `PortfolioEngine.otimizar()`.

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
  - É importado por: `ai_core.py:7`, `app.py:15`, `auditar_recomendacoes.py:24`, `auditoria.py:252`, `auditoria.py:820`, `auditoria.py:859`, `fii_engine.py:2`, `limpar_banco.py:22`, `portfolio_engine.py:4`, `valuation_engine.py:3`.

- `valuation_engine.py`
  - Importa: `logging` (`valuation_engine.py:1`), `math` (`valuation_engine.py:2`), `get_selic_atual` e `DISTRESSED_TICKERS` de `config` (`valuation_engine.py:3`).
  - É importado por: `app.py:9`, `auditar_recomendacoes.py:21`.

- `fii_engine.py`
  - Importa: `logging` (`fii_engine.py:1`), `get_selic_atual` de `config` (`fii_engine.py:2`).
  - É importado por: `app.py:10`, `auditar_recomendacoes.py:22`, `auditoria.py:859`.

- `market_engine.py`
  - Importa: `logging` (`market_engine.py:1`), `Any`, `Dict`, `Optional` de `typing` (`market_engine.py:2`), `yfinance` (`market_engine.py:4`), `FundamentusScraper` de `fundamentus_scraper` (`market_engine.py:6`), `BrapiProvider` de `brapi_provider` (`market_engine.py:7`).
  - É importado por: `app.py:8`, `auditar_recomendacoes.py:20`, `auditoria.py:145`.

- `app.py`
  - Importa: `time` (`app.py:1`), `Any`, `Dict`, `Optional` de `typing` (`app.py:2`), `pandas` (`app.py:4`), `plotly.graph_objects` (`app.py:5`), `streamlit` (`app.py:6`), `DatabaseManager` (`app.py:7`), `MarketEngine` (`app.py:8`), `ValuationEngine` (`app.py:9`), `FIIEngine` (`app.py:10`), `TechnicalEngine` (`app.py:11`), `PortfolioEngine` (`app.py:12`), `PeersEngine` (`app.py:13`), `SentinelaAI` (`app.py:14`), `APP_VERSION`, `FIIS_CONHECIDOS` e `UNITS_CONHECIDAS` (`app.py:15`).
  - É importado por: nenhum arquivo encontrado por busca textual.

- `ai_core.py`
  - Importa: `ThreadPoolExecutor` e `FuturesTimeout` (`ai_core.py:1`), `logging` (`ai_core.py:2`), `os` (`ai_core.py:3`), `requests` (`ai_core.py:5`), constantes de `config` (`ai_core.py:7`), `google.genai` dinamicamente (`ai_core.py:23`), `Groq` dinamicamente (`ai_core.py:33`).
  - É importado por: `app.py:14`.

- `database.py`
  - Importa: `sqlite3` (`database.py:1`), `json` (`database.py:2`), `logging` (`database.py:3`), `datetime` (`database.py:4`), `closing` (`database.py:5`), `os` dentro de `reset_db()` (`database.py:121`).
  - É importado por: `app.py:7`.

- `technical_engine.py`
  - Importa: `pandas` (`technical_engine.py:1`), `numpy` (`technical_engine.py:2`).
  - É importado por: `app.py:11`, `auditar_recomendacoes.py:23`.

- `portfolio_engine.py`
  - Importa: `numpy` (`portfolio_engine.py:1`), `pandas` (`portfolio_engine.py:2`), `minimize` de `scipy.optimize` (`portfolio_engine.py:3`), `FIIS_CONHECIDOS`, `UNITS_CONHECIDAS` e `get_selic_atual` de `config` (`portfolio_engine.py:4`).
  - É importado por: `app.py:12`.

- `peers_engine.py`
  - Importa: `logging` (`peers_engine.py:1`), `ThreadPoolExecutor` e `as_completed` (`peers_engine.py:2`).
  - É importado por: `app.py:13`.

- `fundamentus_scraper.py`
  - Importa: `logging` (`fundamentus_scraper.py:1`), `threading` (`fundamentus_scraper.py:2`), `time` (`fundamentus_scraper.py:3`), `requests` (`fundamentus_scraper.py:5`), `BeautifulSoup` (`fundamentus_scraper.py:6`), `cloudscraper` opcional (`fundamentus_scraper.py:14`).
  - É importado por: `market_engine.py:6`.

- `auditoria.py`
  - Importa: `sys` (`auditoria.py:18`), `os` (`auditoria.py:19`), `re` (`auditoria.py:20`), `io` (`auditoria.py:21`), `json` (`auditoria.py:22`), `math` (`auditoria.py:23`), `sqlite3` (`auditoria.py:24`), `datetime` (`auditoria.py:25`), `requests` dentro da auditoria Selic (`auditoria.py:78`), `MarketEngine` (`auditoria.py:145`), `numpy` (`auditoria.py:220` e `auditoria.py:527`), `get_selic_atual` (`auditoria.py:252`), `APP_VERSION` (`auditoria.py:820`), `FIIS_CONHECIDOS` e `UNITS_CONHECIDAS` (`auditoria.py:859`), `FIIEngine` (`auditoria.py:878`).
  - É importado por: nenhum arquivo encontrado por busca textual.

- `requirements.txt`
  - Importa: não se aplica.
  - É importado por: não se aplica.

- `README.md`
  - Importa: não se aplica.
  - É importado por: não se aplica.

# Seção 5 — Bugs confirmados (com localização exata)

**[RESOLVIDO — Fase 2] Bug 1 — Recomendação de venda depende indevidamente de técnico negativo**

Arquivo: `valuation_engine.py`, linhas 195-210.

Código atual:

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

Código atual da produção:

```python
if not is_growth and dy > 0 and dy_confiavel:
    if dy > 0.15:
        riscos.append("DY muito alto (possível armadilha)")
        confianca -= 10
    taxa_minima = max(selic, 0.05)
    metodos['Bazin'] = (dy * p) / taxa_minima
```

Arquivo de auditoria: `auditoria.py`, linhas 365-369.

Código atual da auditoria:

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

Código atual da produção:

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

Código atual da auditoria:

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

Código atual da produção:

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

Código atual da auditoria:

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

Código atual da produção:

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

Código atual da auditoria:

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

Código atual:

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

# Seção 6 — Melhorias de qualidade (com localização exata)

**[IMPLEMENTADO — Fase 2] Melhoria 1 — Tornar o gráfico responsivo à largura do container**

Arquivo: `app.py`, linha 189.

Código atual:

```python
st.plotly_chart(fig)
```

O que deve mudar e por quê: usar `st.plotly_chart(fig, use_container_width=True)` para manter o gráfico Candlestick consistente com layout wide e colunas responsivas do Streamlit.

**[IMPLEMENTADO — Fase 2] Melhoria 2 — Alinhar metadados de versão**

Arquivo: `app.py`, linha 17.

Código atual:

```python
st.set_page_config(page_title="Sentinela B3 v12.1", layout="wide", page_icon="🦅")
```

Arquivo: `auditoria.py`, linhas 811-814.

Código atual:

```python
_rel['meta'] = {
    "timestamp":  datetime.now().isoformat(),
    "versao":     "Sentinela B3 v13",
    "db_path":    DB_PATH,
```

O que deve mudar e por quê: centralizar a versão ou atualizar os metadados para evitar que UI e auditoria reportem versões diferentes. O README não traz versão numérica.

**[IMPLEMENTADO — Fase 2] Melhoria 3 — Fechar executor do Gemini de forma explícita**

Arquivo: `ai_core.py`, linhas 13-17.

Código atual:

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

Código atual:

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

Código atual:

```python
with ThreadPoolExecutor(max_workers=4) as executor:
    futures = {executor.submit(self.market.buscar_dados_ticker, p): p
               for p in target_peers}
```

O que deve mudar e por quê: `app.py` usa `buscar_dados_ticker_cached()`, mas `PeersEngine` chama `self.market.buscar_dados_ticker` diretamente. Isso pode repetir yfinance/Fundamentus fora do cache do app. Verificar uma estratégia de cache no engine ou injeção de função cached.

# Seção 7 — O que NÃO alterar

- Não alterar a estrutura do SQLite em `database.py` sem necessidade explícita: tabelas `analises` e `carteira_real` são criadas em `database.py:28` e `database.py:35`.
- Não salvar `historico` no banco: `app.py:122` remove esse campo antes de `db.salvar_analise()`.
- Não remover a cadeia de fallback Groq -> Gemini -> Ollama em `ai_core.py:66`, `ai_core.py:78` e `ai_core.py:94`.
- Não remover o timeout do Gemini em `ai_core.py:86-90`.
- Não remover o cache curto de dados de mercado em `app.py:52-62`.
- Não remover o gráfico Candlestick com MA50 e MA200 em `app.py:166-189`.
- Não remover a whitelist de FIIs nem a lista de Units conhecidas de `config.py:39-58`.
- Não alterar a lógica de distressed tickers em `valuation_engine.py:19-33` sem teste específico.
- Não remover flags de qualidade (`erro_scraper`, `dados_parciais`, `pl_confiavel`, `dy_confiavel`, `confianca`, `riscos`), porque elas controlam recomendação e transparência.
- Não remover o lock/rate-limit do Fundamentus em `fundamentus_scraper.py:91-97`.
- Não alterar `auditoria.py` e `limpar_banco.py` como parte de correções financeiras sem validar que a auditoria continua batendo com produção.

# Seção 8 — Ordem de execução das correções

1. `valuation_engine.py:207` — remover a dependência de `tecnico_negativo` para emitir `VENDA` quando o upside for menor que -15%.
2. `auditoria.py:365` — alinhar Bazin da auditoria com `valuation_engine.py:110-111`.
3. `auditoria.py:397` — alinhar Lynch da auditoria com `valuation_engine.py:116-122`, ou decidir que a produção deve seguir a auditoria e ajustar ambos com teste.
4. `auditoria.py:431` — alinhar Gordon da auditoria com `valuation_engine.py:127-134`, ou decidir que a produção deve seguir a auditoria e ajustar ambos com teste.
5. `auditoria.py:847` — usar a mesma detecção de FII do `app.py:85-95`, incluindo `FIIS_CONHECIDOS` e `UNITS_CONHECIDAS`.
6. `portfolio_engine.py:58` — classificar FIIs no otimizador usando a mesma regra de FII/Unit do app ou uma função compartilhada.
7. `app.py:189` — passar `use_container_width=True` para o gráfico Plotly.
8. `app.py:17` e `auditoria.py:813` — alinhar versão reportada pela UI e pelo relatório.
9. `ai_core.py:16` — definir ciclo de vida explícito para `_gemini_executor`.
10. `database.py:48` — adicionar type hints e docstrings em métodos públicos sem mudar contratos.

# Seção 9 — Testes manuais para validar cada correção

- Bug 1 (`valuation_engine.py`): executar um teste direto em Python instanciando `ValuationEngine` com dados sintéticos de ação não distressed, `preco_atual=100`, fundamentos que gerem `fair_value` abaixo de `85`, e sem campo `tecnico_negativo`. Resultado esperado: recomendação `VENDA` quando `upside < -15%`, mesmo sem `tecnico_negativo`.

- Bug 2 (`auditoria.py` Bazin): usar um ticker de renda com DY confiável, por exemplo `PETR4` ou `BBAS3`, e comparar `metodos_usados` do app com a seção Bazin de `python auditoria.py PETR4`. Resultado esperado: mesmo valor de Bazin na produção e na auditoria, respeitando arredondamento.

- Bug 3 (`auditoria.py` Lynch): usar um ticker de crescimento com ROE alto e DY baixo, por exemplo `WEGE3`, e comparar o valor de Lynch mostrado pelo app com `python auditoria.py WEGE3`. Resultado esperado: auditoria e produção calculam o mesmo Lynch.

- Bug 4 (`auditoria.py` Gordon): usar ticker com DY maior que 4% e ROE maior que 10%, por exemplo `BBAS3` ou `EGIE3`, e comparar Gordon no app e em `python auditoria.py BBAS3`. Resultado esperado: mesmo crescimento `g`, mesma taxa `k` e mesmo valor de Gordon.

- Bug 5 (`auditoria.py` roteamento FII): executar `python auditoria.py SANB11 TAEE11 MXRF11`. Resultado esperado: `SANB11` e `TAEE11` não entram como FII; `MXRF11` entra como FII se estiver na whitelist ou passar pela regra do app.

- Bug 6 (`portfolio_engine.py`): montar carteira com uma Unit conhecida (`TAEE11` ou `SANB11`) e uma ação comum (`ITUB4`) no modo Carteira/Gestor. Resultado esperado: a Unit não deve ser tratada como FII na segmentação 40/60, e a alocação deve refletir a regra compartilhada com o app.

- Melhoria do gráfico (`app.py`): abrir o app com `streamlit run app.py`, analisar `PETR4` e inspecionar a aba Gráfico em viewport estreito e largo. Resultado esperado: Candlestick ocupa a largura disponível sem ficar comprimido.

- Versão (`app.py`/`auditoria.py`): abrir a UI e rodar `python auditoria.py --db-only`. Resultado esperado: ambos reportam a mesma versão ou a versão vem de uma constante única.

- Gemini executor (`ai_core.py`): com `GEMINI_API_KEY` configurada, provocar timeout ou simular cliente lento e confirmar que o app cai para Ollama sem travar. Depois de resetar/recarregar o Streamlit, verificar que não há acúmulo anormal de threads.

- Type hints/docstrings (`database.py`): executar `python -m pytest -q` e abrir o app. Resultado esperado: nenhum chamador quebra, e métodos continuam aceitando os mesmos argumentos.

# Seção 10 — Estado atual (Fase 3)

Já implementado e não precisa ser feito:

- Bugs 1 a 6 da Seção 5 estão resolvidos na Fase 2.
- Melhoria 1 da Seção 6 está implementada: `app.py:189` usa `st.plotly_chart(fig, use_container_width=True)`.
- Melhoria 2 da Seção 6 está implementada: `config.py:23` define `APP_VERSION = "v14"`; `app.py:17` usa `APP_VERSION`.
- Melhoria 3 da Seção 6 está implementada: `ai_core.py:19-24` encerra `_gemini_executor` em `__del__()`.
- Melhoria 4 da Seção 6 está implementada: `database.py:48`, `database.py:80` e `database.py:87` têm type hints e docstrings.
- Cache na Carteira está implementado: `app.py:219` usa `buscar_dados_ticker_cached(ticker)` no loop da aba Carteira.
- Filtro de peers por dados úteis está implementado: `peers_engine.py:64-72` define `_peer_valido()` e não descarta apenas por `erro_scraper`.
- Units no otimizador estão implementadas: `portfolio_engine.py:4` importa `FIIS_CONHECIDOS` e `UNITS_CONHECIDAS`; `portfolio_engine.py:57-61` usa `_is_fii()`.

Ainda falta implementar nesta fase:

- Pendente: `remover_posicao()` em `database.py`; não existe método `def remover_posicao`.
- Pendente: botão de remoção na aba Carteira em `app.py`; não existem widgets `remover_ticker` ou `btn_remover`.
- Pendente: Sharpe Ratio no retorno de `portfolio_engine.py`; não existem `_sharpe_otimizado`, `_retorno_anual` ou `_volatilidade_anual`.
- Pendente: métricas de Sharpe/Retorno/Volatilidade no Gestor em `app.py`; o Gestor ainda chama `st.bar_chart(res)` diretamente em `app.py:276`.
- Pendente: ATR em `technical_engine.py`; o retorno ainda não inclui chave `atr`.
- Pendente: duplicatas em `FIIS_CONHECIDOS` em `config.py`; `HGLG11` e `BTLG11` aparecem nas linhas `config.py:42` e `config.py:50`.
- Pendente: usar `MAX_WORKERS` em `peers_engine.py`; o código ainda usa `ThreadPoolExecutor(max_workers=4)` em `peers_engine.py:44`.
- Pendente: renomear `RISK_FREE_RATE` em `config.py`; `config.py:110` ainda define `RISK_FREE_RATE = SELIC_FALLBACK`. Busca nos arquivos Python encontrou uso apenas em `config.py`.
