# Sentinela B3

**Plataforma educacional de análise de ações e FIIs da B3, local-first, com dados oficiais, métodos explícitos e rastreabilidade.**

[![CI](https://github.com/Marcos-Felipe-dos-Santos/Sentinela-B3/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/Marcos-Felipe-dos-Santos/Sentinela-B3/actions/workflows/ci.yml)
![Python 3.13](https://img.shields.io/badge/Python-3.13-blue)

O projeto está em migração gradual da V1 para a V2. A interface atual usa **Streamlit**; a evolução prioriza a qualidade dos dados e a validade dos métodos antes da nova interface.

> Uso educacional e apoio ao estudo. Não constitui consultoria financeira, não emite ordens e não oferece recomendação de compra, venda ou alocação.

## O que está acontecendo no GitHub

**Retrato da `main` consultada em 25/10/2026, até o commit [`5da63b2`](https://github.com/Marcos-Felipe-dos-Santos/Sentinela-B3/commit/5da63b2).** Este resumo descreve o que está publicado; trabalho ainda local não é contado como entregue.

| Frente | Situação publicada | Evidência |
|---|---|---|
| Fase 0 — Preparação | Integrada: auditoria, CI, testes de caracterização e decisões iniciais | [Resumo da fase](docs/loop/historico/fase-0/pr-fase-0.md) |
| Fase 1 — Fundação | Integrada: tipos de unidade, contrato dos métodos, extração das fórmulas e registro de métodos | [PR #10](https://github.com/Marcos-Felipe-dos-Santos/Sentinela-B3/pull/10) · [Resumo](docs/loop/historico/fase-1/pr-fase-1.md) |
| Fase 2A — Dados corretos | Integrada, incluindo o fechamento das auditorias; permanecem bugs conhecidos com destino registrado | [PR #22](https://github.com/Marcos-Felipe-dos-Santos/Sentinela-B3/pull/22) · [Resumo e fechamento](docs/loop/historico/fase-2a/pr-fase-2a.md) |
| Fase 2B — Taxa real, bancos e escopo | Concluída (tag `v2-fase-2b`), com a fila de fechamento da auditoria externa: taxa real, Gordon real, Bazin pela B3, FII sobre NTN-B + spread, lente de bancos, escopo pelo modelo das demonstrações e liquidez mínima. Cinco fichas aprovadas (taxa real, Gordon, Bazin, FII e bancos) | [PR #24](https://github.com/Marcos-Felipe-dos-Santos/Sentinela-B3/pull/24) · [PR #25](https://github.com/Marcos-Felipe-dos-Santos/Sentinela-B3/pull/25) · [Resumo](docs/loop/historico/fase-2b/pr-fase-2b.md) · [Fila da fase](docs/loop/historico/fase-2b/fila.md) |
| Fase 2C — Qualidade e apresentação | Em proposta, **não ativa**: aguarda auditoria DOCUMENTO e as decisões marcadas no texto | [Proposta da 2C](docs/loop/fila-fase2c-proposta.md) |
| Processo de desenvolvimento | Workflow entre ferramentas, ciclo de fase e prompts de auditoria versionados | [Workflow](docs/loop/workflow-multiagente.md) · [Ciclo de fase](docs/loop/ciclo-de-fase.md) |

**Próximo passo registrado:** auditar a proposta da 2C, resolver seus marcadores `[DECISÃO]` e ativar a fila. A proposta não aprova método, parâmetro nem janela. A [fila atual](docs/loop/fila.md) ainda traz o marcador de encerramento da 2B até a ativação da 2C.

**Escopo das ações.** Dos 455 ativos STOCK/UNIT do índice oficial, 346 seguem o modelo de empresa (Graham, Bazin, Lynch e Gordon) e 22 o de banco (lente de P/VP justificado); 9 de seguradoras e **78 de companhias que publicam só demonstrações individuais**, sem balanço consolidado, se abstêm de todos os métodos, sem número.

Acompanhe o estado atualizado pelos [commits da main](https://github.com/Marcos-Felipe-dos-Santos/Sentinela-B3/commits/main/), [pull requests](https://github.com/Marcos-Felipe-dos-Santos/Sentinela-B3/pulls) e [execuções do CI](https://github.com/Marcos-Felipe-dos-Santos/Sentinela-B3/actions/workflows/ci.yml). O badge acima consulta o CI; as tabelas deste README são um retrato datado.

## O que já existe

- **Aplicação local:** interface Streamlit, gráficos Plotly e persistência SQLite.
- **Métodos de análise:** Graham, Bazin, Lynch, Gordon e lentes de FII, extraídos para `sentinela/methods/`, com contratos, versões e motivos de abstenção.
- **Referência oficial de ativos:** associação entre ticker, emissor, CNPJ, código CVM e classe, substituindo decisões baseadas apenas no sufixo do ticker.
- **Dados contábeis:** DFP/ITR da CVM, leitura de contas por código e descrição, composição do capital, informações por ação e dívida financeira líquida.
- **Séries contábeis:** infraestrutura para cinco exercícios e TTM. A escolha da janela de cada método e correções pendentes não estão concluídas.
- **FIIs e bancos:** Informe Mensal da CVM e eventos da B3 na lente de rendimento dos FIIs de tijolo; lente de bancos por P/VP justificado, com o IF.data (Basileia e inadimplência) só como contexto.
- **Rastreabilidade:** proveniência temporal, verificações de consistência e relatório de qualidade dos dados.
- **Mercado:** preços e histórico, indicadores técnicos e métricas de liquidez com COTAHIST.
- **Assistente de texto opcional:** integração com provedores de IA, separada da definição das fórmulas financeiras.

As entregas e suas limitações estão detalhadas no [resumo da 2A](docs/loop/historico/fase-2a/pr-fase-2a.md). “Implementado” não significa ausência de defeitos: o [registro de regressões](tests/regressao/README.md) identifica os bugs confirmados, os corrigidos e os ainda abertos.

## Arquitetura atual

```text
Streamlit (app.py)
    ├── Coleta e enriquecimento (market_engine.py)
    │   ├── Referência oficial do ativo
    │   ├── yfinance → brapi → CVM
    │   ├── IF.data para bancos / Informe Mensal para FIIs
    │   └── COTAHIST, qualidade, proveniência e cache
    ├── Motores de ações e FIIs → sentinela/methods/
    ├── Indicadores técnicos e relatórios
    └── Persistência local em SQLite
```

A sequência resume a orquestração, não uma garantia de prioridade uniforme por campo. O preço vem preferencialmente do yfinance, com brapi como alternativa; os fundamentos são enriquecidos pela CVM. **O Fundamentus foi retirado da cascata.** Dados ausentes ou inconsistentes precisam aparecer como limitações ou abstenções; os desvios conhecidos estão no registro de regressões.

O pacote `sentinela/services/` já existe, mas a ligação da aplicação ao serviço com `as_of` está prevista para a Fase 3. **FastAPI + HTMX é a interface planejada para a Fase 7**, não a interface atual.

| Camada | Tecnologias e fontes |
|---|---|
| Linguagem e ambiente de desenvolvimento | Python 3.13, WSL2/Linux |
| Interface atual | Streamlit e Plotly |
| Dados | CVM, B3/COTAHIST, IF.data, yfinance e brapi |
| Contexto macroeconômico | BCB SGS e Tesouro Direto |
| Processamento | Pandas e NumPy |
| Persistência | SQLite |
| Verificação | pytest, Ruff e testes de mutação com mutmut |

## Plano de evolução

O [plano completo](docs/PLANO.md) define a direção. A [fila](docs/loop/fila.md), os [ADRs](docs/adr/) e as decisões de ativação determinam o trabalho efetivo; este resumo não substitui seus critérios de aceite.

| Fase | Objetivo | Estado nesta main |
|---|---|---|
| 0 | Auditoria, CI, caracterização e preparação | Integrada |
| 1 | Tipos, contratos e métodos separados dos motores | Integrada |
| 2A | Identificação oficial, dados contábeis, unidades e proveniência | Integrada, com pendências rastreadas |
| 2B | Corrigir pendências de dados; revisar taxas, métodos, bancos, escopo e liquidez | Integrada (tag `v2-fase-2b`), com pendências rastreadas |
| 2C | Janelas por método, qualidade empresarial, apresentação por lentes e retirada do otimizador | Em proposta, não ativa |
| 3 | Tempo como entrada, histórico ponto-no-tempo, migrações e backtest reproduzível | Planejada |
| 4 | CLI, fechamento diário, backup restaurável, rastreabilidade e descrição de risco | Planejada |
| 5 | Fatos relevantes e estudo de evento antes de expandir notícias | Planejada; expansão depende dos resultados |
| 6 | Documentação, demonstração e consolidação da vitrine técnica | Planejada |
| 7 | Interface FastAPI + HTMX e conclusão da migração da V1 | Planejada |
| 8 | IA para explicar premissas e limitações; expansão condicional das notícias | Condicional |

A 2C exige fichas e decisões explícitas sobre janelas, qualidade, classificação e apresentação. **Trocar uma taxa ou escolher um modelo não é uma correção automática:** fórmula, insumos, regime, hipóteses, exemplo independente e sensibilidade precisam estar documentados e aprovados.

Referências: [fichas metodológicas](docs/metodologia/README.md), [ficha por ação](docs/metodologia/por-acao.md), [ADR-0003 — validade de dados e método](docs/adr/0003-validade-dados-metodo-auditoria.md) e [proposta detalhada da 2C](docs/loop/fila-fase2c-proposta.md).

## Limitações e trabalho pendente

- **Dados e cálculos ainda têm bugs conhecidos.** Há regressões abertas sobre valores não positivos da CVM, TTM, dados por ação e outros casos; consulte o registro para o estado de cada uma.
- **Histórico ponto-no-tempo ainda não está concluído.** Guardar proveniência agora não torna o backtest legado uma validação histórica confiável.
- **Metodologia em revisão.** Os métodos existentes não representam a implementação final da V2; janelas, qualidade e apresentação ainda serão revistas na 2C.
- **Cobertura de ativos delimitada.** Não há promessa de atender todos os listados. O [universo inicial](docs/decisoes/universo-inicial.md) documenta casos e exclusões; as companhias só com demonstrações individuais e as seguradoras se abstêm até uma decisão de escopo da 2C.
- **Fontes externas podem falhar ou mudar de formato.** Qualidade, atualidade e disponibilidade precisam acompanhar os resultados.
- **Operação e interface ainda estão em migração.** Há orquestração na V1; histórico unificado, rotina diária e nova interface são entregas futuras.
- **Deploy público está adiado.** O foco continua local-first. O plano não prevê retomar sugestão automática de alocação de carteira.

## Como o desenvolvimento é coordenado

O projeto usa uma fila compartilhada e **um executor por item**, com passagem de contexto quando há troca de ferramenta. Auditoria externa usa uma família de modelo diferente da que executou o trabalho.

Decisões metodológicas ficam com o mantenedor. Git, fila, diário e ADRs são a referência; memória de IA auxilia a retomada, mas não substitui evidência. Bugs confirmados recebem regressão antes da correção, e a correção só fecha com o teste passando sem a marca de falha esperada.

Leia o [workflow multiagente](docs/loop/workflow-multiagente.md), o [ciclo de fase](docs/loop/ciclo-de-fase.md), as [regras para agentes](AGENTS.md) e o [backlog do Jules](docs/jules-backlog.md) antes de contribuir.

## Instalação e execução local

Ambiente de referência: Python 3.13 em WSL2/Linux.

```bash
git clone https://github.com/Marcos-Felipe-dos-Santos/Sentinela-B3.git
cd Sentinela-B3
python3.13 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

A interface abre em `http://localhost:8501`. As integrações de IA são opcionais; a disponibilidade de dados depende das fontes externas. Credenciais devem permanecer na configuração local e nunca ser incluídas em commits.

## Testes e evidências

O fechamento documentado da 2B registrou **2.575 testes passando, 1 ignorado e 14 falhas esperadas (`xfail`)** e mutation score de **93,2%** em `sentinela/methods` (1.183/1.269). Esses números são históricos, não uma medição automática deste README. Consulte o [resumo da 2B](docs/loop/historico/fase-2b/pr-fase-2b.md) e o CI para os resultados de cada revisão.

```bash
pip install -r requirements-dev.txt
python -m pytest tests/ --tb=short -rxX
ruff check --select E9,F63,F7,F82 .
```

O [CI](.github/workflows/ci.yml) bloqueia falhas de pytest e do conjunto de regras Ruff acima. Ruff completo, código morto e dependências também aparecem como relatórios; não são todos gates bloqueantes.

Os `xfail` tornam limitações conhecidas visíveis, não demonstram que elas foram corrigidas. Testes verdes e mutation score também não substituem referências independentes para fórmulas, insumos e premissas.

## Mapa da documentação

- [Plano da V2](docs/PLANO.md) — direção, fases e dependências.
- [Fila atual](docs/loop/fila.md) e [proposta da 2C](docs/loop/fila-fase2c-proposta.md) — situação do trabalho e próxima etapa.
- [Histórico por fase](docs/loop/historico/) — entregas, diários e auditorias.
- [Decisões arquiteturais](docs/adr/) e [metodologia](docs/metodologia/) — critérios e justificativas.
- [Regressões conhecidas](tests/regressao/README.md) — bugs e destino das correções.
- [Proveniência](docs/provenance.md) — documentação de origem dos dados.

Desenvolvido por **Marcos Felipe dos Santos**, como projeto de engenharia de software e estudo de dados financeiros brasileiros.

## Licença

MIT — uso pessoal e educacional.
