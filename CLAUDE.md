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
python -m pytest tests/ -x --tb=short              # suíte (2.568 passed, 1 skipped, 14 xfailed; ~10 s)
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
| `market_engine.py` | 1.474 | Cascata de coleta e merge de fontes; a lógica de dado nova fica em `sentinela/data/` |
| `valuation_engine.py` | 588 | Orquestra os métodos de `sentinela/methods/` (Graham, Bazin, Lynch, Gordon; para banco, a lente `Bancos`), score, classificação (na V1, "recomendação"); só STOCK e UNIT seguem, com a classe exigida, e só modelo empresa ou banco pelo BPP consolidado (`dados['modelo_bpp']`, F2B-4); o resto se abstém sem número |
| `fii_engine.py` | 190 | Valuation de FII: orquestra `fii_yield` e `fii_nav`, score; a lente abstida não traz valor nem upside (F2B-62) |
| `config.py` | 342 | Constantes, `MacroContext`, `_normalizar_dy` (invariante do DY) |
| `data_quality.py` | 347 | Completude (pelo `modelo_bpp`, F2B-63), badge, `validacao_cruzada` (linha 203) |
| `database.py` | 217 | SQLite WAL, queries parametrizadas |
| `portfolio_engine.py` | 145 | Markowitz / máximo Sharpe |
| `technical_engine.py` | 104 | RSI, MACD, Bollinger, ATR, MAs |
| `peers_engine.py` | 96 | Comparação setorial (mapa hardcoded, ~40 tickers) |
| `ai_core.py` | 206 | LLM: Groq → Gemini → Ollama |
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
Na 2B entraram `taxas.py` (cesta real), `providers/tesouro.py` (CSV oficial),
`providers/macro.py` (Tesouro, IPCA IBGE e PIB Focus), `gordon_cvm.py` (DVA e base acionária),
`proventos_b3.py` e `providers/b3_proventos.py` (eventos por data ex), `rendimento_fii.py`
e `providers/b3_fundos.py` (Informe e eventos de cota; corte temporal da taxa e das coletas,
F2B-58). `gordon_cvm.entradas(..., modelo="banco")` alimenta a lente de bancos (F2B-32), e o
IF.data lê também a inadimplência do relatório 16, só para leitura.
`domain/ticker.py` valida o ticker (lista permitida).

**Camada nova (`sentinela/`).** Já usados pela V1: `sentinela/methods/` (`base.py` e seis
métodos nos motores, mais `bancos.py`, a lente de bancos do motor de ações desde o F2B-32) e `domain/units.py`, chamados por `valuation_engine.py` e `fii_engine.py`
(extraídos na Fase 1 e atualizados nas Fases 2A/2B); `services/asset_classifier.py` (`app.py`,
`market_engine.py`, `portfolio_engine.py`, `auditar_recomendacoes.py`) e `domain/provenance.py`
e `enums.py` (`market_engine.py`, `valuation_engine.py`). `sentinela/reports/rastreabilidade.py`
roda por linha de comando (`python -m`), fora do app. **NÃO conectados** (só os testes
importam): `methods/registry.py`, `domain/models.py` (usado por `services/analyze_asset.py` e
`repositories/`), `services/analyze_asset.py` (`AnalysisService.analyze` é outra orquestração) e `repositories/`. Não adicione a mesma feature nas duas camadas.

**`backtesting/`** — gate temporal de preço correto, fundamentos de entrada sintéticos.

---

## Fluxo de dados real

`market_engine.buscar_dados_ticker:441-513` — **não** é a ordem do README. Ticker fora do
formato da B3 devolve `None` antes de qualquer fonte (F2A-12).

```
0. índice oficial → classe_ativo, especie, cnpj, cd_cvm, setor... (sem índice: a CVM não é consultada)
1. yfinance       → preco_atual, historico, _shares_outstanding, fundamentos base (DY e ROE pela fronteira)
2. brapi          → sobrescreve fundamentos; só preenche preço se yfinance falhou
3. CVM            → só pelo cd_cvm do índice; sobrescreve fundamentos; série de cinco anos e TTM;
                    LPA, VPA, P/L e P/VP pela Composição do Capital e pelo LPA divulgado (_por_acao_cvm)
   (sem preço, a cascata para aqui)
4. IF.data        → Basileia (contexto) e inadimplência do relatório 16 (só leitura) do banco
5. CVM de FII     → VPA e P/VP oficiais; histórico de rendimento pelo Informe e eventos B3
6. proventos B3   → dividendos/JCP brutos por data ex e eventos em ações; perfil e Bazin
7. liquidez       → COTAHIST, fora do prompt
8. taxa real      → cesta Tesouro + prêmio; IPCA da janela contábil e teto PIB Focus
9. cache SQLite (7d) → fundamentos_incompletos (campo obrigatório faltando depois de todas as fontes)
```

Fundamentos: CVM > brapi > yfinance. A alavancagem (`divida_liq_ebitda`) vem só da CVM.
Preço: yfinance > brapi, sempre fechamento **D-1**.

---

## Regras econômicas vigentes

- Selic via BCB SGS 432, cache 24h, fallback hardcoded
- Bazin 2.0.0 exige DY bruto de 12 meses da B3 ≥ 5% e perfil renda; preço-limite = proventos brutos ÷ 6% fixos, critério nominal independente da Selic. Série completa sem provento conta como DY zero, exigindo registro da espécie; sem evidência, abstém
- Perfil único usa DY da B3 quando válido; sem ele, DY da cascata com aviso. Crescimento exige ROE > 20% e DY confiável < 4%; Lynch ainda usa payout pelo DY da cascata (pendência 2C)
- Gordon 2.0.0 usa D0/payout DVA dos controladores, ROE nominal sobre PL inicial, Fisher e teto PIB real; exige evidência de compatibilidade da base acionária com o preço. Sem essa prova, abstém
- FII 2.0.0, só tijolo elegível: rendimento de 12 meses por cota do Informe ÷ (NTN-B real + spread de 0,03505842448151178), crescimento real zero. Elegibilidade e eventos de cota são conferidos na fronteira; Selic líquida permanece no score/contexto, P/VP como lente de contexto
- Ações agregam valores dos métodos pela **mediana**. Escopo (F2B-4): classe oficial exigida; STOCK/UNIT exigem o modelo do BPP consolidado, com evidência até o as_of: empresa recebe Graham, Bazin, Lynch e Gordon; banco (PL só em 2.07/2.08; lido nos dois modelos, abstém; banco tem precedência sobre o teste de seguradora) recebe só a lente de bancos (F2B-32); seguradora (descrição com "Provisões Técnicas", "contrato(s) de seguro/resseguro" ou "Atividade Seguradora", critério de 25/10/2026) e sem BPP consolidado se abstêm sem número
- Bancos (F2B-32): P/VP justificado = (ROE real − g real)/(k real − g real) × VPA CVM do mesmo documento, DVA e PL inicial dos controladores; lente abstida sai sem número; companhia com mais de uma classe preferencial abstém a lente em todas as classes, inclusive a ON (BRSR3), pela fronteira `gordon_cvm.entradas` (decisão 2 de 25/10/2026; separação na 2C); inadimplência do IF.data (148834 ÷ 24454) só para leitura, em `inadimplencia_ifdata`; Basileia fora
- FII (ficha 1.3): conflito de mesma versão em qualquer campo, composição da versão selecionada, os 13 VPs, amortização vazia vale zero e `NaN` declarado abstém, taxa e coletas até o as_of; a lente abstida não traz valor nem upside (score 50, neutro)
- Avisos fora de `riscos` (F2B-45): dívida líquida/EBITDA que não é número finito não é avaliada e gera `aviso_alavancagem`; liquidez não medida gera `aviso_liquidez`; nenhum dos dois muda a classificação
- Liquidez: nos 63 pregões, presença ≥ 80% e volume mediano diário ≥ R$ 500 mil para ações/units ou R$ 100 mil para FII. Abaixo, abstém; dado ausente, cobertura incompleta ou falha de coleta geram aviso, sem converter ausência em volume zero
- Métodos divergindo > 2x → flag de risco, confiança reduzida
- DY e ROE são convertidos uma vez, na fronteira do provedor (`sentinela/data/normalizacao.py`): yfinance com DY em percentual e ROE em razão (F2A-16); brapi pela regra da V1 (acima de 1 é percentual), declarada como inferência na proveniência. ROE não finito ou fora de [−2; 2] é descartado, com o motivo
- `_normalizar_dy` (`config.py:332`) é só o invariante dos motores: fora de 0 ≤ DY ≤ 0,25, ou não finito, devolve `(0.0, False)`
- LPA, VPA e ROE pelos controladores: lucro e PL atribuídos aos controladores, com as reservas da D20 (F2A-37); o LPA dos métodos é o divulgado da classe do ticker (D19, F2A-36), e o recalculado (ações da Composição do Capital do mesmo documento) é conferência e reserva
- Alavancagem: dívida financeira líquida (2.01.04 + 2.02.01 − 1.01.01 − 1.01.02, regime pós-IFRS 16, arrendamento incluído) ÷ EBITDA (EBIT + D&A da DVA) e ÷ PL; banco e seguradora não recebem a medida (F2A-8)
- Vocabulário: "classificação", "sinal positivo", "classificação heurística". Nunca "recomendação", "compra" ou "venda" em código novo, tabela, coluna ou tela. A V1 ainda exibe COMPRA/NEUTRO/VENDA; a troca é o F2C-4
- Nunca "alocação sugerida" nem qualquer sugestão de carteira: a V2 descreve risco, não recomenda alocação
- **Taxa real vigente (D15):** média de pesos iguais das taxas de aplicação de NTN-B e NTN-B Principal com vencimento ≥ 2035, mais 5 pontos percentuais das ações, sem prêmio soberano adicional. `get_taxa_real` fornece registro/proveniência e `cost_of_equity_real` o custo ou None; ausência não usa contingência numérica. Gordon trabalha com k e g reais; FII usa a NTN-B sem o prêmio das ações. A Selic permanece em contexto/score e Markowitz

---

## Armadilhas conhecidas

Erros que **passam nos testes** e produzem resultado errado. Leia antes de tocar em valuation.

**1. Real vs nominal no Gordon — corrigida (F2B-1/F2B-54)**
`sentinela/methods/gordon.py` converte o crescimento nominal por Fisher antes de aplicar
o teto real PIB; D0 vem da DVA dos controladores, com reconciliação da base acionária.
Não trocar esse fluxo por DY agregado nem dispensar a prova de compatibilidade com o preço.

**2. Validação cruzada tautológica — corrigida em ações e FII (F2A-5/F2B-16)**
`data_quality.validacao_cruzada` evita comparar um múltiplo com a identidade que o gerou.
Para FII, `valores_por_fonte['CVM']` é registrado e o P/VP do Informe é comparado com os
valores independentes do yfinance/brapi (`_alertas_pvp_do_fii`), não com preço ÷ o mesmo VPA.

**3. LPA/VPA sem reconciliação — resolvida (F2A-3, F2A-36, F2A-37)** (`market_engine._por_acao_cvm`)
Era lucro consolidado da CVM ÷ `sharesOutstanding` do yfinance. Agora: lucro e PL dos
controladores ÷ ações da Composição do Capital do mesmo documento, LPA divulgado por classe
nos métodos, e o `sharesOutstanding` só na divergência (`dados['divergencia_acoes']`).

**4. Três normalizadores de DY — resolvida (F2A-4)**
A conversão é uma só, em `sentinela/data/normalizacao.py`; `config._normalizar_dy` é o invariante
dos motores. Não crie outra conversão de percentual fora dela.

**5. Dependência de fluxo e taxa — regras da 2B já implementadas**
Bazin é critério nominal fixo de 6%; Gordon usa DVA e taxa/crescimento reais;
FII usa rendimento do Informe e NTN-B + spread. O FII assume crescimento real zero.
Sensibilidade e limitações não desaparecem com a troca de taxa: consulte as fichas,
os diagnósticos e a evidência de cada insumo, sem inferir fluxo pelo DY agregado.

**6. Backtest com dados fabricados**
`fundamentos_point_in_time.csv` são 15 linhas inventadas, retro-estimadas de dados
atuais. `backtest_results_v1.csv` veio de versão anterior do engine. Não é evidência.

**7. Suíte verde não é sinal**
`app.py`, `auditoria.py`, `limpar_banco.py` em 0%. `adicionar_posicao` tem teste (`tests/test_database_posicoes.py`).
`tests/conftest.py` semeia Selic e taxa real: semeia o BCB (14,75%, igual ao fallback) durante o import de
`config` — contorno do E-6, não correção — e bloqueia `socket.connect`, falhando o teste e a sessão
que tentarem rede. A semente de taxa real substitui o carregador só nos testes; não existe contingência equivalente em produção. Também ajusta `sys.path` e `basetemp` no Windows.

**8. `config.py:329` faz rede no import**
`MACRO = MacroContext()` chama a API do BCB ao importar. Em CI ou daemon isso vira
chamada externa a cada execução, e a Selic fica congelada pelo tempo do processo.
A suíte contorna isso com a semente do `tests/conftest.py`; a correção (E-6) é anterior ao monitoramento contínuo.

**9. Integrações vigentes e resíduos**
`get_taxa_real` é chamado pela cascata; Gordon e FII consomem o registro. A antiga
propriedade `ntnb_longa` saiu no F2B-5; CDI/IPCA legados não são a fonte da nova taxa
real (F3-1). A lente `Bancos` é chamada pelo motor de ações para o modelo banco (F2B-32).
O motor de ações não lê mais a Selic (F2B-5); ela fica no score/contexto do FII e no Markowitz.
CVM de FII e ITR/TTM já estão ligados à cascata desde a 2A.

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
ETF, BDR e `UNKNOWN` não recebem os métodos de ação (`valuation_engine.py:201`). Fora do índice
(ou sem ele), a cascata grava a classe do classificador (F2A-43): fallback por `FIIS_CONHECIDOS` e
`UNITS_CONHECIDAS`; final 11 vira `UNKNOWN`, o resto `STOCK`. A guarda do motor atua nos dois casos.

**15. Cobertura dos mapas manuais — resolvida (F2A-1, F2A-2, F2A-31)**
O índice oficial cobre todos os pares (CNPJ, código) no formato do FCA e os FIIs do Informe e do
COTAHIST; a cascata lê só ele, e sem índice local a CVM não é consultada. Setor, segmento do
FII e controle acionário vêm do índice. O mapa com cache SQLite saiu no F2A-13; dos mapas manuais
ficaram só os dicionários, sem leitor na cascata.

**16. Markowitz com um ano de dados**
Retorno esperado estimado com um ano de pregões (erro-padrão enorme), divisão fixa
de 40% FIIs e 60% ações, e saída chamada "Alocação Sugerida". Não é evidência e não
pode aparecer como sugestão (quarentena no F0-9; aposentado no F2C-9).

**17. Bancos — lente ligada ao motor (F2B-3/F2B-4/F2B-32)**
`methods/bancos.py` calcula P/VP = (ROE real − g real)/(k real − g real), vezes VPA,
com DFP, DVA dos controladores e base acionária compatível; não faz rede nem coleta. O motor
a chama para o modelo banco pelo BPP consolidado, pela fronteira `gordon_cvm.entradas(...,
modelo="banco")`; seguradora fica em abstenção até lente própria. A seleção do IF.data
continua pelo setor (decisão de 25/10/2026; pelo BPP, na 2C). Não apresentar Basileia nem a
inadimplência como parte do valor da lente: as duas são contexto, só para leitura.

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
2. **2A Dados corretos** — concluída (tag `v2-fase-2a`; dados de referência, E-1, DY único, E-2, cinco anos, dívida líquida, bancos, medida de liquidez); **2B Taxa real, bancos e escopo** — fila da fase concluída (resumo em `docs/loop/historico/fase-2b/pr-fase-2b.md`); fila de fechamento da auditoria em execução (`docs/loop/fila.md`, branch `v2/fase-2b`); **2C Qualidade e apresentação** (normalização, lente de qualidade, histerese, vocabulário, lentes, fim do Markowitz)
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

- Correção: teste xfail estrito provando o bug → correção → marca retirada → PASS (ADR-0003, D27).
- Refactor: nenhum teste existente muda; as seções A, B e C de
  `tests/test_financeiro_pre_refactor.py` e o golden dos motores
  (`tests/test_equivalencia_motores.py`, grade em `tests/fixtures/golden_motores.jsonl`) são o juiz.
- Depois: `/review-diff` → `/safe-commit` (sem push) → checkpoint da fase → push manual.
- `xfail_strict = true` é obrigatório, senão XPASS não falha e o gate é fictício.
- Antipadrão recorrente: teste que asserta sem verificar. Valide por mutação.

---

## Bugs e regressão

Decisão do Marcos de 15/10/2026. Registro e detalhe em `tests/regressao/README.md`.

1. Bug confirmado (auditoria, revisão ou uso) vira teste em `tests/regressao/` no mesmo dia,
   antes de qualquer correção
2. Bug ainda não corrigido fica xfail estrito com ID e item que corrige; o `xfail_strict` do
   `pytest.ini` faz o CI quebrar se ele passar sem a marca ser retirada
3. A correção retira a marca, o teste fica para sempre e o registro muda para "corrigido"
4. Nenhum item `fix:` fecha sem o teste de regressão do bug que corrige

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
