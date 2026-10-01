# Inventário de resíduos — Fase 0

**Gerado no F0-7, em 1/10/2026, sem remover nada.** O F0-8 executa só a categoria **remover já** e atualiza este arquivo com o que saiu.

Categorias:

- **remover já** — sem efeito em comportamento; o F0-8 remove.
- **remover na fase X** — depende de um item do `docs/PLANO.md`; o item está citado.
- **investigar** — uso incerto ou decisão do Marcos; o loop não remove.
- **manter** — falso positivo, com o motivo.

Escopo da análise: arquivos rastreados e código do repositório, exceto `venv/`, `mutants/`, `outputs/` e `data/`. Os arquivos intocáveis da Fase 0 (`valuation_engine.py`, `fii_engine.py`, `portfolio_engine.py` e as seções `MacroContext` e `_normalizar_dy` de `config.py`) aparecem quando têm achado, mas nenhum item deles entra em **remover já**.

Comandos usados (reproduzíveis):

```bash
python -m vulture . --min-confidence 80 --exclude venv,mutants,outputs,data
python -m vulture . --min-confidence 60 --exclude venv,mutants,outputs,data
ruff check --select F401,F841,ERA001 . --exclude venv,mutants,outputs,data
ruff check . --statistics --exclude venv,mutants,outputs,data
deptry . --exclude "venv|mutants|outputs|data"
git ls-files ; git branch -a --merged main
```

---

## 1. Código morto — vulture

### 1.1 Confiança ≥ 80% (7 achados, todos em `tests/`)

| Local | Achado | Categoria | Motivo |
|---|---|---|---|
| `tests/conftest.py:26` | `kwargs` não usado | manter | Stub de `requests.get` precisa aceitar a mesma assinatura. Vai para `vulture_whitelist.py` |
| `tests/test_backtest_engine.py:136` | `kwargs` | manter | Idem: dublê com a assinatura da função substituída |
| `tests/test_cvm_provider.py:155` | `kwargs` | manter | Idem |
| `tests/test_cvm_ticker_map.py:68` | `kwargs` | manter | Idem |
| `tests/test_market_engine.py:57, 623` | `kwargs` | manter | Idem |
| `tests/test_market_engine.py:85` | `max_age_days` | manter | Parâmetro do dublê de `buscar_fundamentos_cache` |

O `CLAUDE.md` prevê `vulture_whitelist.py` com o motivo de cada exceção. O F0-8 cria o arquivo com estes sete itens.

### 1.2 Confiança 60–79% (25 achados, em código de produção)

| Local | Achado | Categoria | Motivo / item |
|---|---|---|---|
| `auditar_recomendacoes.py:38-40` | `QUALITY_CAN_BE_BUY`, `CYCLICAL_NEEDS_CAUTION`, `FIIS` | **remover já** | Definidos e nunca lidos (busca por nome em todo o repositório). Os nomes também usam vocabulário a aposentar |
| `config.py:33` | `TIMEOUT_API` | **remover já** | Nenhum leitor no repositório, nem nos testes. Fora das seções intocáveis |
| `config.py:120` | `RISK_FREE_RATE_FALLBACK` | **remover já** | Alias estático sem leitor; o próprio comentário manda usar `get_selic_atual()`. Fora das seções intocáveis |
| `market_engine.py:340, 342` | `fundamentus_ok` | **remover já** | Variável atribuída e nunca lida (também é o F841). Remover a atribuição, mantendo a chamada `_buscar_fundamentus(...)`, que tem efeito colateral |
| `market_engine.py:678` | `buscar_noticias` | investigar | Nenhum chamador; a Fase 5 constrói o módulo de notícias. Decidir se sai agora ou com a Fase 5 |
| `brapi_provider.py:125` | `get_quote` | investigar | Nenhum chamador, nem nos testes; a cascata usa `get_fundamentals`. Pode ser o caminho do preço da brapi (`CLAUDE.md`, "preço: brapi só se o yfinance falhar"), então a decisão é do Marcos |
| `cvm_provider.py:63` | `baixar_itr` | remover na fase | Será usado pelo TTM — F2A-7 |
| `sentinela/domain/enums.py:10-11` | `ETF`, `BDR` | remover na fase | Previstos para a classe do ativo — F2A-1. Entram no `vulture_whitelist.py` até lá |
| `sentinela/domain/models.py:73,74,101,103,105,165,167,205` | campos `fonte_preco`, `fonte_fundamentos`, `roic`, `div_liq_patrimonio`, `margem_bruta`, `score_final`, `metodos_usados`, `atr` | manter | Campos de dataclass lidos por serialização e pelos testes de domínio; fazem parte do modelo `sentinela/`, hoje desconectado (E-21, F3-6) |
| `sentinela/domain/provenance.py:101` | `with_warning` | manter | API do domínio da camada `sentinela/` ainda desconectada (E-21); sem chamador hoje, nem nos testes. Whitelist até o F3-6 decidir |
| `auditoria.py:663`, `cvm_ticker_map.py:91`, `limpar_banco.py:47`, `sentinela/repositories/analysis_repository.py:24` | `row_factory` | manter | Atribuição a atributo do `sqlite3.Connection`; o vulture não entende. Whitelist |

---

## 2. Imports e variáveis sem uso, código comentado — ruff

`ruff check --select F401,F841,ERA001` encontrou 15 achados.

| Local | Regra | Categoria | Motivo |
|---|---|---|---|
| `auditoria.py:220` | F401 `numpy` | **remover já** | `import numpy as np` dentro de função; nenhum `np.` na função (conferido por leitura) |
| `auditoria.py:536` | F401 `numpy` | **remover já** | Idem, em `auditar_tecnica` |
| `market_engine.py:342` | F841 `fundamentus_ok` | **remover já** | Ver 1.2 |
| `tests/test_data_quality.py:5` | F401 `pytest` | **remover já** | Import sem uso; não altera nenhum teste |
| `tests/test_peers_engine.py:5` | F401 `patch` | **remover já** | Idem |
| `tests/test_peers_engine.py:7` | F401 `pytest` | **remover já** | Idem |
| `tests/test_database.py:39` | F841 `wal_path` | **remover já** | Variável atribuída e nunca lida no teste (as linhas seguintes só têm comentário e `db.reset_db()`) |
| `config.py:41, 44` | ERA001 | manter | Falso positivo: títulos de seção da lista de FIIs (`# Papel (CRI/CRA)`, `# Tijolo (Lajes/Galpões)`) |
| `tests/test_data_quality.py:62, 73, 192, 215` | ERA001 | manter | Falso positivo: rótulos de seção e comentários explicativos |
| `tests/test_valuation_engine.py:285, 287` | ERA001 | manter | Falso positivo: aritmética explicada em comentário (`# k = selic + 0.07 -> ...`) |

Conferir antes de remover: nenhum módulo acessa `fundamentus_ok` nem `np` por esses arquivos (o `app.py` tem cobertura 0%; ele não importa nada de `auditoria.py`).

---

## 3. Dívida do `ruff check .` completo

**332 erros** (301 em 1/10; os 31 a mais vêm de arquivos que o próprio loop criou: `scripts/dossie_fase2.py` com 30 e `tests/conftest.py` com 1). **247 têm correção automática.** O repositório não tem arquivo de configuração do ruff (`ruff.toml` ou `[tool.ruff]`), então as regras vêm do ambiente; versionar uma configuração é parte do F1-13.

### 3.1 Correções automáticas seguras (não mudam comportamento)

Anotações de tipo, ordem de imports, f-strings sem variável e `noqa` obsoleto. **Categoria: remover na fase 1 (F1-13, `ruff` completo no CI).**

| Regra | Total | Onde |
|---|---|---|
| UP045 (`Optional[X]` → `X \| None`) | 74 | `sentinela/domain/models.py` 21, `brapi_provider.py` 11, `market_engine.py` 11, `backtesting/backtest_engine.py` 10 |
| UP006 (`List`/`Dict` → `list`/`dict`) | 62 | `market_engine.py` 27, `auditar_recomendacoes.py` 16, `limpar_banco.py` 11, `brapi_provider.py` 7 |
| I001 (ordem de imports) | 25 | cerca de um por arquivo |
| F541 (f-string sem placeholder) | 18 | `auditar_recomendacoes.py` 10, `auditoria.py` 8 |
| UP037 (anotação entre aspas) | 11 | `sentinela/domain/models.py` 6, `provenance.py` 5 |
| RUF046 (`int()` desnecessário) | 10 | `backtesting/backtest_engine.py` — só depois do F3-8 (travado na Fase 3) |
| RUF100 (`noqa` obsoleto) | 8 | `scripts/dossie_fase2.py` 7, `tests/conftest.py` 1 — **remover já** (resíduo do próprio loop, ver 3.3) |
| F401 (import sem uso) | 5 | já na seção 2 |
| FURB188, PYI041 | 3 | `asset_classifier.py`, `backtest_engine.py`, teste de equivalência |

Atenção: UP045 e UP006 em `market_engine.py`, `brapi_provider.py` e `sentinela/` caem em arquivos travados nas Fases 2A e 1; entram no F1-13 só onde o arquivo não estiver travado, e nos demais a limpeza da fase correspondente.

### 3.2 Mudam comportamento ou exigem julgamento

**Categoria: investigar / remover na fase indicada.** Nenhuma entra no F0-8.

| Regra | Total | Onde | Risco / destino |
|---|---|---|---|
| BLE001 (`except` genérico) | 39 | `market_engine.py` 7, `ai_core.py` 6, `auditoria.py` 6, `config.py` 4, `fundamentus_scraper.py` 2 | Troca o tratamento de falha de rede e de LLM — E-15; tratar item a item na fase do módulo |
| DTZ005/006/011 (data sem fuso) | 19 | `database.py` 4, `auditoria.py` 3, `cvm_ticker_map.py` 3, providers CVM | Mudam o formato gravado no banco — F3-2 (SQLite único) |
| B023 (laço e fechamento) | 8 | `scripts/dossie_fase2.py` | Funções internas dentro de laço; revisar no script |
| PLR0124 (comparação consigo) | 5 | `auditoria.py:558-559` (`ma50 != ma50`, `ma200 != ma200`), `scripts/dossie_fase2.py` 3 | **Cuidado:** `x != x` é o teste de NaN; não "corrigir" |
| SIM117 | 13 | `database.py` 5, `cvm_ticker_map.py` 3 | `with` aninhado sobre conexões; refactor |
| C408, PERF102, RUF015, SIM102/103/202, RUF012/013, PT014, S110 | 31 | vários | Estilo; S110 (`try`/`except`/`pass`, 2) esconde falhas em `ai_core.py` e `fundamentus_scraper.py` |

### 3.3 Resíduo do próprio loop

`scripts/dossie_fase2.py` (30 achados), criado no F0-6: `noqa` obsoletos (7), `carteira(..., fii, ...)` com parâmetro `fii` sem uso, campos de `mercado()` que ninguém lê (`ex_div_12m`, `pl`, `roe`, `quote_type`). **Remover já**: os `noqa` obsoletos e o parâmetro sem uso. O resto é estilo de script de levantamento e fica para o F1-13.

---

## 4. Dependências — deptry

| Achado | Categoria | Motivo / item |
|---|---|---|
| DEP001 `cloudscraper` importado e ausente do `requirements.txt` (`fundamentus_scraper.py:14`) | investigar | Depende da decisão do F0-4 (declarar ou remover o scraper). Se o scraper sair, o import some junto |
| DEP002 `reportlab` declarado e sem uso | investigar | Nenhum `import` no repositório e o README não promete PDF. O `.gitignore` ignora `*.xlsx`, o que sugere exportação que existiu. Recomendação: remover do `requirements.txt` depois de o Marcos confirmar que não quer a exportação |
| DEP002 `openpyxl` declarado e sem uso | investigar | Idem (nenhum `to_excel` ou `read_excel`) |
| `pytest-cov` fora do `requirements.txt` | feito | Movido para `requirements-dev.txt` no F0-2 |

---

## 5. Módulos órfãos

Nenhum `.py` é órfão no sentido estrito. Os que ninguém importa em produção:

| Módulo | Quem usa | Categoria | Motivo |
|---|---|---|---|
| `app.py` | ponto de entrada (`streamlit run`) | manter | — |
| `auditoria.py`, `limpar_banco.py` | scripts de linha de comando | manter | `auditoria.py` é a segunda fonte de verdade a aposentar no F2C-8 |
| `auditar_recomendacoes.py` | CLI e teste | manter | Nome e vocabulário a trocar no F2C-4 |
| `backtesting/backtest_engine.py` | CLI e teste | remover na fase 3 | Backtest real no F3-8; os CSVs fabricados saem junto |
| `sentinela/services/analyze_asset.py`, `sentinela/repositories/analysis_repository.py` | só testes | remover na fase 3 | Camada nova desconectada (E-21); o F3-6 liga o `AnalysisService` ao `app.py` |
| `scripts/dossie_fase2.py` | execução manual | manter | Reproduz o dossiê da Fase 2 |

---

## 6. Arquivos rastreados que deveriam estar fora do git

Nenhum `*.db`, `*.log`, `__pycache__`, `outputs/` ou `.env` está rastreado. Há 96 arquivos no índice.

| Arquivo | Categoria | Motivo |
|---|---|---|
| `backtesting/fundamentos_point_in_time.csv` | remover na fase 3 | 15 linhas fabricadas (F-1). Sai no F3-8 |
| `backtesting/backtest_results_v1.csv` | remover na fase 3 | Gerado por versão anterior do engine (F-29). Sai no F3-8 |

### Lacunas do `.gitignore`

Padrões testados com `git check-ignore`:

| Padrão | Estado | Categoria |
|---|---|---|
| `.mutmut-cache` | não ignorado | **remover já** (adicionar ao `.gitignore`); o mutmut 3 usa `mutants/`, mas versões anteriores usam este arquivo |
| `*.db-journal` | não ignorado | **remover já** (adicionar) |
| `*.sqlite-wal`, `*.sqlite-shm` | não ignorados (só `*.sqlite` e `*.sqlite3`) | **remover já** (adicionar) |
| `*.tmp` | não ignorado | **remover já** (adicionar) |
| `.coverage`, `.pytest_cache/`, `.ruff_cache/`, `mutants/`, `outputs/`, `data/`, `.env` | ignorados | — |

Entradas sem alvo local, inofensivas: `verificar_setup.bat`, `.agent/`, `.gemini/`, `.cursor/`, `.VSCodeCounter/`. **Manter** (protegem contra arquivos de ferramentas externas).

---

## 7. Duplicidades conhecidas

| Duplicidade | Categoria | Detalhe |
|---|---|---|
| `FII_MANUAL_FALLBACK` (`config.py:73`, 3 FIIs) × `VACANCIA_CONHECIDA` (`fii_engine.py:10`, 5 FIIs) | remover na fase 2A (F2A-13) | Os 3 FIIs em comum têm a mesma vacância (CVBI11 25%, HGLG11 8%, MXRF11 5%). `FII_MANUAL_FALLBACK` é lido por `market_engine.py:622` e `VACANCIA_CONHECIDA` por `fii_engine.py`; `fii_engine.py` é intocável na Fase 0 |
| MGLU3 em `peers_engine.py:16` (par de varejo), `config.py:68` (`DISTRESSED_TICKERS`) e `auditar_recomendacoes.py:31` | remover na fase 2C (F2C-7) | Mesmo ticker é par setorial e bloqueado como distressed; `VIIA3`, na lista de `auditar_recomendacoes.py`, não existe desde 2023 (F-22) |
| Propriedades do `MacroContext` sem leitor em produção: `cdi`, `ipca_12m`, `ntnb_longa`, `cost_of_equity_real` | remover na fase 2B / 3 (F2B-1, F3-1) | Só os testes as leem. `ntnb_longa` é lido por `cost_of_equity_real`. A seção `MacroContext` é intocável na Fase 0 |
| Constantes do `MacroContext` sem leitor em produção | — | Nenhuma: toda constante tem leitor em produção; `DY_SANIDADE_MAX` é lida só dentro de `config._normalizar_dy` (intocável) |
| Três normalizadores de DY | remover na fase 2A (F2A-4) | `config.py:311`, `market_engine.py:377-379`, `brapi_provider.py:35` |

---

## 8. Documentação que cita arquivo, caminho ou comando inexistente

| Documento | Citação | Categoria | Motivo |
|---|---|---|---|
| `README.md:167` | `venv\Scripts\activate` | remover na fase 6 | Caminho do Windows ao lado de `source venv/bin/activate` (linha 170). O ambiente oficial é o WSL. O README fica travado na Fase 6; o ticket C-A do `docs/jules-backlog.md` já mexe no README e pode levar esta linha |
| `docs/cleanup_report.md` | `Readme.md`, `logs/auditoria_recomendacoes.txt`, `backtesting/backtest_results_v2.csv`, `v3.csv`, `.streamlit/secrets.toml`, `Thumbs.db` | investigar | Relatório de 8/5/2026 sobre a limpeza anterior; os arquivos citados já foram removidos. É histórico, mas aparece como documento vivo em `docs/`. Decidir entre mover para o histórico ou apagar |
| `CLAUDE.md` | `vulture_whitelist.py` | remover na fase 0 (F0-8) | Arquivo criado no F0-8, como o `CLAUDE.md` já descreve; o F0-8 troca esta linha para "feito" |
| `docs/PLANO.md` | `docs/operacao.md`, `sentinela/cli.py` | manter | Arquivos futuros (Fase 4) |
| `docs/PLANO.md`, `docs/loop/fila.md`, `docs/jules-backlog.md` | `docs/loop/fila-faseN-proposta.md`, `docs/loop/pr-fase-N.md`, `tests/test_technical_engine_spec.py` e semelhantes | manter | Arquivos futuros, gerados pelo loop ou pelo Jules |
| `docs/decisoes/scraper-fundamentus.md` | `robots.txt` | manter | Menção genérica, não um caminho do repositório |

Nenhum caminho `C:\` ou `E:\` aparece em código; fora dele, o `E:\` só aparece nos documentos do loop (checkpoint da fila e diário).

---

## 9. Branches

O loop não apaga branch. A lista abaixo é para o Marcos.

**Remotos já integrados à `main`** (`git branch -a --merged main`):

- `origin/feat/cvm-fii-provider`
- `origin/feat/cvm-provider`
- `origin/feat/macro-provider`
- `origin/feat/ui-improvements` (PR #8)
- `origin/refactor/economic-fixes`
- `origin/refactor/macro-context`

**Locais:** `main`; `chore/fase-0-preparacao` (à frente da `main`, não integrado); `v2/fase-0` (a fase em curso). Nenhum branch local está integrado e sobrando.

---

## 10. Lista de execução do F0-8 (só **remover já**)

1. Remover a atribuição `fundamentus_ok` em `market_engine.py:340,342`, mantendo a chamada.
2. Remover `import numpy as np` em `auditoria.py:220` e `:536`.
3. Remover as constantes `QUALITY_CAN_BE_BUY`, `CYCLICAL_NEEDS_CAUTION` e `FIIS` de `auditar_recomendacoes.py:38-40`.
4. Remover `TIMEOUT_API` (`config.py:33`) e `RISK_FREE_RATE_FALLBACK` (`config.py:120`).
5. Remover os imports sem uso em `tests/test_data_quality.py:5`, `tests/test_peers_engine.py:5,7` e a variável `wal_path` em `tests/test_database.py:39`.
6. Em `scripts/dossie_fase2.py`: tirar os `noqa` obsoletos e o parâmetro `fii` de `carteira()`. Os `noqa: E402` só são obsoletos com o conjunto de regras atual (sem configuração versionada); se o F1-13 versionar outro conjunto, podem voltar a ser necessários.
7. `.gitignore`: acrescentar `.mutmut-cache`, `*.db-journal`, `*.sqlite-wal`, `*.sqlite-shm` e `*.tmp`.
8. Criar `vulture_whitelist.py` com os falsos positivos das seções 1.1 e 1.2 (`kwargs`/`max_age_days` dos dublês, `row_factory`, campos de dataclass, `with_warning`, `ETF`/`BDR`), cada um com o motivo em comentário.
9. Reexecutar vulture, ruff e deptry e atualizar este inventário.

Nada acima toca `valuation_engine.py`, `fii_engine.py`, `portfolio_engine.py`, nem as seções `MacroContext` e `_normalizar_dy`. Os itens 3 e 4 estão em `config.py`/`auditar_recomendacoes.py` fora dessas seções.
