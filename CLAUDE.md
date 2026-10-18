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
python -m pytest tests/ -x --tb=short              # suíte (~1.360 testes, 76 módulos, ~8 s)
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
| `market_engine.py` | 1.105 | Cascata de coleta e merge de fontes; a lógica de dado nova fica em `sentinela/data/` |
| `valuation_engine.py` | 363 | Orquestra os métodos de `sentinela/methods/` (Graham, Bazin, Lynch, Gordon), score, classificação (na V1, "recomendação"); abstém-se para ETF, BDR e `UNKNOWN` quando `dados['classe_ativo']` existe |
| `fii_engine.py` | 157 | Valuation de FII: orquestra `fii_yield` e `fii_nav`, score |
| `config.py` | 318 | Constantes, `MacroContext`, `_normalizar_dy` (invariante do DY) |
| `data_quality.py` | 302 | Completude, badge, `validacao_cruzada` (linha 182) |
| `database.py` | 217 | SQLite WAL, queries parametrizadas |
| `portfolio_engine.py` | 145 | Markowitz / máximo Sharpe |
| `technical_engine.py` | 104 | RSI, MACD, Bollinger, ATR, MAs |
| `peers_engine.py` | 96 | Comparação setorial (mapa hardcoded, ~40 tickers) |
| `ai_core.py` | 200 | LLM: Groq → Gemini → Ollama |
| `auditoria.py` | 924 | Sanidade runtime. **Não é suíte de testes. Cobertura 0%** |
| `auditar_recomendacoes.py` | 398 | Validação contra tickers conhecidos |
| `limpar_banco.py` | 196 | Manutenção do SQLite. Cobertura 0% |

**Provedores:** `cvm_provider.py`, `cvm_fii_provider.py`, `brapi_provider.py`. O Fundamentus
saiu no F2A-22. `cvm_ticker_map.py` e `cvm_fii_map.py` não são mais lidos pela cascata
(F2A-31); no F2A-13 ficaram só os dicionários, lidos por `scripts/levantamento_fase2a.py`,
`scripts/dossie_fase2.py` e o índice falso de `tests/test_market_engine.py`.

**Camada de dados (`sentinela/data/`, Fase 2A).** Funções puras chamadas pela cascata e pelos
provedores: `referencia/` (índice oficial ticker ↔ CNPJ ↔ CD_CVM ↔ classe, com setor, segmento
e controle; `carga.py` o mantém em memória), `contas_cvm.py` (contas por código e descrição,
tabela `referencia/contas_cvm.csv`), `controladores.py` (lucro e PL dos controladores, com as
reservas da D20), `acoes_cvm.py` (ações, escala, LPA divulgado e recalculado, VPA),
`series_cvm.py` (cinco exercícios e TTM), `divida_liquida.py`, `normalizacao.py` (DY e ROE na
fronteira), `liquidez.py`, `proveniencia.py`; `providers/b3_cotahist.py` e `providers/ifdata.py`.
`domain/ticker.py` valida o ticker (lista permitida).

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

`market_engine.buscar_dados_ticker:419-481` — **não** é a ordem do README. Ticker fora do
formato da B3 devolve `None` antes de qualquer fonte (F2A-12).

```
0. índice oficial → classe_ativo, especie, cnpj, cd_cvm, setor... (sem índice: a CVM não é consultada)
1. yfinance       → preco_atual, historico, _shares_outstanding, fundamentos base (DY e ROE pela fronteira)
2. brapi          → sobrescreve fundamentos; só preenche preço se yfinance falhou
3. CVM            → só pelo cd_cvm do índice; sobrescreve fundamentos; série de cinco anos e TTM;
                    LPA, VPA, P/L e P/VP pela Composição do Capital e pelo LPA divulgado (_por_acao_cvm)
   (sem preço, a cascata para aqui)
4. IF.data        → Basileia do banco
5. CVM de FII     → VPA e P/VP oficiais pelo Informe Mensal
6. liquidez       → COTAHIST, fora do prompt
7. cache SQLite (7d) → fundamentos_incompletos (campo obrigatório faltando depois de todas as fontes)
```

Fundamentos: CVM > brapi > yfinance. A alavancagem (`divida_liq_ebitda`) vem só da CVM.
Preço: yfinance > brapi, sempre fechamento **D-1**.

---

## Regras econômicas vigentes

- Selic via BCB SGS 432, cache 24h, fallback hardcoded
- Bazin exige `dy >= 0.05`; FII compara com `Selic × 0.85`; fair value é **mediana**
- Métodos divergindo > 2x → flag de risco, confiança reduzida
- DY e ROE são convertidos uma vez, na fronteira do provedor (`sentinela/data/normalizacao.py`): yfinance com DY em percentual e ROE em razão (F2A-16); brapi pela regra da V1 (acima de 1 é percentual), declarada como inferência na proveniência. ROE não finito ou acima de 2 é descartado, com o motivo
- `_normalizar_dy` (`config.py:308`) é só o invariante dos motores: fora de 0 ≤ DY ≤ 0,25, ou não finito, devolve `(0.0, False)`
- LPA, VPA e ROE pelos controladores: lucro e PL atribuídos aos controladores, com as reservas da D20 (F2A-37); o LPA dos métodos é o divulgado da classe do ticker (D19, F2A-36), e o recalculado (ações da Composição do Capital do mesmo documento) é conferência e reserva
- Alavancagem: dívida financeira líquida (2.01.04 + 2.02.01 − 1.01.01 − 1.01.02, regime pós-IFRS 16, arrendamento incluído) ÷ EBITDA (EBIT + D&A da DVA) e ÷ PL; banco e seguradora não recebem a medida (F2A-8)
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

**2. Validação cruzada tautológica — resolvida na CVM de ações (F2A-5)** (`data_quality.py:182`)
O P/L da CVM é `preço ÷ LPA` (`market_engine.py:963`), então compará-lo com `preço ÷ LPA` dá zero.
Os checks 2 e 3 só rodam com fontes diferentes (`_mesma_fonte`), e o LPA é comparado com o
divulgado e as ações com o yfinance. Ainda vale para FII: o P/VP da CVM é `preço ÷ VPA` e não
grava `valores_por_fonte['CVM']`, então o check 3 roda e nunca alerta (F2A-11).

**3. LPA/VPA sem reconciliação — resolvida (F2A-3, F2A-36, F2A-37)** (`market_engine._por_acao_cvm`)
Era lucro consolidado da CVM ÷ `sharesOutstanding` do yfinance. Agora: lucro e PL dos
controladores ÷ ações da Composição do Capital do mesmo documento, LPA divulgado por classe
nos métodos, e o `sharesOutstanding` só na divergência (`dados['divergencia_acoes']`).

**4. Três normalizadores de DY — resolvida (F2A-4)**
A conversão é uma só, em `sentinela/data/normalizacao.py`; `config._normalizar_dy` é o invariante
dos motores. Não crie outra conversão de percentual fora dela.

**5. Colapso metodológico**
Bazin, Gordon e FII reduzem a `DY ÷ taxa` com o preço cancelando. Antes de
"corrigir" qualquer um: gerar a matriz de sensibilidade Selic × fair value.

**6. Backtest com dados fabricados**
`fundamentos_point_in_time.csv` são 15 linhas inventadas, retro-estimadas de dados
atuais. `backtest_results_v1.csv` veio de versão anterior do engine. Não é evidência.

**7. Suíte verde não é sinal**
`app.py`, `auditoria.py`, `limpar_banco.py` em 0%. `adicionar_posicao` tem teste (`tests/test_database_posicoes.py`).
`tests/conftest.py` só mocka a Selic: semeia o BCB (14,75%, igual ao fallback) durante o import de
`config` — contorno do E-6, não correção — e bloqueia `socket.connect`, falhando o teste e a sessão
que tentarem rede. Fora isso ajusta `sys.path` e `basetemp` no Windows. 33 dos 76 módulos não usam mock.

**8. `config.py:305` faz rede no import**
`MACRO = MacroContext()` chama a API do BCB ao importar. Em CI ou daemon isso vira
chamada externa a cada execução, e a Selic fica congelada pelo tempo do processo.
A suíte contorna isso com a semente do `tests/conftest.py`; a correção (E-6) é anterior ao monitoramento contínuo.

**9. Integrações inertes**
`cost_of_equity_real`, `ntnb_longa`, `cdi`, `ipca_12m` sem consumidor fora dos testes
(`ntnb_longa` só é lido por `cost_of_equity_real`). Resolvidas na 2A: o `CVMFIIProvider` roda
pela cascata (F2A-11), e o motor de FII perdeu o caminho de provedor próprio (F2A-13); o
`baixar_itr` alimenta o TTM (F2A-7); o `cloudscraper` saiu com o scraper (F2A-22).

**10. Escala da quantidade de ações na CVM**
A seção Composição do Capital da DFP/ITR informa a quantidade na escala escolhida
no documento (mil ou unidade), sem dizer qual. A escala é inferida pelo LPA divulgado do mesmo
documento, na faixa [0,1; 10] (`acoes_cvm.inferir_escala`, F2A-3), e a conversão passa por
`Escala` e `QuantidadeAcoes` do `units.py`. Indeterminada, abstém-se; nunca assuma.

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

**14. Classe do ativo deduzida do ticker — resolvida no índice (F2A-1, F2A-20, F2A-29)**
Para ticker do índice oficial, a classe vem dele (`dados['classe_ativo']`), nunca do sufixo, e
ETF, BDR e `UNKNOWN` não recebem os métodos de ação (`valuation_engine.py:125`). Fora do índice,
`classe_ativo` não é gravado: o classificador cai no fallback (`FIIS_CONHECIDOS`,
`UNITS_CONHECIDAS`; final 11 vira `UNKNOWN`, o resto `STOCK`), e o guard do motor não atua.

**15. Cobertura dos mapas manuais — resolvida (F2A-1, F2A-2, F2A-31)**
O índice oficial cobre todos os pares (CNPJ, código) no formato do FCA e os FIIs do Informe e do
COTAHIST; a cascata lê só ele, e sem índice local a CVM não é consultada. Setor, segmento do
FII e controle acionário vêm do índice. O mapa com cache SQLite saiu no F2A-13; dos mapas manuais
ficaram só os dicionários, sem leitor na cascata.

**16. Markowitz com um ano de dados**
Retorno esperado estimado com um ano de pregões (erro-padrão enorme), divisão fixa
de 40% FIIs e 60% ações, e saída chamada "Alocação Sugerida". Não é evidência e não
pode aparecer como sugestão (quarentena no F0-9; aposentado no F2C-9).

**17. Bancos sem regra própria**
Métodos de empresa não financeira ainda são aplicados a bancos. Na 2A: PL, lucro e ROE pelo
modelo de instituição financeira (F2A-9); receita, margem e alavancagem não são preenchidas
para banco; Basileia do IF.data (inadimplência sem fonte). Com o VPA da CVM, o Graham dos bancos
passou a usá-lo. Bancos terão lente própria (F2B-3).

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
1. **Fundação** — concluída (tag `v2-fase-1`): `units.py`, contrato de método e extração de `methods/`, comportamento idêntico, golden dos motores
2. **2A Dados corretos** — em execução (`docs/loop/fila.md`, branch `v2/fase-2a`; dados de referência, E-1, DY único, E-2, cinco anos, dívida líquida, bancos, medida de liquidez), **2B Taxa real, bancos e escopo** e **2C Qualidade e apresentação** (normalização, lente de qualidade, histerese, vocabulário, lentes, fim do Markowitz)
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
- Ticker validado por lista permitida (`sentinela/domain/ticker.py`, F2A-12) antes do yfinance
  e da brapi (cascata e `brapi_provider._primeiro_resultado`) e do prompt (`SentinelaAI.analisar`)
- **O repositório é público.** Dados da carteira do Marcos (posições, pesos, lista
  de ativos) nunca entram em arquivo versionado — nem em docs, testes, fixtures ou
  diário. Análises que usam a carteira vão para `outputs/`, que o git ignora
- Texto de notícia e de LLM é dado não confiável: nunca vira instrução no prompt,
  nunca passa por `|safe` no template
- Interface web só em `127.0.0.1`, com autoescape e CSRF nas escritas
- Env: `GROQ_API_KEY`, `GEMINI_API_KEY`, `BRAPI_TOKEN`
  (o último lido em `brapi_provider.py:64`; segundo o levantamento, ausente do `.env.example` — não verificado pelo loop)
- Assinatura Google AI Pro **não** é cota da API Gemini — verificar antes de
  desenhar features de IA em cima do `ai_core`

---

## Git

- Conventional Commits em inglês, imperativo: `feat:` `fix:` `test:` `docs:` `refactor:` `chore:`
- Um commit por item da fila; um branch por fase
- Depois do merge, o branch da fase é apagado e a fase ganha a tag `v2-fase-N`
- Nunca commitar `.env`, `__pycache__`, `*.db`, `outputs/`, `venv/`, `mutants/`

<!-- multiagente 14/10/2026 -->
## Multiagente

Ver a seção "Multiagente" do `AGENTS.md` e `docs/loop/workflow-multiagente.md`. Ao retomar trabalho começado por outro agente ou noutra sessão, use a skill `retomar` antes de editar. Ao parar com item pela metade, use `passagem`. A ordem das etapas de uma fase e os comandos de auditoria estão em `docs/loop/ciclo-de-fase.md`.
