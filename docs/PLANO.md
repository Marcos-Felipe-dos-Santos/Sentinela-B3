# Plano V2 — Sentinela B3

> Roteiro único do projeto. Decisões de arquitetura em `docs/adr/`: 0001 (refactor V1 → V2.1) e 0002 (execução por loop, tempo como entrada, dados oficiais primeiro, limpeza e núcleo financeiro). Execução em `docs/loop/`.
>
> Itens marcados **[D5]**, **[D6]** etc. dependem das propostas do ADR-0002, aceitas ou recusadas no checkpoint da Fase 0.
>
> Versão de 22/09/2026, revisada para incluir a limpeza de resíduos e o núcleo financeiro.

## 1. Propósito

O Sentinela B3 é uma plataforma educacional e local-first de análise de ações e FIIs da B3. Não é consultoria financeira.

O diferencial não é a interface nem a quantidade de indicadores. É a metodologia auditável: cada número tem origem, data e versão de método; o sistema se abstém quando não tem insumo; e qualquer análise pode ser refeita para qualquer data passada.

Nada disso vale se o número estiver errado. Por isso o núcleo financeiro vem antes de qualquer feature nova.

## 2. Definição de pronto

### Núcleo de portfólio (Fases 0–6)

**Números corretos**
- [ ] Todo método devolve `MethodResult | Abstention`; nenhum fallback silencioso no caminho do resultado.
- [ ] Toda companhia e todo FII listados estão mapeados para a CVM por dado oficial; a classe do ativo (ação, unit, FII, ETF, BDR) nunca é deduzida do ticker.
- [ ] Taxa de desconto real (NTN-B longa + prêmio), com k e g no mesmo regime; a Selic não é taxa de desconto.
- [ ] Bancos têm lente própria; método que não se aplica a um setor se abstém, com motivo.
- [ ] Os métodos usam a série de cinco anos onde a metodologia pede, e a qualidade da empresa pesa na classificação.
- [ ] Alavancagem medida por dívida financeira líquida.
- [ ] Unidade é tipo; existe um único normalizador de DY, na fronteira do provedor.
- [ ] Os achados críticos estão fechados (seção 10).

**Tempo**
- [ ] `analisar(ticker, as_of)` reproduz a análise de qualquer data da série reconstruída. [D5]
- [ ] O backtest roda sobre dados ponto-no-tempo reais, com universo sem viés de sobrevivência. [D5]
- [ ] O histórico de classificações existe desde o início da série. [D5]

**Carteira**
- [ ] Nenhuma alocação sugerida. A carteira tem camada de risco: concentração, volatilidade, correlação e sensibilidade a juros.
- [ ] Dados da carteira do usuário nunca aparecem em arquivo versionado.

**Operação e engenharia**
- [ ] O fechamento diário roda sem supervisão, com relatório de saúde e backup. [D6]
- [ ] Existe relatório de rastreabilidade por ativo. [D9]
- [ ] O estudo de evento dos fatos relevantes está publicado. [D8]
- [ ] Uma fonte de verdade por conceito: sem `auditoria.py` reimplementando métodos, sem dois bancos SQLite, sem orquestração duplicada.
- [ ] Nenhum resíduo: vulture e deptry sem achados fora da lista de exceções justificada; nenhum módulo órfão; nenhuma referência a arquivo removido na documentação; uma única cópia do repositório (seção 11).
- [ ] CI verde, `xfail_strict` ativo, contratos de import no CI e mutation score ≥ 80% em `sentinela/methods/`.
- [ ] README e página de metodologia gerada do registro de métodos.

### Produto completo (Fases 7–8)

- [ ] Interface FastAPI + HTMX com paridade com a V1; Streamlit e `app.py` removidos.
- [ ] Raiz do repositório sem módulos da V1: só `sentinela/`, `tests/`, `docs/` e configuração.
- [ ] Gate de cobertura no CI.
- [ ] IA nas telas explicando premissas, com abstenção e conjunto de avaliação próprio.
- [ ] Estágios 2–4 de notícias, se e somente se o estudo de evento justificar.

## 3. Princípios

1. **Motor antes da vitrine.** A camada de entrega não migra antes da camada de resultado ser confiável. (ADR-0001)
2. **O sistema pode se recusar.** Sem insumo, abstenção — nunca número degradado. (ADR-0001)
3. **Unidade é tipo.** `Ratio`, `Percent`, `BRL`, `RateNominal`, `RateReal` e quantidade de ações com escala. (ADR-0001)
4. **Tempo é entrada.** Nenhum cálculo lê "hoje" por conta própria; `as_of` é parâmetro. [D5]
5. **Métodos são funções puras.** Sem rede, banco ou relógio; não importam notícias, análise técnica nem provedores. Garantido por contrato de import no CI. (ADR-0001 + D11)
6. **Oficial primeiro.** CVM, B3 e Banco Central como fonte primária; APIs de terceiros como complemento. [D7]
7. **Uma fonte de verdade por conceito, e nada de resíduo.** O legado sai ao fim da fase que o substitui; toda fase fecha com uma limpeza; o CI impede resíduo novo. (D14)
8. **O loop executa, o Marcos decide.** Nenhum item com definição de "correto" em aberto entra na fila sem a decisão escrita nele.
9. **A nota mede a empresa, não o ciclo de juros.** Juros entram como custo de capital real; a qualidade da empresa pesa na classificação. (D15)
10. **A carteira do usuário é dado privado.** Nunca vai para arquivo versionado — o repositório é público. (D15)

## 4. Arquitetura-alvo

```
sentinela/
  domain/       units.py  models.py  provenance.py  enums.py  tempo.py
  methods/      base.py       ValuationMethod, MethodInputs (congelado, com as_of),
                              MethodResult | Abstention, applies_to
                graham.py  bazin.py  lynch.py  gordon.py  fii_yield.py  fii_nav.py
                bancos.py  qualidade.py  reverso.py (opcional)
                registry.py (versão + changelog)
  data/
    providers/  cvm.py  cvm_fii.py  cvm_ipe.py  b3_cotahist.py  bcb_sgs.py
                bcb_bancos.py (fonte a confirmar)  brapi.py  yfinance.py
                fundamentus.py (conforme F0-4)
    referencia/ ticker ↔ CNPJ, classe do ativo, setor, segmento do FII, grupo de controle
    pit/        leitura ponto-no-tempo: demonstração vigente, preço e universo na data
    store/      SQLite único + migrations/
  services/     AnalysisService.analisar(ticker, as_of)
  risk/         concentração, volatilidade, correlação, sensibilidade a juros
  jobs/         fechamento.py  backfill.py
  reports/      rastreabilidade/  digest/       Jinja + SVG, HTML estático
  news/         collectors/  scoring/
  cli.py        sentinela analisar | fechamento | backfill | relatorio
  api/          routers FastAPI
  web/          templates (reusa reports/) + HTMX + Tailwind
```

**Contrato de import (verificado no CI):**

```
sentinela/methods  ──✗──>  sentinela/news, technical_engine, sentinela/data, rede, banco
```

O cálculo recebe tudo pronto em `MethodInputs`. Quem busca dado é `data/`; quem escolhe a data é o chamador.

## 5. Modelo de dados

Um SQLite único, alterado só por migração numerada (`sentinela/data/store/migrations/NNN_descricao.sql`), com tabela `schema_version`.

| Tabela | Conteúdo | Chave |
|---|---|---|
| `demonstracoes` | contas da DFP/ITR, com escala | cnpj, documento, dt_refer, versao, conta |
| `entregas` | data de entrega de cada documento e versão | cnpj, documento, dt_refer, versao |
| `composicao_capital` | ações ON, PN e em tesouraria por documento | cnpj, dt_refer, versao |
| `precos` | COTAHIST bruto: OHLC, volume, negócios | ticker, data |
| `eventos_societarios` | desdobramentos, grupamentos, bonificações | ticker, data_ex |
| `series_macro` | séries completas do SGS (432, 12, 433, NTN-B) | codigo, data |
| `universo` | ticker ↔ cnpj, classe do ativo, setor, segmento do FII, grupo de controle, início e fim de listagem | ticker, inicio |
| `indicadores_bancarios` | Basileia e inadimplência por instituição e data | cnpj, data |
| `analises` | resultado ou abstenção por ticker, data, método e versão; hash dos insumos; proveniência | ticker, as_of, metodo, versao |
| `carteira` | posições do usuário — dado local, nunca exportado para arquivo versionado | ticker |
| `watchlist`, `digests`, `fatos_relevantes` | operação e notícias | — |

**Regra de leitura ponto-no-tempo:** numa data D, vale a última versão entregue até D. Onde versões antigas não estiverem disponíveis, usa-se a versão atual e a limitação fica registrada na proveniência.

## 6. Fases

Cada item vira um commit. Os IDs são estáveis e aparecem na fila, no diário e nos PRs.

Toda fila termina com dois itens fixos: a **limpeza** do que a fase tornou obsoleto e o **resumo**, que também arquiva a fase (seção 11).

### Onde está o núcleo financeiro

| Tema | Itens |
|---|---|
| Proteção imediata: aviso de revisão, sem "Alocação Sugerida", backtest marcado como inválido | F0-9 |
| Críticos: E-1, E-2, mutação de dados | F2A-3, F2A-5, F2A-6 |
| Dados de referência: cobertura de todos os listados e classe do ativo por dado oficial | F2A-1, F2A-2 |
| Taxa real (NTN-B + prêmio) no lugar da Selic | F2B-1, F2B-2 |
| Bancos | F2A-9, F2B-3, F2B-4 |
| Cinco anos de CVM e qualidade da empresa | F2A-7, F2C-1, F2C-2 |
| Alavancagem por dívida financeira líquida | F2A-8 |
| Carteira: fim do otimizador e camada de risco | F2C-9, F4-7 |
| Histórico longo de preços e séries macro completas | F3-1, F3-4 |
| Backtest real | F3-8 |

A ordem segue a prioridade "críticos → taxa real → dados de referência → o resto", com uma inversão: os dados de referência vêm primeiro na Fase 2A, porque sem o mapa automático a CVM só alcança os tickers dos mapas manuais — e o E-1 e os dados de bancos dependem dela.

### Fase 0 — Preparação

Em execução pelo loop. Escopo e aceites em `docs/loop/fila.md`.

| Item | Tipo | Entrega |
|---|---|---|
| F0-0 | docs | Auditoria no repositório, com IDs de achado normalizados |
| F0-1 | docs | Instruções, plano e ADRs validados contra o código |
| F0-2 | chore | CI em Python 3.13, `xfail_strict`, fixture da Selic, mutmut 3 e ferramentas de limpeza |
| F0-3 | test | Rede de caracterização (seções A, B e C) |
| F0-4 | levantamento | Brief da decisão do scraper (E-11 × F-25) |
| F0-5 | docs | Backlog do Jules |
| F0-6 | levantamento | Dossiê de decisões da Fase 2, incluindo o núcleo financeiro |
| F0-7 | levantamento | Inventário de resíduos, classificado |
| F0-8 | limpeza | Remoção dos resíduos puros, sem efeito em comportamento |
| F0-9 | chore | Quarentena da V1: aviso de revisão, sem "Alocação Sugerida", backtest marcado como inválido |
| F0-10 | levantamento | Proposta da fila da Fase 1 |
| F0-11 | docs | Resumo e arquivamento da fase |

**Checkpoint:** revisar o F0-3, que é o gate da Fase 1; decidir o F0-4 e os itens *investigar* do inventário; conferir a quarentena no app; aceitar ou recusar D5–D13; aprovar a fila da Fase 1; push da fase. Com o push confirmado, arquivar e apagar a cópia do repositório no `E:\`.

### Fase 1 — Fundação: tipos, contratos e extração

Comportamento idêntico ao da V1. Refactor e mudança de comportamento nunca no mesmo item. Ela vem antes dos críticos porque as correções dependem dela: o E-1 precisa do `units.py` para a escala das ações, e as lentes novas precisam do contrato de método.

| Item | Entrega |
|---|---|
| F1-1 | `units.py` (aditivo) |
| F1-2 | Contrato de método: `MethodInputs` congelado com `as_of` [D5], `MethodResult \| Abstention`, `applies_to` |
| F1-3 a F1-8 | Extração de um método por item (Graham, Bazin, Lynch, Gordon, FII yield, FII NAV); o motor V1 passa a delegar |
| F1-9 | `registry.py`, com versão 1.0.0 = comportamento V1 |
| F1-10 | Contratos de import no CI [D11] |
| F1-11 | Remoção do caminho morto `tecnico_negativo` |
| F1-12 | Relatório de rastreabilidade v0, estático, com os dados de hoje [D9] |
| F1-13 | Limpeza: código de método que sobrou no `valuation_engine.py` e no `fii_engine.py`; `ruff` completo, `deptry` e `vulture` (em modo relatório) no CI |
| F1-14 | Resumo e arquivamento |

**Gate:** seções A, B e C inalteradas; mutation ≥ 80% em `sentinela/methods/`; contratos verdes.
**Antes de começar:** a fila final vem do F0-10, revisada no checkpoint. A tabela acima é o formato esperado.

### Fase 2A — Dados corretos

Correções com teste xfail primeiro. Dados de referência antes de tudo.

| Item | Entrega |
|---|---|
| F2A-1 | Dados de referência: mapa ticker ↔ CNPJ automático para todas as companhias e FIIs listados; classe do ativo (ação, unit, FII, ETF, BDR) por dado oficial, nunca pelo sufixo do ticker; conserto da classe de atualização automática (`CVMTickerMap`, nunca instanciada fora dos testes e que não preenche `ticker`). Os mapas manuais viram fallback |
| F2A-2 | Setor, segmento do FII e grupo de controle, lidos dos arquivos da CVM que o projeto já baixa |
| F2A-3 | Ações da Composição do Capital (ON + PN − tesouraria, escala via `units.py`, mesmo documento do lucro) — E-1 [D7] |
| F2A-4 | Um único normalizador de DY, na fronteira do provedor; os outros dois saem |
| F2A-5 | Validação cruzada contra fonte independente — E-2 |
| F2A-6 | Fim da mutação de `dados` antes das checagens de qualidade |
| F2A-7 | Série de cinco anos por empresa a partir da DFP, e TTM a partir do ITR (quatro trimestres; o quarto = DFP − acumulado de nove meses) |
| F2A-8 | Dívida financeira líquida (empréstimos + debêntures − caixa e aplicações), que passa a ser a medida de alavancagem no lugar do endividamento contábil total |
| F2A-9 | Dados de bancos: patrimônio, lucro e ROE da DFP; Basileia e inadimplência de fonte oficial do Banco Central, confirmada no dossiê |
| F2A-10 | Gate de liquidez com volume e negócios do COTAHIST; abaixo do limiar, abstenção [D7] |
| F2A-11 | `CVMFIIProvider` conectado; P/VP ausente vira abstenção em vez de 1,0 |
| F2A-12 | Validação de ticker (allowlist) antes de URL e de prompt |
| F2A-13 | Limpeza: tabelas de vacância manuais (`FII_MANUAL_FALLBACK`, `VACANCIA_CONHECIDA`), fallbacks que perderam função, heurística de classe pelo sufixo e — se o mapa automático cobrir o universo — os mapas manuais |
| F2A-14 | Resumo e arquivamento |

**Gate:** cada correção com XPASS; seção A inalterada; seção B só muda onde está marcada; mutation; cobertura CVM de 100% dos listados mapeáveis.
**Decisões:** limiares de divergência de ações e de liquidez; fonte dos dados bancários.
**Jules:** os tickets dele em `cvm_provider.py` precisam estar integrados antes do F2A-1.

### Fase 2B — Taxa real, bancos e escopo

Decisão do Marcos item a item, com o dossiê do F0-6. Cada método alterado muda de versão, com changelog.

| Item | Entrega |
|---|---|
| F2B-1 | Taxa de desconto: NTN-B longa (real) + prêmio de risco, via `cost_of_equity_real`, com k e g no mesmo regime. A Selic deixa de ser taxa de desconto. Prêmio e vértice decididos com o dossiê |
| F2B-2 | Benchmarks por classe: FII comparado com a NTN-B (spread) e com a Selic líquida; cada método documenta a taxa que usa |
| F2B-3 | Lente de bancos: P/VP justificado pelo ROE e pelo custo de capital do F2B-1; Basileia e inadimplência como qualidade. Holdings de banco pelo desconto sobre as participações (opcional) |
| F2B-4 | `applies_to`: métodos de empresa não financeira se abstêm em bancos e seguradoras; ETFs e BDRs ficam fora do escopo dos métodos, com o motivo exibido |
| F2B-5 | Limpeza: constantes e caminhos que usavam a Selic como taxa de desconto |
| F2B-6 | Resumo e arquivamento |

**Gate:** seção A inalterada; seção B virou exatamente onde marcada; mutation ≥ 80%; os resultados antes e depois da taxa real estão comparados no diário.

### Fase 2C — Qualidade e apresentação

| Item | Entrega |
|---|---|
| F2C-1 | Fundamentos normalizados: cada método declara se usa o último ano, o TTM ou a série de cinco anos (por exemplo, dividendos médios no Bazin, LPA médio no Graham, CAGR no Lynch) |
| F2C-2 | Lente de qualidade com cinco anos: ROE e sua estabilidade, margens, dívida líquida sobre EBITDA, consistência de lucro e de dividendos |
| F2C-3 | Banda neutra com histerese na classificação — F-28 |
| F2C-4 | Vocabulário único: "classificação" e "sinal" em código, banco e textos [D10] |
| F2C-5 | Métodos apresentados como lentes, sem mediana vendida como "valor justo" — incluindo o caso de dois métodos, que hoje vira média por acidente da biblioteca padrão |
| F2C-6 | Lente de valuation reverso sobre fluxo de caixa (DFC) — opcional |
| F2C-7 | Setores e pares a partir dos dados do F2A-2; fim do mapa fixo e da duplicidade do MGLU3 |
| F2C-8 | Métodos duplicados do `auditoria.py` aposentados; o que sobra vira invariante sobre `methods/` |
| F2C-9 | Otimizador de Markowitz e divisão fixa 40% FIIs / 60% ações aposentados: retorno esperado estimado com um ano de dados não tem significância, e o resultado era uma sugestão de alocação |
| F2C-10 | Limpeza: código do otimizador, constantes de `config.py` sem leitor e marcas `QUEBRA ESPERADA` já resolvidas, consolidadas na seção A |
| F2C-11 | Resumo e arquivamento |

**Gate:** seção A inalterada; seção B virou exatamente onde marcada; mutation ≥ 80%.

### Fase 3 — Tempo como entrada [D5]

| Item | Entrega |
|---|---|
| F3-1 | Sem rede no import; `MacroContext` por data, com as séries completas do SGS e não só o último valor — E-6 |
| F3-2 | SQLite único com migrações; os dois bancos atuais viram um — E-14 |
| F3-3 | Demonstrações ponto-no-tempo: contas, entregas, versões e composição do capital |
| F3-4 | Histórico longo de preços pelo COTAHIST, com eventos societários e série ajustada para retorno |
| F3-5 | Universo ponto-no-tempo, a partir dos dados de referência do F2A-1, incluindo empresas deslistadas |
| F3-6 | `AnalysisService.analisar(ticker, as_of)` conectado; `app.py` passa a chamar o serviço |
| F3-7 | Reconstrução histórica (backfill) do universo |
| F3-8 | Backtest ponto-no-tempo; os CSVs fabricados saem do repositório |
| F3-9 | Limpeza: os dois bancos antigos (com backup antes), o cache de 7 dias da cascata antiga, a orquestração duplicada do `app.py`, `limpar_banco.py` (substituído pelas migrações) e `auditar_recomendacoes.py` (substituído pelo backtest), conforme o inventário |
| F3-10 | Resumo e arquivamento |

**Gate:** `as_of` = hoje reproduz o resultado atual; backtest reprodutível; universo com deslistadas; limitações registradas na proveniência.
**Decisões:** definição do universo; profundidade da série (desde 2011, quando começa o ITR aberto, ou menos); tratamento de reapresentações antigas.

### Fase 4 — Operação diária, rastreabilidade e risco [D6, D9]

| Item | Entrega |
|---|---|
| F4-1 | CLI `sentinela` (analisar, fechamento, backfill, relatorio); dependências em `pyproject.toml` + `uv.lock` |
| F4-2 | Job de fechamento: atualiza cada fonte na sua cadência, analisa universo e watchlist na data, grava, gera digest com histerese e relatório de saúde |
| F4-3 | Agendamento pelo Agendador do Windows via `wsl.exe`, rodando mesmo se perder o horário; roteiro em `docs/operacao.md` |
| F4-4 | Relatório de rastreabilidade v1, com histórico de classificações |
| F4-5 | Backup do banco após o fechamento (rclone para o Google Drive) |
| F4-6 | Testes de contrato dos provedores com respostas gravadas |
| F4-7 | Camada de risco da carteira: concentração por ativo, classe, setor e grupo econômico; volatilidade, drawdown e correlação com o histórico longo; sensibilidade a juros. Sem otimizador e sem alocação sugerida; os alertas de risco entram no digest |
| F4-8 | Limpeza: `requirements*.txt` (substituídos pelo `pyproject.toml`), scripts avulsos que viraram comando da CLI e política de retenção dos downloads brutos da CVM e da B3 no job |
| F4-9 | Resumo e arquivamento |

**Gate:** 14 dias seguidos de fechamento sem falha silenciosa; relatório gerado para todo o universo; camada de risco calculada para a carteira (relatório local, fora do git).

### Fase 5 — Notícias medidas [D8]

| Item | Quem | Entrega |
|---|---|---|
| F5-1 | Jules | Coletor do IPE: fatos relevantes, CNPJ → ticker, incremental |
| F5-2 | Loop | Estudo de evento com os cinco anos que o IPE aberto oferece: retorno anormal contra o Ibovespa por janela e tipo de documento, com significância; relatório em `docs/estudos/` |
| F5-3 | Marcos | Go/no-go dos estágios 2–4, registrado em ADR |
| F5-4 | Loop | Limpeza: extrações e notebooks exploratórios que não entraram no relatório |
| F5-5 | Loop | Resumo e arquivamento |

**Gate:** estudo reprodutível a partir do banco.

### Fase 6 — Vitrine (fecha o núcleo)

Começa pela **varredura final**:
- vulture e deptry zerados fora das exceções justificadas, e passam a bloquear o CI;
- nenhum módulo órfão;
- documentação sem referência a arquivo removido;
- branches integrados apagados.

Depois, a vitrine: README reescrito; página de metodologia gerada do `registry.py`; texto do estudo de evento; demonstração em GIF; CHANGELOG por fase.

### Fase 7 — Interface FastAPI + HTMX

Mantenedor e loop; nunca o Jules.

| Item | Entrega |
|---|---|
| F7-1 | Casca FastAPI em `127.0.0.1`; Jinja reusando `reports/`; HTMX vendorizado; Tailwind pela CLI standalone, sem Node |
| F7-2 | Telas: painel (digest), ativo (lentes, rastreabilidade, histórico), carteira (risco), watchlist e notícias |
| F7-3 | Segurança: autoescape; nunca `\|safe` em texto de LLM ou notícia; CSRF nas escritas; testes de rota com `TestClient` |
| F7-4 | Paridade com a V1; Streamlit e `app.py` removidos; gate de cobertura entra no CI |
| F7-5 | Limpeza final da V1: módulos da raiz sem chamador e dependências de interface antigas — fim da migração gradual |
| F7-6 | Resumo e arquivamento |

### Fase 8 — IA nas telas e notícias 2–4 (condicional)

| Item | Entrega |
|---|---|
| F8-1 | IA que explica premissas, recebe confiança e abstenções e pode concluir que os dados não sustentam conclusão |
| F8-2 | Saída cacheada por hash dos insumos + versão do prompt; texto de notícia tratado como dado não confiável (sem ferramentas, saída estruturada) |
| F8-3 | Modelo local via Ollama, com a GPU no WSL2, como padrão; Groq e Gemini como alternativa |
| F8-4 | Conjunto de avaliação com casos em que a IA precisa se abster |
| F8-5 | Estágios 2–4, só com o go do F5-3 |
| F8-6 | Limpeza: versões de prompt e modelos locais que não entraram |
| F8-7 | Resumo e arquivamento |

## 7. Ciclo de uma fase

1. **Planejar.** No fim da fase anterior, o fable-architect propõe a fila em `docs/loop/fila-faseN-proposta.md`; o senior-reviewer revisa o plano; o Marcos aprova.
2. **Decidir.** Item que depende de decisão recebe a decisão escrita antes de entrar na fila.
3. **Ativar.** No branch novo `v2/fase-N`, criado a partir da `main`:

   ```bash
   git mv -f docs/loop/fila-faseN-proposta.md docs/loop/fila.md
   git commit -m "chore: activate phase N queue"
   ```

4. **Executar.** No WSL2, dentro do tmux:

   ```bash
   cd ~/projetos/Sentinela_B3 && source venv/bin/activate
   claude --permission-mode auto
   ```

   Na sessão, `/model sonnet` e depois:

   ```text
   /goal Todos os itens de docs/loop/fila.md antes da linha [DECISÃO] estão marcados [x], ou algum item está [!] com o motivo registrado em docs/loop/diario.md. Leia e siga docs/loop/protocolo.md à risca. Nunca faça git push nem abra PR. Ao fechar cada item, rode cat docs/loop/fila.md e git log --oneline -3.
   ```

5. **Revisar.** No `[DECISÃO]`, o Marcos lê o resumo em `docs/loop/historico/fase-N/` e revisa os commits.
6. **Publicar.** Push do branch `v2/fase-N`; PR da fase opcional, com o resumo como corpo. O CI roda; o Jules revisa.
7. **Integrar.** Merge na `main`; apagar o branch da fase (local e remoto) e marcar a tag `v2-fase-N`; atualizar a seção "Fase atual" do `AGENTS.md`.

## 8. Divisão de trabalho

| Frente | Marcos | Loop (Claude Code) | Jules |
|---|---|---|---|
| Decisões de metodologia, taxa, janelas e limiares | decide | prepara dossiê | — |
| Código das Fases 0–4 | revisa no checkpoint | implementa | — |
| Limpeza | decide os itens *investigar*; apaga o que não é rastreado | inventaria e remove o rastreado | aponta resíduo no PR, sem remover |
| Testes com especificação externa | — | — | escreve (mutation ≥ 80%) |
| Fila mecânica de infraestrutura | — | — | só fora dos arquivos travados |
| Coletor do IPE (F5-1) | — | — | código e teste |
| Estudo de evento | desenho e conclusão | implementa | — |
| Interface (Fase 7) | decide telas | implementa | nunca |
| PR da fase | aprova o merge | — | revisa |

**Arquivos travados por fase.** Enquanto a fase estiver em andamento, o Jules não abre PR que toque nestes arquivos:

| Fase | Arquivos |
|---|---|
| 0 | `CLAUDE.md`, `AGENTS.md`, `docs/`, `pytest.ini`, `pyproject.toml`, `.gitignore`, `tests/conftest.py`, `.github/`, `app.py` |
| 1 | `valuation_engine.py`, `fii_engine.py`, `sentinela/domain/`, `sentinela/methods/` |
| 2A | `market_engine.py`, `cvm_provider.py`, `cvm_fii_provider.py`, `cvm_ticker_map.py`, `cvm_fii_map.py`, `fii_engine.py`, `brapi_provider.py`, `data_quality.py`, `config.py`, `sentinela/data/` |
| 2B | `sentinela/methods/`, `config.py` |
| 2C | `sentinela/methods/`, `config.py`, `peers_engine.py`, `auditoria.py`, `portfolio_engine.py` |
| 3 | `config.py`, `database.py`, `backtesting/`, `sentinela/data/`, `sentinela/services/`, `app.py`, `limpar_banco.py`, `auditar_recomendacoes.py` |
| 4 | `sentinela/jobs/`, `sentinela/reports/`, `sentinela/risk/`, `sentinela/cli.py`, `pyproject.toml`, `requirements*.txt` |
| 6 | `README.md`, `docs/`, arquivos da raiz |
| 7 | `sentinela/api/`, `sentinela/web/`, `app.py`, módulos da V1 na raiz |

## 9. Modelos e limites de uso

- **Orquestrador do loop e junior-dev:** Sonnet.
- **senior-reviewer:** Opus, por item. Se o limite semanal apertar, Sonnet por item e um Opus por fase, sobre o diff inteiro.
- **fable-architect:** só no item de planejamento de cada fase.
- **scout:** Haiku.
- **Expectativa no Pro:** esperas de limite fazem parte. O loop retoma sozinho até duas vezes seguidas; confira uma vez por dia.

## 10. Achados da auditoria e da análise financeira

IDs conforme a auditoria normalizada no F0-0 (`docs/auditoria/2026-09-red-team.md`).

| Achado | Onde |
|---|---|
| E-1 — LPA/VPA sem reconciliação de ações | F2A-3 |
| E-2 — validação cruzada tautológica | F2A-5 |
| Mutação de `dados` antes das checagens | F2A-6 |
| Backtest com fundamentos retroestimados | quarentena no F0-9; backtest real no F3-8 |
| Colapso DY ÷ taxa; nota seguindo o ciclo da Selic | F2B-1, F2B-2, F2C-2, F2C-5 |
| Selic nominal como taxa de desconto; `cost_of_equity_real` sem uso | F2B-1 |
| Só o último ano, com cinco anos de CVM já baixados | F2A-7, F2C-1 |
| Alavancagem pelo endividamento contábil total | F2A-8 |
| Bancos sem regras próprias | F2A-9, F2B-3, F2B-4 |
| Markowitz com um ano de dados, divisão fixa 40/60 e "Alocação Sugerida" | F0-9, F2C-9, F4-7 |
| Cobertura por mapas manuais; atualizador que não preenche ticker | F2A-1, F2A-13 |
| Segmento do FII e controle acionário baixados e não lidos | F2A-2 |
| BDRs tratados como ações e ETFs como FIIs | F2A-1, F2B-4 |
| Histórico de preço de um ano; séries macro só com o último valor | F3-4, F3-1 |
| Três normalizadores de DY | F2A-4 |
| E-6 — Selic congelada no import | F3-1 |
| E-14 — análise sobrescrita, sem histórico | F3-2 |
| F-28 — score colado no gate | F2C-3 |
| E-11 × F-25 — scraper do Fundamentus | decisão no F0-4 |
| Integrações inertes (`CVMFIIProvider`, ITR, NTN-B, CDI, IPCA) | F2A-11, F2A-7, F2B-1, F3-1 |
| P/VP ausente tratado como 1,0 no motor de FII | F2A-11 |
| Duas tabelas de vacância, ambas ignoradas | F2A-13 |
| `tecnico_negativo` morto | F1-11 |
| Ticker sem validação | F2A-12 |
| RSI devolve 50 onde Wilder manda 100 | Jules, grupo B |
| `auditoria.py` como segunda fonte de verdade | F2C-8 |
| Dois bancos SQLite | F3-2 e F3-9 |
| Mapa de pares fixo; MGLU3 duplicado | F2C-7 |
| `BRAPI_TOKEN` fora do `.env.example` | Jules, grupo C |

## 11. Resíduos e limpeza (D14)

### Regras

1. **Inventário primeiro.** O F0-7 procura resíduo com `vulture`, `deptry`, `ruff` (F401, F841, ERA001), busca de módulos órfãos, `git ls-files` contra o `.gitignore` e revisão de documentos e branches. Cada achado recebe uma categoria:
   - *remover já* — sem efeito em comportamento;
   - *remover na fase X* — tem substituto planejado, com o item deste plano;
   - *investigar* — uso incerto (chamado por nome, callback do Streamlit, acesso por outro módulo);
   - *manter* — falso positivo, que vai para a lista de exceções do vulture com o motivo.
2. **Toda fase limpa o que tornou obsoleto**, num item de limpeza antes do resumo, e atualiza o inventário.
3. **Resíduo novo não entra.** Nenhum item acrescenta código comentado, import sem uso, print de depuração, arquivo temporário ou TODO sem item na fila. A partir da Fase 1 o CI relata; a partir da Fase 6, bloqueia.
4. **O loop só remove o que o git devolve.** Arquivo rastreado sai com `git rm`; artefato que deve continuar existindo localmente sai com `git rm --cached`. Arquivo não rastreado e branch nunca são apagados pelo loop — vão para a lista do Marcos no diário. Item *investigar* nunca sai sem decisão.
5. **Arquivar não é apagar.** O item de resumo move diário, fila e resumo da fase para `docs/loop/historico/fase-N/` e deixa no lugar da fila só a linha `[DECISÃO]`. A fila seguinte só entra quando o Marcos a ativa (seção 7).

### Resíduos conhecidos

| Resíduo | Sai em |
|---|---|
| Caminho morto `tecnico_negativo` | F1-11 |
| Código de método que sobra no `valuation_engine.py` e no `fii_engine.py` | F1-13 |
| Heurística de classe do ativo pelo sufixo do ticker | F2A-1 |
| Três normalizadores de DY | F2A-4 |
| Tabelas de vacância manuais | F2A-13 |
| Mapas manuais de ticker (`cvm_ticker_map.py`, `cvm_fii_map.py`) | F2A-13, se o mapa automático cobrir o universo |
| Selic como taxa de desconto (constantes e caminhos) | F2B-5 |
| Mapa de pares fixo | F2C-7 |
| Métodos duplicados do `auditoria.py` | F2C-8 |
| Otimizador de Markowitz e divisão fixa 40/60 | F2C-9 e F2C-10 |
| Constantes de `config.py` sem leitor | F2C-10 |
| CSVs fabricados do backtest | F3-8 |
| Dois bancos antigos, cache da cascata e orquestração duplicada do `app.py` | F3-9 |
| `limpar_banco.py` e `auditar_recomendacoes.py` (a confirmar no inventário) | F3-9 |
| `requirements*.txt` e scripts avulsos | F4-8 |
| `fundamentus_scraper.py` e `cloudscraper` | conforme a decisão do F0-4 |
| Streamlit e `app.py` | F7-4 |
| Módulos da V1 na raiz sem chamador | F7-5 |
| Cópia do repositório no `E:\` e venv do Windows | depois do push da Fase 0 |
| Branches integrados | depois de cada merge |

## 12. Cronograma estimado

Estimativa, não compromisso. Supõe o loop fazendo a maior parte do código e 6 a 8 horas por semana do Marcos para decisões e revisões.

| Período | Fases |
|---|---|
| fim de setembro e começo de outubro de 2026 | 0 |
| outubro | 1 |
| outubro a novembro | 2A |
| novembro | 2B |
| novembro a dezembro | 2C |
| dezembro de 2026 a janeiro de 2027 | 3 |
| janeiro a fevereiro | 4 |
| fevereiro a março | 5 |
| março de 2027 | 6 — núcleo de portfólio pronto |
| abril a maio | 7 |
| depois | 8, condicional |

O núcleo financeiro custou cerca de um mês: a linha de corte passou de fevereiro para março de 2027, ainda antes da reta final da graduação, no primeiro semestre.

## 13. Riscos

| Risco | Mitigação |
|---|---|
| Desânimo nas fases sem nada visível | Relatório de rastreabilidade v0 já no fim da Fase 1 |
| Limite do Pro travar o loop | Modelos por papel (seção 9); conferência diária |
| Taxa real mudar muitos números de uma vez | Dossiê comparando antes e depois; versão nova de cada método, com changelog |
| Fonte oficial de dados bancários indisponível | Confirmar no dossiê; sem ela, a lente de bancos usa só a DFP e declara a limitação |
| Dados da carteira vazarem no repositório público | Regra de privacidade; análises com a carteira só em `outputs/`, ignorado pelo git |
| Fonte externa quebrar ou mudar de formato | CVM/B3 primeiro; abstenção; testes de contrato (F4-6) |
| Ponto-no-tempo imperfeito no passado | Guardar versões desde já; limitação registrada na proveniência |
| Viés de sobrevivência no backtest | Universo com datas de listagem (F3-5) |
| Desdobramento entre a demonstração e o preço | Eventos societários explícitos (F3-4), com testes de casos conhecidos |
| Loop cimentando comportamento errado | Mutação, `[DECISÃO]` e protocolo |
| Limpeza apagar algo usado de forma dinâmica | Categoria *investigar*, lista de exceções, rede de caracterização e remoção só por `git rm` |
| Jules e loop no mesmo arquivo | Arquivos travados por fase (seção 8) |
| Perda de dados no WSL | Push por fase; backup do banco (F4-5) |

## 14. Adiado conscientemente

- **Deploy público.** Exige autenticação, isolamento por usuário e revisão do vocabulário à luz das regras da CVM sobre análise de valores mobiliários.
- **Reddit e YouTube como fontes.** Os motivos do ADR-0001 continuam valendo.
- **Estágios 2–4 de notícias.** Até o go do F5-3.
- **Gate de cobertura no CI.** Até o `app.py` sair (F7-4).
- **VM na Oracle.** Só se o fechamento precisar rodar com o PC desligado.
- **Lentes para ETFs e BDRs.** Fora do escopo; abstenção com motivo.
- **Lente para seguradoras.** Abstenção até existir lente própria.
- **Otimizador de carteira.** Não volta: a V2 descreve risco, não sugere alocação.
- **Canal externo de alerta** (e-mail, Telegram). O digest começa como página e arquivo.

## 15. Decisões pendentes

| Decisão | Quando | Insumo |
|---|---|---|
| Aceite de D5–D13 do ADR-0002 | checkpoint da Fase 0 | este plano |
| Scraper do Fundamentus | checkpoint da Fase 0 | F0-4 |
| Itens *investigar* do inventário | checkpoint da Fase 0 | F0-7 |
| Fila da Fase 1 | checkpoint da Fase 0 | F0-10 |
| Fonte oficial de Basileia e inadimplência | antes do F2A-9 | dossiê F0-6 |
| Limiares de divergência de ações e de liquidez | antes da Fase 2A | dossiê F0-6 |
| Prêmio de risco e vértice da NTN-B | antes da Fase 2B | dossiê F0-6 |
| Benchmark do FII (Selic líquida, NTN-B ou os dois) | antes da Fase 2B | dossiê F0-6 |
| Janela de cada método (último ano, TTM ou cinco anos) | antes da Fase 2C | dossiê F0-6 |
| Histerese, lentes e valuation reverso | antes da Fase 2C | dossiê F0-6 |
| Universo, profundidade histórica e reapresentações | antes da Fase 3 | teste de volume |
| Limites de concentração da camada de risco | Fase 4 | — |
| Canal do digest | Fase 4 | — |
| Janelas e referência do estudo de evento | antes da Fase 5 | — |
| Estágios 2–4 | fim da Fase 5 | F5-2 |
| PR por fase ou só push | a cada checkpoint | — |
