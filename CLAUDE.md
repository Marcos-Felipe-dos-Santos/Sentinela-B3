# Sentinela B3

Plataforma educacional de análise de ações e FIIs da B3.
Python + Streamlit (V1; interface FastAPI + HTMX prevista para a Fase 7), local-first, SQLite.
**Não é consultoria financeira.**

> Fonte primária para Claude Code. `AGENTS.md` é a versão para agentes externos
> (Jules) e é subconjunto deste arquivo — os dois nunca podem se contradizer.
> Roteiro: `docs/PLANO.md`. Decisões: `docs/adr/` (0001 e 0002).
> Auditoria red team de 9/9/2026: `docs/auditoria/2026-09-red-team.md` (IDs normalizados no F0-0).
> Execução em loop: `docs/loop/protocolo.md` e `docs/loop/fila.md`.

---

## Ambiente

- WSL2 (Ubuntu). Repositório em `~/projetos/Sentinela_B3`, nunca em `/mnt/*`.
- Python 3.13, venv em `venv/` (criada com `uv venv --python 3.13 --seed venv`).
- Ative a venv antes de abrir o Claude Code: `source venv/bin/activate`.
- O loop roda dentro do tmux, em modo auto: `claude --permission-mode auto`.

---

## Comandos

```bash
streamlit run app.py                               # app (V1)
python -m pytest tests/ -x --tb=short              # suíte (~655 testes, 44 módulos, ~5 s)
python -m pytest tests/test_x.py::test_y -v        # teste único
python -m pytest tests/ --cov=. --cov-report=term-missing
python -m mutmut run "technical_engine*"           # mutação de um módulo (config em [tool.mutmut])
python -m mutmut export-cicd-stats                 # mortos e sobreviventes, para o mutation score
ruff check .
ruff format <arquivos alterados>                   # nunca no repositório inteiro
python -m vulture . vulture_whitelist.py --min-confidence 80 --exclude "venv,mutants,outputs,$PWD/data/*"   # código morto
deptry .                                           # dependências sem uso ou faltando
```

O mutmut 3 só roda em Linux (WSL) e só muta código dentro de funções.
A lista de exceções do vulture (`vulture_whitelist.py`) traz o motivo de cada exceção.

---

## Arquitetura real (V1 — o que roda hoje)

| Módulo | Linhas | Papel |
|---|---|---|
| `app.py` | 554 | Streamlit, 4 abas, orquestração real. **Cobertura 0%** |
| `market_engine.py` | 690 | Cascata de coleta e merge de fontes |
| `valuation_engine.py` | 341 | Orquestra os métodos de `sentinela/methods/` (Graham, Bazin, Lynch, Gordon), score, classificação (na V1, "recomendação") |
| `fii_engine.py` | 199 | Valuation de FII: orquestra `fii_yield` e `fii_nav`, score |
| `config.py` | 314 | Constantes, `MacroContext`, `_normalizar_dy` |
| `data_quality.py` | 236 | Completude, badge, `validacao_cruzada` (linha 170) |
| `database.py` | 217 | SQLite WAL, queries parametrizadas |
| `portfolio_engine.py` | 145 | Markowitz / máximo Sharpe |
| `technical_engine.py` | 103 | RSI, MACD, Bollinger, ATR, MAs |
| `peers_engine.py` | 96 | Comparação setorial (mapa hardcoded, ~40 tickers) |
| `ai_core.py` | 188 | LLM: Groq → Gemini → Ollama |
| `auditoria.py` | 933 | Sanidade runtime. **Não é suíte de testes. Cobertura 0%** |
| `auditar_recomendacoes.py` | 398 | Validação contra tickers conhecidos |
| `limpar_banco.py` | 196 | Manutenção do SQLite. Cobertura 0% |

**Provedores:** `cvm_provider.py`, `cvm_fii_provider.py`, `brapi_provider.py`,
`fundamentus_scraper.py`, `cvm_ticker_map.py`, `cvm_fii_map.py`

**Camada nova (`sentinela/`).** Já usados pela V1: `sentinela/methods/` (`base.py` e os seis
métodos) e `domain/units.py`, chamados por `valuation_engine.py` e `fii_engine.py`
(extraídos na Fase 1, comportamento da V1); `services/asset_classifier.py` (`app.py`,
`market_engine.py`, `portfolio_engine.py`, `auditar_recomendacoes.py`) e `domain/provenance.py`
e `enums.py` (`market_engine.py`, `valuation_engine.py`). `sentinela/reports/rastreabilidade.py`
roda por linha de comando (`python -m`), fora do app. **NÃO conectados** (só os testes
importam): `methods/registry.py`, `domain/models.py` (usado por `services/analyze_asset.py` e
`repositories/`), `services/analyze_asset.py` (`AnalysisService.analyze` duplica
`app.py:208-244`) e `repositories/`. Não adicione a mesma feature nas duas camadas.

**`backtesting/`** — gate temporal de preço correto, fundamentos de entrada sintéticos.

---

## Fluxo de dados real

`market_engine.buscar_dados_ticker:327-341` — **não** é a ordem do README:

```
1. yfinance   → preco_atual, historico, _shares_outstanding, fundamentos base
2. brapi      → sobrescreve fundamentos; só preenche preço se yfinance falhou
3. CVM        → sobrescreve fundamentos; deriva lpa/vpa/pl/pvp (linhas 501-518)
4. Fundamentus→ só preenche lacunas
5. cache SQLite (7d) → fallback manual FII
```

Fundamentos: CVM > brapi > yfinance > Fundamentus.
Preço: yfinance > brapi, sempre fechamento **D-1**.

---

## Regras econômicas vigentes

- Selic via BCB SGS 432, cache 24h, fallback hardcoded
- Bazin exige `dy >= 0.05`; FII compara com `Selic × 0.85`; fair value é **mediana**
- Métodos divergindo > 2x → flag de risco, confiança reduzida
- `_normalizar_dy` (`config.py:308`): `>1` → percentual; `>0.25` → inválido (devolve `(0.0, False)`: DY zerado e não confiável)
- Vocabulário: "classificação", "sinal positivo", "classificação heurística". Nunca "recomendação", "compra" ou "venda" em código novo, tabela, coluna ou tela. A V1 ainda exibe COMPRA/NEUTRO/VENDA; a troca é o F2C-4
- Nunca "alocação sugerida" nem qualquer sugestão de carteira: a V2 descreve risco, não recomenda alocação
- **Alvo (D15, Fase 2B):** taxa de desconto real (NTN-B longa + prêmio, via `cost_of_equity_real`), com k e g no mesmo regime. A Selic deixa de ser taxa de desconto

---

## Armadilhas conhecidas

Erros que **passam nos testes** e produzem resultado errado. Leia antes de tocar em valuation.

**1. Real vs nominal no Gordon** (`sentinela/methods/gordon.py`)
`cost_of_equity_real()` devolve taxa real; `g = ROE × retenção` é nominal.
Trocar Selic por NTN-B sem converter os dois derruba `k − g` de ~13,75% para ~6%
e mais que dobra todos os fair values. Escolha um regime, converta tudo.

**2. Validação cruzada tautológica** (`data_quality.py:170`)
Compara `pl` com `preco/lpa`, mas `market_engine.py:512` **define** `pl = preco/lpa`.
Divergência sempre zero. Ajustar o limiar não resolve.

**3. LPA/VPA sem reconciliação** (`market_engine.py:501-518`)
Lucro consolidado da CVM ÷ `sharesOutstanding` do yfinance, sem checar escopo de
classe. Para dual-class o erro pode ser fator ~2, e sai com badge 🟢.

**4. Três normalizadores de DY** (`config.py:308`, `market_engine.py:377-378`, `brapi_provider.py:35`)
Regras incompatíveis em cascata. 30% pode virar 0,3% sem alerta. Não crie um quarto.

**5. Colapso metodológico**
Bazin, Gordon e FII reduzem a `DY ÷ taxa` com o preço cancelando. Antes de
"corrigir" qualquer um: gerar a matriz de sensibilidade Selic × fair value.

**6. Backtest com dados fabricados**
`fundamentos_point_in_time.csv` são 15 linhas inventadas, retro-estimadas de dados
atuais. `backtest_results_v1.csv` veio de versão anterior do engine. Não é evidência.

**7. Suíte verde não é sinal**
`app.py`, `auditoria.py`, `limpar_banco.py` em 0%. `adicionar_posicao` sem teste;
`_limpar_valor` tem teste, mas fraco (`test_fundamentus_scraper.py:24` aceita `None` ou qualquer float).
`tests/conftest.py` só mocka a Selic: semeia o BCB (14,75%, igual ao fallback) durante o import de
`config` — contorno do E-6, não correção — e bloqueia `socket.connect`, falhando o teste e a sessão
que tentarem rede. Fora isso ajusta `sys.path` e `basetemp` no Windows. 27 dos 44 módulos não usam mock.

**8. `config.py:305` faz rede no import**
`MACRO = MacroContext()` chama a API do BCB ao importar. Em CI ou daemon isso vira
chamada externa a cada execução, e a Selic fica congelada pelo tempo do processo.
A suíte contorna isso com a semente do `tests/conftest.py`; a correção (E-6) é anterior ao monitoramento contínuo.

**9. Integrações inertes**
`CVMFIIProvider` nunca injetado (`app.py:158`). `cloudscraper` fora do requirements.
`baixar_itr`, `cost_of_equity_real`, `ntnb_longa`, `cdi`, `ipca_12m` sem consumidor
fora dos testes (`ntnb_longa` só é lido por `cost_of_equity_real`).

**10. Escala da quantidade de ações na CVM**
A seção Composição do Capital da DFP/ITR informa a quantidade na escala escolhida
no documento (mil ou unidade). Converta sempre pelo `units.py`; nunca assuma.

**11. Preço bruto × ajustado**
Múltiplo numa data usa o preço bruto daquela data e as ações do mesmo documento do
lucro. Retorno usa série ajustada. Um desdobramento entre a demonstração e o preço
erra o LPA por fator inteiro — a mesma família do item 3.

**12. `tecnico_negativo` — resolvida (F1-11)**
O `valuation_engine` lia a chave, que nenhum código de produção escrevia: caminho morto,
e contrário ao isolamento (métodos não leem sinal técnico). A leitura saiu; um teste
(`test_sinal_tecnico_nao_altera_resultado`) garante que o sinal não altera o resultado.

**13. Limites do mutmut 3**
Só muta código dentro de funções: constantes de módulo (como as de `config.py`)
ficam fora do score. Com `xfail_strict` ligado, um XPASS acidental conta como
mutante morto — por isso o `[tool.mutmut]` desliga o `xfail_strict` só na mutação.

**14. Classe do ativo deduzida do ticker**
ETFs viram FIIs e BDRs viram ações comuns. Units, que também terminam em 11, correm
o mesmo risco. Classe vem de dado oficial (F2A-1), nunca do sufixo.

**15. Cobertura dos mapas manuais**
Só 45 ações (mapa regenerado do cadastro oficial da CVM no F1-15) e 30 FIIs estão mapeados; fora deles, os fundamentos vêm do
fallback. A classe que atualizaria o mapa (`CVMTickerMap`) só é instanciada nos testes,
e o `refresh` grava `cd_cvm`/CNPJ sem nunca preencher `ticker`; a leitura de coluna
inexistente citada na auditoria não foi verificada (exige rede).
Segmento do FII e controle acionário estão em arquivos da CVM já baixados e não lidos.

**16. Markowitz com um ano de dados**
Retorno esperado estimado com um ano de pregões (erro-padrão enorme), divisão fixa
de 40% FIIs e 60% ações, e saída chamada "Alocação Sugerida". Não é evidência e não
pode aparecer como sugestão (quarentena no F0-9; aposentado no F2C-9).

**17. Bancos sem regra própria**
Métodos de empresa não financeira aplicados a bancos. Alavancagem medida pelo
endividamento contábil total, que num banco não significa o mesmo que numa empresa
comum. Bancos terão lente própria (F2B-3).

---

## Estrutura-alvo

Detalhe em `docs/PLANO.md`, seção 4.

```
sentinela/
  domain/     units.py  models.py  provenance.py  enums.py  tempo.py
  methods/    base.py (ValuationMethod, MethodInputs congelado com as_of,
              MethodResult | Abstention, applies_to)
              graham.py  bazin.py  lynch.py  gordon.py  fii_yield.py  fii_nav.py
              bancos.py  qualidade.py  registry.py
  data/       providers/  referencia/  pit/  store/ (SQLite único + migrations/)
  services/   AnalysisService.analisar(ticker, as_of)
  risk/       concentração, volatilidade, correlação, sensibilidade a juros
  jobs/  reports/  news/  cli.py  api/  web/
```

**Contrato de isolamento:** `sentinela/methods/` não importa `sentinela/news/`,
`technical_engine` nem `sentinela/data/`, e não faz rede, banco ou leitura de
relógio. Garantido por teste no grafo de import (F1-10), não por disciplina.

**Contrato de método:** cada método declara `version`, `regime` (REAL|NOMINAL|SEM_TAXA),
`requires`, `assumptions` e `applies_to`, e devolve `MethodResult | Abstention`.
Sem insumo, abstém-se — não devolve número conservador.

---

## Fases

0. **Preparação** — concluída (tag `v2-fase-0`)
1. **Fundação** — em execução (`docs/loop/fila.md`): `units.py`, contrato de método e extração de `methods/`, comportamento idêntico, golden dos motores
2. **2A Dados corretos** (dados de referência, E-1, DY único, E-2, cinco anos, dívida líquida, bancos, liquidez), **2B Taxa real, bancos e escopo** e **2C Qualidade e apresentação** (normalização, lente de qualidade, histerese, vocabulário, lentes, fim do Markowitz)
3. **Tempo como entrada** — E-6, E-14, ponto-no-tempo, `analisar(ticker, as_of)`, backtest real
4. **Operação diária, rastreabilidade e risco da carteira**
5. **Notícias medidas** — coletor do IPE e estudo de evento
6. **Vitrine** — fecha o núcleo de portfólio
7. **Interface FastAPI + HTMX**
8. **IA nas telas e notícias 2–4** (condicional)

Regra dura: **refactor e mudança de comportamento nunca no mesmo commit.**
As Fases 3 a 8 dependem das propostas D5–D13 do ADR-0002.

---

## Execução em loop

- Um branch por fase (`v2/fase-N`), um commit por item, diário em `docs/loop/diario.md`.
- **O loop nunca faz push nem abre PR.** O push é do Marcos, no checkpoint `[DECISÃO]`.
- Não pergunte durante o loop: dúvida que muda o resultado vira `[!]` e parada.
- Item com definição de "correto" em aberto só entra na fila com a decisão escrita nele.
- Toda fila termina com limpeza e resumo. O resumo arquiva a fase em `docs/loop/historico/`.
- Itens de limpeza removem arquivo rastreado com `git rm`, recuperável pelo histórico.
  O loop nunca apaga arquivo não rastreado nem branch.
- Nenhum item acrescenta código comentado, import sem uso, print de depuração,
  arquivo temporário ou TODO sem item na fila.

---

## Divisão com o Jules

O Jules nunca escreve código cujo comportamento correto ainda está sendo decidido.

| Frente | Jules |
|---|---|
| Revisão de PR de fase | sim |
| Testes com spec externa | escreve; gate = mutation score |
| Coletor do IPE (F5-1) | código + teste |
| Fila mecânica (infra) | código + teste de regressão, fora dos arquivos travados |
| `methods/`, valuation, FastAPI | nunca |

Arquivos travados por fase: `docs/PLANO.md`, seção 8.

---

## Testes

- Correção: teste xfail provando o bug → implementação → XPASS.
- Refactor: nenhum teste existente muda; as seções A, B e C de
  `tests/test_financeiro_pre_refactor.py` e o golden dos motores
  (`tests/test_equivalencia_motores.py`, grade em `tests/fixtures/golden_motores.jsonl`) são o juiz.
- Depois: `/review-diff` → `/safe-commit` (sem push) → checkpoint da fase → push manual.
- `xfail_strict = true` é obrigatório, senão XPASS não falha e o gate é fictício.
- Antipadrão recorrente: teste que asserta sem verificar. Valide por mutação.

---

## Segurança

- SQL sempre parametrizado com `?`
- Nunca ler, modificar ou commitar `.env`
- Nunca `git push` sem aprovação explícita — no loop, há deny para isso
- Não remover ou enfraquecer testes para passar
- Ticker não é validado: entra em URL (`fundamentus_scraper.py:99`) e em prompt
  de LLM (`ai_core.py:122`) sem sanitização (correção: F2A-12)
- **O repositório é público.** Dados da carteira do Marcos (posições, pesos, lista
  de ativos) nunca entram em arquivo versionado — nem em docs, testes, fixtures ou
  diário. Análises que usam a carteira vão para `outputs/`, que o git ignora
- Texto de notícia e de LLM é dado não confiável: nunca vira instrução no prompt,
  nunca passa por `|safe` no template
- Interface web só em `127.0.0.1`, com autoescape e CSRF nas escritas
- Env: `GROQ_API_KEY`, `GEMINI_API_KEY`, `BRAPI_TOKEN`
  (o último lido em `brapi_provider.py:72`; segundo o levantamento, ausente do `.env.example` — não verificado pelo loop)
- Assinatura Google AI Pro **não** é cota da API Gemini — verificar antes de
  desenhar features de IA em cima do `ai_core`

---

## Git

- Conventional Commits em inglês, imperativo: `feat:` `fix:` `test:` `docs:` `refactor:` `chore:`
- Um commit por item da fila; um branch por fase
- Depois do merge, o branch da fase é apagado e a fase ganha a tag `v2-fase-N`
- Nunca commitar `.env`, `__pycache__`, `*.db`, `outputs/`, `venv/`, `mutants/`
