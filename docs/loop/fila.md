# Fila do loop — Fase 0 (Preparação)

Branch: `v2/fase-0` · Protocolo: `docs/loop/protocolo.md` · Diário: `docs/loop/diario.md`
Plano: `docs/PLANO.md` · Decisões: `docs/adr/0001-refactor-v2.md` e `docs/adr/0002-loop-tempo-dados.md`
Auditoria: `docs/auditoria/2026-09-red-team.md` (IDs de achado normalizados no F0-0)

**Intocáveis nesta fase:** `valuation_engine.py`, `fii_engine.py`, `portfolio_engine.py` e as seções `MacroContext` e `_normalizar_dy` de `config.py`.

**Privacidade:** o repositório é público. Nenhum dado da carteira do Marcos (posições, pesos, lista de ativos) entra em arquivo versionado; o que usar a carteira vai para `outputs/`.

Legenda: `[ ]` pendente · `[x]` feito · `[!]` bloqueado · `[DECISÃO]` o loop para aqui

## Itens

- [x] **F0-0** · docs · `docs: add red team audit with normalized finding IDs`
  A auditoria de 9/9 está em `docs/auditoria/2026-09-red-team.md`, ainda com a numeração quebrada. Normalizar sem mudar o conteúdo dos achados:
  - cada bloco ganha ID explícito no cabeçalho;
  - blocos financeiros: F-1 a F-15, com F-14 = conformidade regulatória (o que o Veredito chama de F-24) e F-15 = Markowitz mal rotulado;
  - a tabela de baixa severidade passa a começar em F-16;
  - a numeração de engenharia (E-*) fica como está;
  - referências cruzadas internas ("ver F-24" e afins) apontam para os IDs novos;
  - uma tabela "ID antigo → ID novo" no fim do documento.

  Depois, atualizar as citações de IDs F-* em `CLAUDE.md`, `AGENTS.md`, `docs/PLANO.md`, `docs/adr/0002-loop-tempo-dados.md` e nesta fila (por exemplo, F-25 e F-28).
  **Aceite:** todo achado com ID único e explícito; nenhuma referência a ID inexistente, na auditoria ou nos documentos do plano; tabela de correspondência presente.

- [x] **F0-1** · docs · `docs: sync agent instructions and plan with codebase`
  Validar `CLAUDE.md`, `AGENTS.md`, `docs/PLANO.md`, `docs/adr/0001-refactor-v2.md` e `docs/adr/0002-loop-tempo-dados.md` contra o código:
  - módulos e contagens de linha;
  - linhas citadas: `market_engine.py:377/503/513/519`, `config.py:308/311`, `app.py:158/227`, `brapi_provider.py:72`, `fundamentus_scraper.py:99`, `ai_core.py:121`, `valuation_engine.py:120-130`, `data_quality.py:170`;
  - regras econômicas descritas vs. comportamento testado;
  - IDs de achado (E-*, F-*) citados batem com a auditoria normalizada no F0-0;
  - fatos atribuídos ao código: `CVMFIIProvider`, `cost_of_equity_real`, `tecnico_negativo`, `dados.update(analise)`, `FII_MANUAL_FALLBACK`, `VACANCIA_CONHECIDA`;
  - armadilhas 14 a 17 do `CLAUDE.md`, que vieram da análise financeira: classe do ativo pelo sufixo, cobertura e atualizador dos mapas, Markowitz (um ano, 40/60, "Alocação Sugerida") e bancos.

  Divergiu: corrige o documento, nunca o código.
  **Aceite:** diff só nesses cinco arquivos; divergências listadas no diário.

- [x] **F0-2** · chore · `chore: add CI gate, strict xfail, hermetic fixtures and dev tooling`
  - (a) `.github/workflows/ci.yml` em push e pull_request, Python 3.13, rodando `ruff check --select E9,F63,F7,F82 .` e `python -m pytest tests/ --tb=short`, sem gate de cobertura.
  - (b) `pytest.ini`: `xfail_strict = true`, seção `markers` com os marks da seção B do F0-3 e `--strict-markers` em `addopts`, para que mark digitado errado vire erro.
  - (c) Fixture `autouse` de sessão em `tests/conftest.py` semeando a Selic de forma determinística, sem cair no fallback por exceção. `MACRO` é instanciado no import de `config`: prefira a abordagem que não mexe em `config.py` e justifique a escolha no diário. Se usar stub de `requests.get`, ele responde só à URL do BCB e levanta exceção em qualquer outra. Comentário no `conftest.py` apontando para o E-6: a fixture é contorno, não correção.
  - (d) Guarda de sessão permanente que falha a suíte em qualquer conexão de rede (`socket.connect`).
  - (e) `requirements-dev.txt` com `ruff`, `mutmut`, `pytest-cov`, `vulture` e `deptry`; `pytest-cov` sai do `requirements.txt`.
  - (f) `[tool.mutmut]` no `pyproject.toml` para o layout plano do projeto, fora de `tests/`, `venv/` e `backtesting/`, com `pytest_add_cli_args = ["-o", "xfail_strict=False"]`.
  - (g) `mutants/` no `.gitignore`.
  - (h) Conferir que os comandos de mutação do `CLAUDE.md` e do `AGENTS.md` funcionam, e atualizar a armadilha 7 do `CLAUDE.md` para refletir a fixture e a guarda novas.

  **Aceite:** workflow válido; suíte verde e hermética, sem aviso do BCB no stderr; a guarda de rede derruba um teste descartável que tenta conectar (o teste não é commitado); `xfail_strict` e `--strict-markers` ativos; `python -m mutmut run "technical_engine*"` termina e `python -m mutmut export-cicd-stats` gera os números; `git status` limpo depois da mutação.

- [x] **F0-3** · test · `test: add characterization safety net before refactor`
  `tests/test_financeiro_pre_refactor.py` com valores sintéticos, em três seções:
  - **A (preservar):**
    - com três métodos assimétricos (por exemplo 10, 12 e 40), o fair value é a mediana (12), não a média (20,67) — com só dois métodos, `statistics.median` devolve a média e o teste não verificaria nada;
    - com exatamente dois métodos, o resultado é a média dos dois, inclusive quando a flag de divergência (`max/min > 2`) dispara — com comentário explicando que é propriedade do `statistics.median`, comportamento atual que ninguém decidiu (a decisão é do F2C-5);
    - Bazin não dispara abaixo de 5%;
    - FII compara com Selic líquida.
  - **B (deve mudar):** caracteriza o estado atual de Gordon (taxa Selic nominal), FII, alavancagem por endividamento total e Markowitz (um ano, 40/60). Cada teste leva `# QUEBRA ESPERADA: <achado>` e `pytest.mark` próprio.
  - **C (invariantes):** DY em [0, 0.30], score em [0, 100], fair value e preço na mesma escala.

  **Aceite:** suíte verde; seções filtráveis por mark; mutation score de pelo menos um módulo no diário; teste que sobrevive a mutação não entra.

- [x] **F0-4** · levantamento · `docs: add Fundamentus scraper decision brief`
  Conflito E-11 (declarar `cloudscraper`) × F-25 (remover o scraper por ToS). Sem decidir e sem mudar código, escrever em `docs/decisoes/scraper-fundamentus.md`:
  - quantos campos dependem só do Fundamentus, e para quantos tickers;
  - o que quebra se o módulo sair (testes, cobertura, cascata);
  - se brapi + CVM cobrem esses campos no universo mapeado.

- [x] **F0-5** · docs · `docs: add Jules backlog`
  `docs/jules-backlog.md` em três grupos:
  - **A:** configuração para o Jules revisar os PRs de fase.
  - **B:** um ticket por módulo com especificação externa (`technical_engine`, `fundamentus_scraper._limpar_valor`, `database.adicionar_posicao`, `cvm_provider`). Aceite = mutation score ≥ 80% com o mutmut 3, com aviso explícito de que um teste vermelho pode ser o resultado correto — o RSI hoje devolve 50 onde Wilder manda 100.
  - **C:** achados de baixa severidade agrupados por arquivo tocado, marcando os sequenciais.

  Todo ticket respeita os arquivos travados por fase (`docs/PLANO.md`, seção 8). Os de `cvm_provider.py` (E-7, E-8, E-20) ficam agendados para a Fase 1 e precisam terminar antes da Fase 2A.
  Cada ticket leva título Conventional Commit, arquivos, cenário de falha, correção esperada e aceite com nome do teste. Não abrir issues.

- [x] **F0-6** · levantamento · `docs: add phase 2 decision dossier`
  Em `docs/decisoes/dossie-fase2.md`, com o script em `scripts/dossie_fase2.py`, sem alterar módulos de produção. Amostra: os tickers dos mapas atuais, nunca a carteira.
  - **E-1:** ações da Composição do Capital da CVM (ON + PN − tesouraria, na escala do documento) contra o `sharesOutstanding` do yfinance, ticker a ticker; divergências acima de 5%, casos com duas classes de ação e efeito no LPA, VPA e P/L.
  - **Taxas:** fair value por método com a Selic de 10% a 15% em passos de 0,5 (incluindo 13,75%) e com k real a partir da NTN-B longa mais três níveis de prêmio. Para variar as taxas, usar o mesmo mecanismo da fixture do F0-2.
  - **Gordon:** regime atual × opção A (k e g reais) × opção B (ajuste nominal).
  - **FII:** DY contra a Selic líquida × spread sobre a NTN-B.
  - **Cinco anos:** LPA e dividendos do último ano × média de cinco anos, e quanto isso muda cada método.
  - **Bancos:** se Basileia e inadimplência estão disponíveis em fonte oficial do Banco Central, e P/VP justificado pelo ROE para os bancos da amostra.
  - **Cobertura e classe:** quantas companhias e FIIs listados dá para mapear automaticamente pela CVM/B3, e quantos tickers a regra atual classifica errado (ETF como FII, BDR como ação, units).

  O mesmo recorte de cobertura, classe e bancos aplicado aos ativos da carteira do Marcos vai para `outputs/dossie-carteira.md`, fora do git. Rede só para leitura (CVM, B3, Banco Central, yfinance). O documento termina com as perguntas que o Marcos precisa responder.

- [x] **F0-7** · levantamento · `docs: add residue inventory`
  Em `docs/limpeza/inventario.md`, sem remover nada:
  - código morto com `python -m vulture .` (confiança ≥ 80%; abaixo disso, lista separada);
  - `ruff check --select F401,F841,ERA001 .` — imports e variáveis sem uso, código comentado;
  - a dívida do `ruff check .` completo (301 erros em 1º/10), separando as correções automáticas seguras (UP045, UP006, ordem de imports) das que mudam comportamento (como BLE001, `except` genérico);
  - `deptry .` — dependências sem uso, faltando ou só transitivas;
  - módulos órfãos: `.py` que nada importa e que não são ponto de entrada;
  - arquivos rastreados que deveriam ser ignorados (`*.db`, `__pycache__`, `outputs/`, logs) e lacunas no `.gitignore`;
  - duplicidades conhecidas: `FII_MANUAL_FALLBACK` × `VACANCIA_CONHECIDA`, MGLU3 no mapa de pares e na lista de distressed, constantes do `MacroContext` sem leitor;
  - documentação que cita arquivo, caminho ou comando que não existe mais, incluindo caminhos do Windows;
  - branches locais e remotos já integrados à `main`.

  Cada achado recebe uma categoria: **remover já** (sem efeito em comportamento), **remover na fase X** (com o item do `docs/PLANO.md`), **investigar** (uso incerto — chamado por nome, callback do Streamlit, acesso por outro módulo) ou **manter** (falso positivo, com motivo).

- [x] **F0-8** · limpeza · `chore: remove pure residue`
  Só os itens **remover já** do inventário, fora dos intocáveis:
  - arquivo rastreado sai com `git rm`; artefato que deve continuar existindo localmente (como o banco `.db`) sai com `git rm --cached`;
  - lacunas do `.gitignore` corrigidas;
  - import sem uso só sai depois de confirmar por busca que nenhum módulo o acessa através daquele arquivo — em especial o `app.py`, que tem cobertura 0%;
  - falsos positivos vão para `vulture_whitelist.py`, com o motivo em comentário.

  Não apaga arquivo não rastreado nem branch: esses vão para a lista do Marcos no diário.
  **Aceite:** suíte verde; seções A, B e C do F0-3 inalteradas; inventário atualizado com o que saiu.

- [x] **F0-9** · chore · `chore: quarantine V1 outputs under methodological review`
  Só no `app.py`, sem tocar em módulo de cálculo:
  - aviso fixo em todas as abas: resultados em revisão metodológica, com link para o `docs/PLANO.md` — não usar para decisão;
  - a "Alocação Sugerida" do Markowitz deixa de ser exibida (o cálculo continua até o F2C-9);
  - resultados de backtest, onde aparecerem, marcados como baseados em fundamentos sintéticos, ou retirados da tela.

  **Aceite:** suíte verde; seções A, B e C inalteradas; o app sobe sem erro. A conferência visual fica para o Marcos no checkpoint.

- [x] **F0-10** · levantamento · `docs: propose phase 1 queue`
  O `fable-architect` propõe a fila da Fase 1 em `docs/loop/fila-fase1-proposta.md`, a partir da seção "Fase 1" do `docs/PLANO.md`:
  - um item por commit, com tipo, escopo e aceite;
  - gate = seções A, B e C do F0-3 inalteradas;
  - refactor e mudança de comportamento nunca no mesmo item;
  - itens que dependem das propostas D5, D9 e D11 do ADR-0002 marcados;
  - penúltimo item: limpeza da Fase 1, com os resíduos do inventário marcados para ela; último item: resumo e arquivamento.

  Nada é implementado.

- [ ] **F0-11** · docs · `docs: add phase 0 summary and archive loop files`
  Nesta ordem:
  1. escrever `docs/loop/pr-fase-0.md` a partir do diário: itens e commits, testes antes → depois, decisões pendentes, resíduos que ficaram para o Marcos e o que revisar primeiro;
  2. registrar este item no diário e marcá-lo `[x]`;
  3. `git mv` de `fila.md`, `diario.md` e `pr-fase-0.md` para `docs/loop/historico/fase-0/`;
  4. criar um `docs/loop/fila.md` novo contendo só:
     `[DECISÃO] Fase 0 encerrada. Histórico em docs/loop/historico/fase-0/. Próxima fila aguardando aprovação: docs/loop/fila-fase1-proposta.md.`
  5. commit e `cat docs/loop/fila.md`.

- [DECISÃO] **Fim da Fase 0.** O Marcos:
  1. revisa o F0-3, que é o gate da Fase 1;
  2. decide o F0-4 e os itens **investigar** do inventário;
  3. confere a quarentena no app (F0-9);
  4. lê o dossiê, inclusive a parte da carteira em `outputs/`;
  5. aceita ou recusa D5–D13 do ADR-0002;
  6. aprova a fila da Fase 1;
  7. faz o push do branch `v2/fase-0` — com PR da fase, se quiser, usando `docs/loop/historico/fase-0/pr-fase-0.md` como corpo;
  8. com o push confirmado no GitHub, arquiva a cópia do `E:\` (zip no Google Drive) e apaga essa cópia, a venv do Windows e os arquivos não rastreados listados no resumo.
