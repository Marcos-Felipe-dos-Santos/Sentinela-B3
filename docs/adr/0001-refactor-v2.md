# ADR 0001 — Refactor V2.1: extrair metodologia para `sentinela/methods/`

- **Status:** aceito
- **Data:** 2026-09-09
- **Contexto de origem:** `docs/auditoria/2026-09-red-team.md` (60 achados: 6 críticos, 22 altos)
- **Decisores:** mantenedor

---

## Contexto

O Sentinela B3 tem uma base de engenharia melhor do que a média: 255 testes que
rodam em ~2s (a Selic é buscada no BCB no import de `config`, ver armadilha 8 do `CLAUDE.md`), `sentinela/domain/` com 91-98% de cobertura, SQL
parametrizado sem exceção e um modelo de proveniência por campo bem desenhado.

O problema não é a fundação. São duas camadas acima dela.

**A camada de resultado não é auditável.** O sistema produz um número em toda
circunstância: nenhuma falha de fonte, nenhum dado ausente e nenhuma incoerência
de unidade interrompe a análise. 19 dos 60 achados produzem erro silencioso, e a
validação cruzada que deveria capturá-los é tautológica no caminho CVM — compara
`pl` com `preco/lpa` quando `market_engine.py:513` **define** `pl = preco/lpa`.
A consequência prática: não há como distinguir, olhando a tela, uma análise
correta de uma errada por fator 2. O badge 🟢 "Dados CVM" acompanha as duas.

**A metodologia não está validada.** A única evidência empírica do projeto usa
dados fabricados (`fundamentos_point_in_time.csv`, 15 linhas retro-estimadas de
dados atuais). Três dos quatro métodos — Bazin, Gordon e o valuation de FII —
colapsam em `DY ÷ taxa`, com o preço cancelando, e não conseguem gerar sinal
positivo no regime de juros vigente.

Continuar adicionando features sobre essa base multiplica a superfície de erro
silencioso.

---

## Decisão

Extrair a metodologia de valuation de `valuation_engine.py` e `fii_engine.py`
para um pacote `sentinela/methods/`, com **contrato explícito de unidade, regime
e abstenção**, em fases nas quais refactor e mudança de comportamento nunca
ocorrem no mesmo PR.

### Estrutura-alvo

```
sentinela/
  domain/     units.py (NOVO: Ratio, Percent, BRL, RateNominal, RateReal)
              models.py  provenance.py  enums.py
  methods/    base.py (Protocol + MethodResult | Abstention)
              graham.py  bazin.py  lynch.py  gordon.py
              fii_yield.py  fii_nav.py  registry.py
  data/       providers
  news/       collectors/  scoring/     ← dependência de mão única
  services/   AnalysisService, conectado
  api/        routers FastAPI
  web/        templates Jinja2 + HTMX + Tailwind
```

### Contratos que a estrutura precisa garantir

**Contrato de método.** Cada método declara `version`, `regime` (`REAL` |
`NOMINAL`), `requires`, `assumptions`, e devolve `MethodResult | Abstention`.
Sem insumo, o método **abstém-se** — não devolve um número conservador. Essa é a
correção direta do achado central da auditoria: hoje o sistema sempre produz um
número, e é isso que torna o resultado inauditável.

**Contrato de unidade.** `units.py` torna a mistura real/nominal um erro de tipo,
não um bug silencioso. `cost_of_equity_real()` devolve taxa real; `g = ROE ×
retenção` é nominal. Trocar Selic por NTN-B no Gordon sem converter os dois
derruba `k − g` de ~13,75% para ~6% e mais que dobra todos os fair values.

**Contrato de isolamento.** `sentinela/methods/` **nunca** importa de
`sentinela/news/`. Garantido por teste no grafo de import, não por disciplina.

**Ponto único de normalização de DY.** Hoje existem três normalizadores
independentes com regras incompatíveis, aplicados em cascata sobre o mesmo campo
(`config.py:311`, `market_engine.py:377-379`, `brapi_provider.py:35`). 30% pode virar
0,3% sem alerta. A V2.1 tem um, na fronteira do provider.

---

## Fases

| # | Fase | Conteúdo |
|---|---|---|
| 0 | Preparação | sync de instruções, CI + `xfail_strict` + fixture Selic + `mutmut`, rede de segurança de caracterização, decisão sobre o scraper |
| 1 | `units.py` + extração de `methods/` | preservando comportamento; caracterização como gate |
| 2 | Metodologia | E-1, E-2, DY em ponto único, matriz Selic. **Um PR por método** |
| 3 | E-14 (histórico) + E-6 (Selic) | pré-requisitos duros da V2.1 |
| 4 | FastAPI + HTMX | casca, telas persistentes, watchlist |
| 5 | Notícias estágio 1 | só CVM Fatos Relevantes. Entrega e mede |
| 6 | Estágios 2-4 | corroboração/tração/sentimento, só se o estágio 1 provar necessidade |

**Regra dura da Fase 1:** refactor e mudança de comportamento nunca no mesmo PR.
Um PR que move código não altera nenhum número; um PR que altera um número não
move código. Sem isso, a suíte de caracterização não consegue distinguir
regressão de progresso.

---

## Classificação do código existente

Herdada da auditoria, seção "Reescrever vs. Refatorar vs. Manter".

**Reescrever** — a lógica está errada por dentro, não apenas malfeita:
`valuation_engine.processar` (piso de P/L 7, taxa do Gordon, taxa do Bazin e JCP
são decisões que precisam ser retomadas juntas), `fii_engine.analisar` (sem
ancoragem patrimonial, dupla contagem de vacância), `portfolio_engine.otimizar`
(split 40/60 hardcoded, médias históricas como retorno esperado),
`backtesting/fundamentos_point_in_time.csv` (deletar e reconstruir da CVM por
`DT_ENTREGA`).

**Refatorar** — a estrutura serve, os detalhes falham: `market_engine` (a cascata
está certa; normalização, proveniência e preservação de valores brutos precisam
de trabalho), `cvm_provider` (download atômico, cache de DataFrame, `DT_REFER`
determinístico, plano de contas por setor, TTM via ITR), `data_quality` (os
checks certos, aplicados aos valores certos, **antes** das mutações), `app.py`
(delegar para `AnalysisService` e parar de mutar `dados`), `AssetClassifier`
(inverter a regra do sufixo "11" para evidência positiva).

**Manter** — `sentinela/domain/`, `technical_engine` (só corrigir o RSI sem
perdas), `database.py` (PK composta e migrations, não reescrita),
`cvm_ticker_map` / `cvm_fii_map`, e os 255 testes existentes.

---

## Alternativas consideradas

**Reescrever do zero.** Rejeitada. A fundação — domínio, proveniência, SQL,
suíte rápida — é o ativo mais caro de reconstruir e é justamente a parte
que está boa. O que está errado é a camada de metodologia, que é pequena
(`valuation_engine.py` 249 linhas, `fii_engine.py` 152) e cujo custo real está na
decisão econômica, não no código.

**Emendar `valuation_engine.py` in-place, achado a achado.** Rejeitada. O piso de
P/L 7, a taxa do Gordon, a taxa do Bazin e o tratamento de JCP interagem: corrigir
um isoladamente desloca o fair value pelos outros sem que nenhum teste perceba.
E sem contrato de unidade, cada correção reintroduz o risco de mistura
real/nominal.

**Manter o `valuation_engine` e só adicionar validação por cima.** Rejeitada.
A validação cruzada tautológica (`data_quality.py:170`) é exatamente essa
tentativa, e é estruturalmente incapaz de disparar. Validação sobre valores já
mutados não valida nada.

---

## Consequências

**Positivas.** A abstenção torna visível o que hoje é silencioso. O contrato de
unidade transforma a classe de bug mais cara do projeto em erro de tipo. A
separação por método permite um PR por decisão econômica, revisável isoladamente.
A camada `sentinela/` deixa de ser código morto testado e passa a ser o caminho
real.

**Negativas e custos aceitos.** Duas camadas de orquestração coexistem durante a
transição (`app.py` roda, `sentinela/services/` não está conectado) — e a mesma
feature não pode ser adicionada nas duas. A Fase 2 vai **mudar números na tela**,
possivelmente muito: a matriz de sensibilidade Selic × fair value é
pré-requisito, não documentação posterior. O esforço até "local, confiável e
documentado com honestidade" é de 7-8 semanas focadas.

**Riscos.** O maior é fazer a Fase 2 sem a rede de caracterização da Fase 0, e
não conseguir distinguir uma correção de uma regressão. O segundo é a Fase 4
(FastAPI) começar antes da Fase 2 terminar, dobrando a superfície de UI sobre uma
metodologia ainda em revisão.

---

## Travas — nenhuma feature nova antes destas

Condições mínimas de retomada, da auditoria:

1. Guard de reconciliação em LPA/VPA (`|shares × preço − market_cap| / market_cap ≤ 5%`)
2. Matriz de sensibilidade Selic × fair value publicada
3. Normalização de DY em ponto único, com teste parametrizado na zona ambígua
4. Backtest sintético removido do repositório e estado real declarado
5. CI no GitHub Actions rodando `pytest` + `ruff` em todo PR
6. README, roadmap e `CLAUDE.md` sincronizados com o código
7. Decisão explícita sobre deploy público — se sair do roadmap, E-29 (banco
   global sem autenticação) e o vocabulário de recomendação viram bloqueadores
   absolutos

---

## Referências

- `docs/auditoria/2026-09-red-team.md` — achados, cenários de falha e esforços
- `CLAUDE.md` — armadilhas conhecidas, fonte primária para o Claude Code
- `AGENTS.md` — subconjunto para agentes externos; nunca pode contradizer o `CLAUDE.md`
