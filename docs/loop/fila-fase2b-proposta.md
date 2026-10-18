# Fila do loop — Fase 2B (Taxa real, bancos e escopo)

> **Proposta, não ativa.** Escrita no F2A-28 pelo `fable-architect` e revisada em 18/10/2026, em duas rodadas: a primeira com a auditoria externa da 2A (`docs/loop/historico/fase-2a/auditoria-externa.md`, seção "Correções da proposta da 2B") e as decisões de ativação do Marcos (última seção); a segunda com a primeira auditoria DOCUMENTO desta proposta e a primeira auditoria FICHA da ficha por ação 1.1 (três bloqueios em cada uma, corrigidos com decisões do Marcos do mesmo dia). Quem a coloca em `docs/loop/fila.md` é o Marcos, depois de cumprir as condições de ativação.

Branch: `v2/fase-2b` · Protocolo: `docs/loop/protocolo.md` · Diário: `docs/loop/diario.md`
Plano: `docs/PLANO.md` (seção 6, "Fase 2B"; seções 8, 10, 11, 13 e 15) · Decisões: `docs/decisoes/checkpoint-fase0.md` (seção 4, itens 2, 3 e 5) e `docs/adr/0002-loop-tempo-dados.md` (D7, D11 e D15) · Validade: `docs/adr/0003-validade-dados-metodo-auditoria.md` (D16, D19 a D23, D27, D28 e D30) · Auditoria externa: `docs/loop/auditoria-externa.md`
Auditoria: `docs/auditoria/2026-09-red-team.md` (F-4, F-5, F-6, F-9 e F-11) · Dossiê: `docs/decisoes/dossie-fase2.md` (perguntas 2, 3 e 5) · Fontes: `docs/decisoes/fontes-fase2a.md` · Fichas: `docs/metodologia/` · Universo: `docs/decisoes/universo-inicial.md` · Inventário: `docs/limpeza/inventario.md` · Jules: `docs/jules-backlog.md` · Fase 2A: `docs/loop/historico/fase-2a/` (com `auditoria-gemini-completa.md`)

**Condições de ativação** (todas, antes do `git mv`; ciclo em `docs/loop/ciclo-de-fase.md`):
1. Fase 2A integrada na `main` com a tag `v2-fase-2a` (feito em 15/10/2026) e os restos do [DECISÃO] dela: limpeza do cache (passo 4) e caches apagados à mão (passo 9). A limpeza pode ser da tabela inteira, sem lista de tickers (`python -c "import sqlite3; c = sqlite3.connect('sentinela_v6.db'); c.execute('DELETE FROM fundamentals_cache'); c.commit()"`), ou por ticker com `python scripts/invalidar_cache_cvm.py TICKER...` (primeiro sem `--aplicar`, que só lista; depois com ele).
2. Ficha por ação na versão 1.1 (pontos da **[FICHA 1.1]**, decididos em 18/10/2026; seções 7.7 a 7.10, revistas depois da primeira auditoria), auditada em modo FICHA até "pode seguir" (`python scripts/auditar.py codex ficha --fase 2b --arquivo docs/metodologia/por-acao.md --foco "a versão 1.1: seções 7.7 a 7.10 e as mudanças nas seções 2 e 4; refaça por conta própria as contas que elas citam"`) e marcada "aprovada" pelo Marcos.
3. Decisões de ativação respondidas pelo Marcos em 18/10/2026 (última seção): **[SEÇÃO A]** em (c), **[LIQUIDEZ]**, **[FICHA 1.1]** e **[AUDITORIA]**.
4. Auditoria externa desta proposta em modo DOCUMENTO (`python scripts/auditar.py codex documento --fase 2b --arquivo docs/loop/fila-fase2b-proposta.md`), com "pode seguir" ou "pode seguir com ressalvas", e as correções que o Marcos aceitar feitas por commit dele.
5. Ativação (ciclo, etapa 3): `git switch -c v2/fase-2b main`, `git mv -f docs/loop/fila-fase2b-proposta.md docs/loop/fila.md` e `git commit -m "chore: activate phase 2B queue"`.
6. O Marcos troca a seção "Fase atual" do `AGENTS.md` pelo texto abaixo. O loop nunca toca nessa seção.

```
**Fase 2B — Taxa real, bancos e escopo.** O mantenedor trabalha num branch local por fase e só
publica no fim de cada fase. Baseie seu branch sempre na `main` mais recente.

Arquivos travados enquanto esta fase estiver em andamento. Não abra PR que toque
em nenhum deles:

market_engine.py  cvm_provider.py  cvm_fii_provider.py  fii_engine.py  valuation_engine.py
data_quality.py  config.py  ai_core.py  pytest.ini  vulture_whitelist.py
sentinela/data/  sentinela/domain/  sentinela/methods/  sentinela/services/  sentinela/reports/
scripts/  tests/conftest.py  tests/fixtures/  tests/golden_motores.py
tests/test_market_engine*.py  tests/test_cvm_*.py  tests/test_fii_*.py  tests/test_valuation_*.py
tests/test_data_quality*.py  tests/test_methods_*.py  tests/test_registry.py  tests/test_rastreabilidade.py
tests/test_acoes_cvm.py  tests/test_controladores.py  tests/test_contas_cvm*.py  tests/test_referencia*.py
tests/test_asset_classifier*.py  tests/test_saidas_finitas.py  tests/test_roe_fronteira.py
tests/test_dy_fronteira.py  tests/test_liquidez*.py  tests/test_macro_context.py  tests/test_units.py
tests/test_contratos_*.py  tests/test_invalidar_cache_cvm.py  tests/test_tesouro.py  tests/test_taxa*.py
tests/regressao/  tests/test_cotahist.py

Tickets com janela nesta fase, se ainda abertos: B1, B3, C-A, C-B e C-C (a última janela
do C-C). B2, C-D e C-E não têm mais janela.
```

**Linhas citadas.** São de 15/10/2026, conferidas em 18/10/2026 contra a `main` (nenhum desses arquivos mudou no fechamento da 2A), e só em arquivos que os tickets do Jules não mexem antes da ativação: `config.py`, `valuation_engine.py`, `app.py`, `sentinela/methods/` (menos `base.py`) e `tests/test_financeiro_pre_refactor.py`. Nos demais arquivos, a fila cita a função.

**Comportamento.** Esta fase troca a taxa e o escopo dos métodos, então muda número e texto na saída.
- Cada mudança tem um item `fix:` próprio, com teste xfail estrito antes (xfail estrito → correção → marca retirada → PASS; ADR-0003, D27), e nunca divide o commit com refactor. Nenhum item desta fila é `refactor:`.
- Os itens `feat:` acrescentam dado, tipo ou método sem mudar a saída dos motores: F2B-27, F2B-28, F2B-29, F2B-30 e F2B-3.
- Saída dos motores muda (e por isso o golden) só nos itens marcados **[golden]**: F2B-4 e F2A-10 (estes, só com inclusões), F2B-20, F2B-1, F2B-31, F2B-2, F2B-32 e F2B-45. Nenhum item `chore:` muda o golden (auditoria externa da 2A).
- **Bugs e regressão** (`tests/regressao/README.md`; ciclo, seção 4). Cada item que corrige um BUG registrado retira a marca do teste de regressão dele, que passa a PASS, e atualiza o registro. Bug novo que o loop confirmar vira teste de regressão no item em que aparece, ou no F2B-43, antes de qualquer correção.
- Os demais itens mudam a cascata (`dados`), o índice, o relatório de qualidade ou o relatório do F1-12.

**IDs e ordem.** F2B-1 a F2B-6, F2A-10 e F2A-39 mantêm o significado da tabela do PLANO; o F2B-3 do PLANO se divide em F2B-3 (o método) e F2B-32 (a ligação no motor). F2B-7 a F2B-34 vêm da primeira versão desta proposta; F2B-35 a F2B-45, da revisão de 18/10/2026, numerados na ordem em que aparecem. Saíram na revisão, porque o fechamento da 2A os resolveu: F2B-9 (F2A-41), F2B-15 (F2A-43) e F2B-19 (F2A-42). A execução segue a ordem da lista, não a numérica:
1. abertura: instruções dos agentes, registro dos bugs do IF.data e seção A;
2. correções de dados decididas na ativação: valores ≤ 0 da CVM, ficha por ação 1.1, FII na cascata e na qualidade, ROE, preço e os bugs abertos da 2A;
3. levantamento das taxas e das fontes, e o registro dos bugs que ele confirmar;
4. fichas: taxa real, Gordon, Bazin, FII e bancos;
5. dado sem consumidor: rendimento do FII pelo Informe;
6. marcador das fichas, da taxa e das fontes;
7. Tesouro, contrato e taxa real;
8. métodos: Gordon, Bazin e FII;
9. escopo: BTG, `applies_to`, IF.data e bancos;
10. liquidez;
11. documentação, proposta da 2C, texto de dívida, limpeza e resumo.

**Intocáveis nesta fase:**
- `tests/test_financeiro_pre_refactor.py`:
  - seção A: muda só no F2B-7 (**[SEÇÃO A]** em (c)); depois dele, não muda;
  - seção B: recebe no F2B-7 os números da seção A que dependem da taxa, com `quebra_esperada`; muda depois só no F2B-1 (os dois testes do F-4, `:115` e `:125`, e os que o F2B-7 marcou com o F-4), no F2B-31 (os marcados com o F-5) e no F2B-2 (`test_b_fii_nao_considera_o_patrimonio_no_fair_value`, `:135`: muda o número do benchmark, e o teste continua caracterizando o F-9, porque o P/VP fica como contexto pelo checkpoint; e os marcados com o F-9);
  - seção C: não muda.
- `tests/fixtures/golden_motores.jsonl` e `tests/golden_motores.py`: só nos itens **[golden]**, pela regra abaixo. `tests/test_equivalencia_motores.py` não muda.
- `config.py`:
  - `_normalizar_dy` não muda;
  - as constantes que o harness do golden lê para montar as ids (as de DY, `BAZIN_DY_MIN`, `BAZIN_DY_ARMADILHA`, `GORDON_DY_MIN`, `ROE_CRESCIMENTO_MIN`, `GORDON_ROE_MIN`, `ROE_PENALIDADE_MAX`, as do Graham e as de P/VP do FII) não mudam; se uma ficha aprovada mudar uma delas, o item declara o `--par` de cada id renomeada;
  - constante nova, só nos itens que a pedem: F2B-30, F2B-1, F2B-31, F2B-2, F2B-32 e F2A-10; constante sem leitor sai só no F2B-5;
  - `get_selic_atual` e `SELIC_FALLBACK` ficam: contexto do FII, Markowitz até o F2C-9, E-6 no F3-1. `FII_MANUAL_FALLBACK` sai no F2C-10.
- `app.py` (Fases 3 e 7) e `portfolio_engine.py` (F2C-9) não mudam. O que o app precisa mostrar chega pelos motores; a taxa real aparece no relatório do F1-12, não na tela (resíduo do F3-6).
- Itens que podem mexer em cada arquivo restrito:
  - `valuation_engine.py`: F2B-20, F2B-1, F2B-31, F2B-4, F2B-32, F2A-10, F2B-45 e F2B-5;
  - `fii_engine.py`: F2B-20, F2B-2 e F2A-10;
  - `sentinela/methods/`: F2B-41 (`fii_nav.py`) e F2B-42 (`graham.py`), F2B-29 e F2B-4 (`base.py`), F2B-4 também nos módulos dos seis métodos (versão menor e escopo declarado em cada um), F2B-1 (Gordon), F2B-31 (Bazin), F2B-2 (rendimento do FII), F2B-3 (`bancos.py`), o `registry.py` em cada um deles, e F2B-5 (remoções). O contrato de pureza do F1-10 vale para tudo;
  - `config.py`: F2B-30, F2B-1, F2B-31, F2B-2, F2B-32, F2A-10 e F2B-5;
  - `tests/conftest.py`: F2B-30 (semente da taxa real); `pytest.ini`: F2B-7;
  - `tests/regressao/`: F2B-36 e F2B-43 (registro); qualquer item que confirmar um bug novo, que grava o teste xfail estrito e a linha do registro antes da correção (`BUG-2B-NN`); e o item que corrige cada bug (marca retirada e registro). Os testes de comportamento que os itens nomeiam fora desse diretório (F2B-18, F2B-20, F2B-45 e outros) seguem o rito da D27 no próprio arquivo.
- Os singletons dos motores (`_GRAHAM`, `_BAZIN`, `_LYNCH`, `_GORDON`, `_FII_YIELD`, `_FII_NAV` e o novo dos bancos): nenhum item os renomeia sem atualizar `sentinela/reports/rastreabilidade.py` no mesmo commit.
- Arquivos dos tickets do Jules com janela nesta fase: `peers_engine.py` e `tests/test_peers_engine.py` (C-C), `technical_engine.py` (B1), `database.py` (B3), `README.md` (C-A) e `.env.example` (C-B). Nenhum item os toca.
- Teste existente só muda onde o item manda; a lista está em cada item, e a justificativa, no diário.

**Regra do golden** (a da 2A, decidida pelo Marcos em 5/10/2026, opção (a); esta proposta a mantém):
- Item **[golden]** regenera com `GERAR_GOLDEN=1 python -m pytest tests/test_equivalencia_motores.py::test_gerar_golden`, no mesmo commit da mudança.
- `python scripts/golden_diff.py --onde "<predicado do item>"` sai com 0: toda linha alterada satisfaz o predicado. Inclusões e remoções, só onde o item declara.
- O diário traz o predicado, a contagem, as ids (até 50; acima disso, a contagem por grupo) e o tamanho do arquivo.
- Item sem **[golden]**: `git diff --exit-code HEAD -- tests/fixtures/golden_motores.jsonl` antes do stage.
- **Taxa no harness.** O F2B-1 acrescenta a cada caso a taxa real (NTN-B e inflação), com o valor padrão igual ao da semente do F2B-30, e substitui o ponto de entrada da taxa nos dois motores, como hoje faz com `get_selic_atual`. A chave nova não conta como alteração: o `golden_diff.py` compara só a `saida`. As ids não mudam; a parte "selic" delas fica, e o diário de cada item de taxa registra que ela deixou de mover o método.

**Gate da fase (todo item):**
- `git diff v2-fase-2a -- tests/test_financeiro_pre_refactor.py` mostra só as mudanças previstas, depois dos itens que as fazem;
- o golden segue a regra acima;
- `python -m pytest -q` e `ruff check --select E9,F63,F7,F82 .` verdes;
- `ruff check sentinela/methods/ sentinela/data/` verde, com as regras completas;
- mutação:
  - `sentinela.methods*` ≥ 80% em todo item que muda método (hoje 100%), por módulo no diário;
  - módulos novos ou alterados de `sentinela/data/` e de `sentinela/domain/`: ≥ 80% no item que os cria ou altera;
  - módulos V1 tocados: o score vai para o diário, sem meta;
- método só muda com a ficha aprovada (D21); o exemplo da ficha vira teste, com o valor tirado dela (D28). Exceção decidida pelo Marcos em 18/10/2026 ([AUDITORIA]): as guardas de validade de insumo do F2B-41 e do F2B-42 (P/VP ≤ 0 e VPA ≤ 0 viram abstenção), que não mudam fórmula, regime nem parâmetro, entram sem ficha, com versão menor. Também sem ficha, por dispensa do Marcos de 18/10/2026 limitada a isso: a aplicação do escopo declarado (classe do ativo e modelo da demonstração) nos seis métodos, no F2B-4, que não muda fórmula, insumo, regime nem parâmetro. Graham, Lynch e o P/VP do FII ganham ficha quando a fórmula deles mudar (2C).

**Rito dos dados:**
- **Onde fica o código.** Lógica nova de dado vira função pura em `sentinela/data/`, e o `market_engine.py` só orquestra. Os provedores da raiz ficam onde estão.
- **Isolamento.** Os módulos novos não importam `config`, que faz rede no import (armadilha 8). O teste do F1-10 impede `sentinela/methods/` de importar `sentinela/data/`.
- **Download.** Com cache em `data/` (ignorado pelo git) e TTL. O módulo do B4.3 (`cvm_download`) serve a ZIP; CSV e JSON seguem o padrão do `ifdata.py`. Se a rede falha, vale o cache, com aviso e com a data dele. Nada de rede no import.
- **Testes.** Sem rede, com arquivos sintéticos em `tmp_path` montados pela especificação oficial, nunca a partir de valor calculado pelo código. Provedor novo ganha teste de contrato (D18), com recorte do arquivo real e a fonte, a data e o hash anotados.
- **Provedor novo no `MarketEngine`.** Entra por atributo lido com `getattr(self, ..., None)`.
- **Prompt.** Bloco estruturado novo em `dados` entra, no mesmo item, na lista `excluir` de `_formatar_dados` do `ai_core.py`.
- **Rede.** Só de leitura (Tesouro Nacional, BCB, CVM, B3), só no levantamento ou na verificação descrita no item, nunca em teste.
- **Tempo.** Código novo recebe a data de referência como parâmetro; só o ponto de entrada da V1 lê o relógio.

**Rito dos métodos:**
- **Ficha antes** (D21). O item de método confere o status "aprovada" da ficha; sem ele, `[!]`.
- **Versão.** Regime, insumo ou fórmula novos: versão maior. Abstenção nova: versão menor (como o Gordon 1.1.0 e as guardas do F2B-41 e do F2B-42). Só o motivo da abstenção: correção (como o Bazin 1.0.1). Sempre com changelog no `registry.py`.
- **Regime** (armadilha 1, D22). Real e nominal nunca se misturam. A conversão é só a de Fisher do F2B-29. Método REAL não exige `selic`.
- **Sem taxa, abstenção.** NTN-B indisponível ou mais velha que a defasagem da ficha: o método se abstém ("insumo ausente"). Nenhum valor de contingência entra no lugar dela.
- **Antes e depois** (armadilha 5; gate do PLANO). O item que troca uma taxa registra no diário, para o universo inicial: preço justo, upside e a classificação agrupada (sinal positivo, neutro, sinal negativo), com o prêmio-base e os de sensibilidade (4% e 7%).

**Paralelo do Jules (o loop não executa nenhum ticket nem toca nos arquivos deles):**
- B1, B3, C-A, C-B e C-C seguem em paralelo, se ainda abertos. Esta é a última janela do C-C: a 2C trava `peers_engine.py`.
- B2, C-D e C-E: sem janela.
- Grupo A: revisão do PR da fase, no checkpoint.
- D31: a fase não abre ticket novo. Teste com valor de referência numérico (o exemplo das fichas) é do loop.

**Decisões:**
- **[SEÇÃO A]**, **[LIQUIDEZ]**, **[FICHA 1.1]** e **[AUDITORIA]**: respondidas pelo Marcos em 18/10/2026 (última seção).
- **[TAXA]**, **[BAZIN]**, **[FII]**, **[BANCOS]**, **[FINANCEIRAS]** e **[BTG]**: respondidas no marcador "Fichas da 2B, taxa e fontes", depois do levantamento. O prêmio só é fixado depois da coleta da NTN-B com o Tesouro respondendo (checkpoint da Fase 0, seção 4, item 2).
- **[CORREÇÕES]**: a regra aprovada em 5/10/2026 (evidência oficial em cada linha, correção visível na proveniência) vale para o F2B-13 e o F2A-39.
- **[golden]**: o item regenera o golden pela regra acima.
- **[D7]**: COTAHIST como fonte da liquidez (F2A-10).
- **[ADR-0003]** vale para toda a fila: proveniência (D16), números por ação (D19), contas por código e descrição (D20), fichas e parâmetros justificados (D21 a D23), aceite em PASS (D27), referência independente (D28) e auditoria externa (D30).
- As opções e o efeito de cada decisão estão na última seção.

**Privacidade:** o repositório é público. Nenhum dado da carteira do Marcos (posições, pesos, lista de ativos) entra em arquivo versionado: nem em fixture, nem no golden, nem no diário, nem nas fichas, nem nos documentos de levantamento.
- Fixtures usam tickers genéricos (`TST3`, `TST11`) ou os do universo inicial e do índice oficial.
- Medições, matrizes e exemplos das fichas usam o universo inicial; scripts desta fila nunca leem a carteira.
- A limpeza do cache no fim da fase é da tabela inteira, sem lista de tickers.

**Vocabulário:** nunca "recomendação", "compra" ou "venda" em código novo, tabela, coluna, chave de `dados` ou texto de risco ou de abstenção. Os rótulos da V1 (COMPRA/NEUTRO/VENDA) ficam até o F2C-4; nas medições do diário, aparecem agrupados (sinal positivo, neutro, sinal negativo), como no dossiê.
- **Exceção em aberto (F2B-21, F2B-27, F2B-30).** O Tesouro chama os campos do título de "taxa de compra" e "taxa de venda". Duas saídas, decididas na [TAXA]: nomes neutros no código (por exemplo, `taxa_investidor` e `taxa_resgate`), com o nome oficial do campo na proveniência; ou exceção explícita a esta regra só para o nome técnico do título público. Por isso o F2B-27 vem depois do marcador (auditoria externa da 2A, correção 2); o levantamento (F2B-21) cita o nome oficial do campo só no documento dele.

Legenda: `[ ]` pendente · `[x]` feito · `[!]` bloqueado · `[DECISÃO]` o loop para aqui

## Itens

- [ ] **F2B-35** · docs · `docs: sync agent instructions after the phase 2A closure`
  Pendências do fechamento da 2A (diário do fechamento, F2A-40 e F2A-43; auditoria externa da 2A, "Correções do resumo da fase") e da [SEÇÃO A]. Valida contra o código e corrige:
  - **`CLAUDE.md`:**
    - "Testes": o rito da D27 (xfail estrito → correção → marca retirada → PASS; hoje termina em "XPASS") e uma seção "Bugs e regressão" com o texto do `AGENTS.md` (o `AGENTS.md` é subconjunto do `CLAUDE.md` e já a tem);
    - armadilha 2: o trecho do FII cita o F2A-11 de forma ambígua; a pendência é o F2B-16 (BUG-2A-12);
    - armadilha 14 e a linha do `valuation_engine.py` na "Arquitetura real": desde o F2A-43, fora do índice a cascata grava a classe do classificador e a guarda do motor atua;
    - "Fases": a 2A concluída (tag `v2-fase-2a`) e a 2B em andamento;
    - a contagem da suíte em "Comandos" (testes e módulos, contados com `python -m pytest --collect-only -q`).
  - **`AGENTS.md`** (menos a "Fase atual", que é do Marcos): a contagem da suíte.
  - **`docs/PLANO.md`:**
    - o parágrafo "O ADR-0003 acrescenta, antes do F2A-7: …", logo depois da tabela da Fase 2A, repete itens que a tabela já lista; sai;
    - o gate da Fase 2B ("seção A inalterada") passa a dizer "seção A muda só no F2B-7 ([SEÇÃO A] em (c), decisão de 18/10/2026)".

  Se algo divergir, corrige o documento, nunca o código.

  **Aceite:**
  - diff só nesses três arquivos;
  - cada linha alterada conferida com `grep -n` e listada no diário;
  - `CLAUDE.md` e `AGENTS.md` sem contradição entre si;
  - golden inalterado; nenhum código muda.

- [ ] **F2B-36** · test · `test: register the IF.data audit bugs and point open bugs to their items`
  Achados da 2ª passada do Gemini (15/10/2026; auditoria externa da 2A, correção 7), conferidos pelo Claude no código em 18/10/2026 (`sentinela/data/providers/ifdata.py`, `IFDataProvider._buscar`):
  - **BUG-2A-19:** os arquivos do IF.data em `data/ifdata/` não registram a proveniência da D16 (data da coleta, hash, arquivo lateral `.proveniencia.json`), e o `Capital` devolvido não a carrega;
  - **BUG-2A-20:** a validade do cache é medida pelo relógio (`time.time()`), não pelo instante de referência recebido, e a resposta vazia (`value: []`, data-base ainda não publicada pelo BCB) é gravada e reaproveitada por até 7 dias.

  Um teste por bug em `tests/regressao/`, xfail estrito com `corrige: F2B-44`, e as linhas no registro. Bug que não reproduzir não entra como xfail: vai para o diário com a evidência ("não reproduzido"), como manda o `tests/regressao/README.md`.

  No mesmo item, o destino dos bugs abertos da 2A passa de "proposta da 2B" para o item que os corrige, no registro e no `reason` de cada teste: BUG-2A-10 → F2B-37; 11 → F2B-14; 12 → F2B-16; 13 → F2B-17; 14 → F2B-38; 15 → F2B-39; 16 → F2B-40; 17 → F2B-41; 18 → F2B-42.

  **Aceite:**
  - `python -m pytest tests/regressao -q --runxfail` mostra cada teste novo falhando pelo sintoma descrito; sem `--runxfail`, verde;
  - registro com as duas linhas novas e os destinos trocados;
  - nenhum código de produção muda; golden inalterado;
  - gate da fase.

- [ ] **F2B-7** · test · `test: move rate-dependent section A checks to section B` · **[SEÇÃO A]**
  **[SEÇÃO A]** em (c), decidida pelo Marcos em 18/10/2026. Quatro testes da seção A fixam números que dependem da Selic como taxa: `test_a_fair_value_com_tres_metodos_e_a_mediana_nao_a_media` (`:71`), `test_a_fair_value_com_dois_metodos_e_a_media_inclusive_com_divergencia` (`:81`), `test_a_bazin_nao_dispara_abaixo_de_5_por_cento` (`:92`) e `test_a_fii_compara_dy_com_a_selic_liquida_de_ir` (`:100`).
  - **Seção A.** Fica a propriedade que não depende da taxa (mediana e não média; gate de 5% do Bazin), com a taxa injetada pelo próprio teste.
  - **Seção B.** Os números que dependem da Selic vão para testes com `quebra_esperada` e a marca do achado (F-4, F-5 ou F-9; `f5_bazin_selic` registrada no `pytest.ini`), citando o checkpoint (seção 4, itens 2 e 3). O item de taxa de cada achado os vira: F-4 no F2B-1, F-5 no F2B-31 (ou ficam, se a [BAZIN] ficar em (a) ou (d)) e F-9 no F2B-2.
  - Nenhuma asserção é enfraquecida: cada número sai de um teste e entra noutro.

  **Aceite:**
  - `python -m pytest -m preservar` e `python -m pytest -m quebra_esperada` verdes;
  - diário: cada asserção numérica que sai da seção A e o teste da seção B que a recebe;
  - `git diff v2-fase-2a -- tests/test_financeiro_pre_refactor.py` mostra só a mudança de seção;
  - nenhum código de produção muda; golden inalterado;
  - score de mutação de `valuation_engine*` e `fii_engine*` antes → depois no diário, sem queda;
  - gate da fase.

- [ ] **F2B-8** · fix · `fix: keep non-positive CVM figures over stale positive values` · **[AUDITORIA]**
  Corrige o BUG-2A-01. Achado 1 da auditoria do Gemini, confirmado no código em 14/10/2026 e já anotado nos diários do F2A-22 e do F2A-30. `_is_field_missing` (`market_engine.py`) trata como ausente qualquer `pl`, `pvp`, `roe`, `lpa` ou `vpa` ≤ 0:
  - `merge_if_valid` descarta o prejuízo e o PL negativo que a CVM apurou e mantém o valor positivo do yfinance, da brapi ou do cache de 7 dias. O motor de ações deriva o LPA do P/L (`valuation_engine.py:175`), então o Gordon e o Graham calculam com o número velho;
  - `list_missing_required_fields` conta prejuízo como campo faltando: `fundamentos_incompletos` (−30 de confiança e "Dados fundamentais obrigatórios ausentes") e consulta ao cache;
  - `dados['lpa_cvm']` e `valores_por_fonte['CVM']` guardam o valor que o merge jogou fora.

  **Decisão do Marcos (18/10/2026, [AUDITORIA] em (a)):** ausente é só `None` ou não finito nesses campos. O valor ≤ 0 da CVM vence as outras fontes, prejuízo e PL negativo deixam de ser campo faltando (sem os −30 de confiança nem "Dados fundamentais obrigatórios ausentes"), e cada método se abstém pela própria regra.

  **Testes que mudam:** `tests/test_market_engine.py::test_quality_helpers_respect_zero_dy_but_not_zero_price`, se a regra do zero mudar; os demais que fixam ≤ 0 como ausente (lista no diário).

  **Aceite:**
  - `tests/regressao/test_bug_2a_01_cvm_nao_positivo_descartado.py` com a marca retirada, em PASS, e o registro atualizado;
  - `tests/test_market_engine_valores_negativos.py::test_prejuizo_da_cvm_nao_e_trocado_por_valor_positivo` passa por xfail estrito → correção → marca retirada → PASS. Cascata falsa: yfinance com `trailingPE` positivo, CVM com LPA negativo;
  - `::test_cache_nao_repoe_valor_que_a_cvm_entregou`, `::test_lpa_cvm_e_valor_final_concordam` e `::test_prejuizo_nao_conta_como_campo_faltando`;
  - golden inalterado: a mudança é da cascata;
  - diário: nas ações atuais do universo inicial, as que têm prejuízo ou PL negativo na DFP 2025, com `pl`, `lpa`, `roe`, `vpa` e `fundamentos_incompletos` antes → depois;
  - gate da fase.

- [ ] **F2B-10** · fix · `fix: infer share scale from consolidated earnings when controlling earnings abstain` · **[FICHA 1.1]**
  Ponto (a) da ficha 1.1 (decisão 7.7, adotada em 18/10/2026). Com o lucro dos controladores abstido (D20, decisão 7.2), a escala das ações fica indeterminada, e o VPA e a capitalização se abstêm, mesmo com o PL dos controladores lido: 9 companhias, a KLBN11 entre elas (diário do F2A-36); 7 têm razão calculável (ficha, 7.7). Pela decisão 7.7:
  - a escala (unidade ou mil) é inferida pelo lucro consolidado (3.11) ÷ ações contra o LPA divulgado coerente do mesmo documento, na faixa [0,1; 10] (ficha, 7.1), nos dois chamadores (`market_engine._por_acao_cvm` e `series_cvm`);
  - o lucro consolidado serve só à escala; nunca entra no LPA nem no ROE, e o recalculado continua abstido (sem lucro dos controladores);
  - a faixa não garante a escala (ficha, 7.7): o VPA e a capitalização só voltam se a quantidade de ações da CVM na escala escolhida ficar a menos de 10 vezes da `sharesOutstanding` do yfinance para o mesmo ticker (a medida da divergência de ações); sem o yfinance, a abstenção continua, e o yfinance nunca entra no cálculo;
  - a proveniência do VPA registra "escala inferida pelo lucro consolidado e confirmada pela quantidade do yfinance".

  **Aceite:**
  - `tests/test_market_engine_acoes_cvm.py::test_escala_pelo_consolidado_quando_controladores_se_abstem` passa por xfail estrito → correção → marca retirada → PASS;
  - `::test_consolidado_nao_entra_no_lpa_nem_no_roe`, `::test_escala_pelo_consolidado_na_proveniencia`, `::test_escala_pelo_consolidado_exige_a_confirmacao_do_yfinance` (com divergência de 1.000 vezes, abstém) e `::test_sem_yfinance_a_abstencao_continua`;
  - `::test_exemplo_da_ficha_klbn11` com os valores da ficha (seção 5.3: 6.135.427.665 ações, razão 1,1965352, VPA da unit 6,4265659; D28);
  - mutation ≥ 80% em `sentinela.data.acoes_cvm*`;
  - golden inalterado;
  - diário: as 9 companhias, com razão, confirmação, escala e VPA antes → depois, e o motivo das que seguem em abstenção (Cataguases e Aliperti, pela ficha);
  - gate da fase.

- [ ] **F2B-11** · fix · `fix: read the aggregate EPS line as the EPS of a single-class company` · **[FICHA 1.1]**
  Ponto (b) da ficha 1.1 (decisão 7.8, adotada em 18/10/2026). O BBAS3 e o Banco Pine (62.144.175/0001-20) trazem só as linhas agregadas (3.99 e 3.99.01), sem espécie: pela ficha (7.4), a escala fica indeterminada, e LPA, VPA e P/VP se abstêm (diário do F2A-36). Pela decisão 7.8:
  - companhia com uma só espécie no FCA (o BBAS3, só ON) e sem linhas por espécie: a linha de LPA básico agregada (3.99.01) é o LPA divulgado dessa espécie; zerada ou ausente, vale a 3.99, só se o recalculado na escala escolhida ficar a até 10% dela (no BBAS3, 3.99.01 = 0 e 3.99 = 2,40; razão 1,000 no F2A-3; ficha, 7.8), com o mesmo teste de coerência (D19, regra 1; ficha, 7.5 e 7.6), e serve à escala; a proveniência registra "LPA da linha agregada: companhia de espécie única no FCA";
  - mais de uma espécie (o Pine): a abstenção continua.

  **Aceite:**
  - `tests/test_market_engine_acoes_cvm.py::test_linha_agregada_vale_para_companhia_de_especie_unica` passa por xfail estrito → correção → marca retirada → PASS;
  - `::test_linha_agregada_nao_vale_com_mais_de_uma_especie`, `::test_linha_399_vale_so_com_o_recalculado_a_ate_10_por_cento` e `::test_exemplo_da_ficha_bbas3` (LPA 2,40; ficha, seção 5.3);
  - mutation ≥ 80% em `sentinela.data.acoes_cvm*`;
  - golden inalterado;
  - diário: BBAS3 e Pine com LPA, VPA e P/VP antes → depois, e quantas companhias da DFP 2025 trazem só a linha agregada, por número de espécies e por linha usada (3.99.01 ou 3.99);
  - gate da fase.

- [ ] **F2B-12** · fix · `fix: apply one preferred-class rule to units and standalone shares` · **[FICHA 1.1]**
  Ponto (c) da ficha 1.1 (decisão 7.9, adotada em 18/10/2026, opção (i)). A USIM5 (PNA e PNB no FCA, uma linha "PN" na DRE) se abstém pela regra 3; numa unit da mesma companhia, a linha "PN" entraria no componente PN (revisão do F2A-36, registrada no diário do F2A-37). Pela decisão 7.9:
  - a linha básica "PN" única vale como LPA divulgado de cada classe preferencial quando a DRE não as separa, e a USIM5 ganha LPA, com a marca "LPA da linha PN única, aplicado à classe <classe>"; o recalculado comum continua proibido para essas classes (regra 3);
  - a ação avulsa e o componente da unit seguem a mesma ordem: a linha da classe (PNA) e, sem ela, a linha "PN" única;
  - a composição da unit guarda a sigla da classe ("2 PNA"), em vez de reduzi-la a "PN" (revisão do F2A-36, registrada no diário do F2A-36; ressalva da 2ª passada do Gemini a `acoes_cvm.parsear_acoes_por_unit`). O BPAC11 do F2A-39 tem esse caso.

  **Aceite:**
  - `tests/test_market_engine_acoes_cvm.py::test_linha_pn_unica_com_classes_distintas` passa por xfail estrito → correção → marca retirada → PASS, com a ação avulsa e a unit no mesmo teste;
  - `::test_unit_com_componente_pna_usa_a_linha_da_classe` passa por xfail estrito → correção → marca retirada → PASS;
  - mutation ≥ 80% em `sentinela.data.acoes_cvm*`;
  - golden inalterado;
  - diário: a USIM5 e as companhias da DFP 2025 com mais de uma classe preferencial no FCA e uma só linha "PN" na DRE, antes → depois;
  - gate da fase.

- [ ] **F2B-13** · fix · `fix: correct share species through the source corrections table` · **[FICHA 1.1]** **[CORREÇÕES]**
  Ponto (d) da ficha 1.1 (decisão 7.10, adotada em 18/10/2026). O FCA 2026 (versão 1) classifica a MGLU3 como "Ações Preferenciais", e a DRE e a Composição do Capital só trazem ON; o LPA usa o recalculado com marca (diário do F2A-36). Pela decisão 7.10:
  - a tabela de correções do F2A-19 ganha a correção de espécie (colunas do campo corrigido e do valor), com a mesma regra de evidência: arquivo oficial, coluna e data. A correção exige as duas evidências do mesmo documento, a Composição do Capital e a DRE; com uma só, é rejeitada. Caso a caso, nunca automática;
  - a correção aparece na proveniência e no relatório do F1-12, como a do código.

  **Aceite:**
  - `tests/test_referencia_correcoes.py::test_correcao_de_especie_com_evidencia` passa por xfail estrito → correção → marca retirada → PASS;
  - `::test_correcao_de_especie_sem_evidencia_e_rejeitada` e `::test_correcao_de_especie_na_proveniencia`;
  - mutation ≥ 80% em `sentinela.data.referencia*`;
  - golden inalterado;
  - diário: o LPA da MGLU3 antes → depois e a cobertura do índice (`python -m sentinela.data.referencia --cobertura`);
  - gate da fase.

- [ ] **F2B-14** · fix · `fix: cross-check recalculated EPS only against coherent reported EPS` · **[FICHA 1.1]** **[AUDITORIA]**
  Corrige o BUG-2A-11. Achado 6; revisão do F2A-36 (registrada no diário do F2A-37). `_lpa_divulgado_comparado` (`market_engine.py`) busca o divulgado em `lpa_divulgado_por_especie` e `lpa_divulgado`, antes do filtro de coerência (`acoes_cvm.divulgados_coerentes`). Com o divulgado descartado pela D19 (linhas conflitantes ou sinal oposto), o alerta de 10% do F2A-5 compara o recalculado com um valor que a ficha mandou ignorar. Pela ficha (7.3 e 7.5): a conferência usa só o divulgado coerente da espécie; com o divulgado incoerente, o alerta é só o da incoerência.

  **Aceite:**
  - `tests/regressao/test_bug_2a_11_alerta_lpa_antes_da_coerencia.py` com a marca retirada, em PASS, e o registro atualizado;
  - `tests/test_data_quality_fontes.py::test_divulgado_incoerente_nao_entra_na_conferencia` passa por xfail estrito → correção → marca retirada → PASS;
  - `::test_divulgado_coerente_segue_conferido`;
  - golden inalterado;
  - diário: os tickers do universo inicial cujo alerta muda (QUAL3 e os de sinal oposto);
  - gate da fase.

- [ ] **F2B-16** · fix · `fix: record FII figures per source for the cross-checks` · **[AUDITORIA]**
  Corrige o BUG-2A-12. Achado 7; pendência do F2A-11; armadilha 2, no trecho que ainda vale para FII. `_buscar_cvm_fii` não grava `valores_por_fonte['CVM']`: o check 3 da validação cruzada compara o P/VP da CVM com preço ÷ VPA da própria CVM e nunca alerta. Pela regra do F2A-5, identidade é pulada.
  - A etapa grava em `valores_por_fonte['CVM']` o que o Informe entregou.
  - Alerta P/VP da CVM × P/VP da fonte de mercado (yfinance ou brapi) acima de 10%, o limiar dos checks 2 e 3 da V1 (decisão do Marcos de 18/10/2026, [AUDITORIA]).

  **Aceite:**
  - `tests/regressao/test_bug_2a_12_fii_sem_valores_por_fonte.py` com a marca retirada, em PASS, e o registro atualizado;
  - `tests/test_market_engine_fii_cvm.py::test_informe_grava_valores_por_fonte` passa por xfail estrito → correção → marca retirada → PASS;
  - `tests/test_data_quality_fontes.py::test_identidade_do_fii_e_reconhecida` e `::test_pvp_do_fii_divergente_da_fonte_de_mercado_gera_alerta` (acima de 10% alerta; até 10%, não);
  - golden inalterado;
  - gate da fase.

- [ ] **F2B-17** · fix · `fix: stop flagging FIIs as outside CVM company coverage` · **[AUDITORIA]**
  Corrige o BUG-2A-13. Achado 8; pendências do F2A-11 e da revisão do F2A-31 (registrada no diário do F2A-27). `_buscar_cvm` roda para todo ticker e, no FII (sem `cd_cvm`), grava "ticker fora da cobertura da CVM", mesmo quando o Informe Mensal preenche os dados em seguida. E o FII sem índice só recebe "referência oficial indisponível" por efeito colateral dessa chamada.
  - Para FII, `_buscar_cvm` não grava o aviso de cobertura das companhias.
  - "referência oficial indisponível: dados da CVM não consultados" passa a ser gravado sem depender do `_buscar_cvm`, para qualquer classe.
  - FII sem CNPJ no índice: "FII fora da cobertura do Informe Mensal".

  **Testes que mudam:** os que afirmam o aviso de cobertura das companhias para FII (lista no diário).

  **Aceite:**
  - `tests/regressao/test_bug_2a_13_fii_risco_fora_da_cvm.py` com a marca retirada, em PASS, e o registro atualizado;
  - `tests/test_market_engine_fii_cvm.py::test_fii_nao_recebe_o_aviso_de_cobertura_das_companhias` passa por xfail estrito → correção → marca retirada → PASS;
  - `::test_fii_sem_indice_tem_o_aviso_de_referencia` e `::test_fii_sem_cnpj_tem_o_aviso_do_informe`;
  - golden inalterado;
  - gate da fase.

- [ ] **F2B-18** · fix · `fix: discard implausible negative ROE at the provider boundary` · **[AUDITORIA]**
  Decisão C da auditoria do Gemini; pendência do F2A-30. `guardar_roe` (`sentinela/data/normalizacao.py`) corta ROE acima de 2, mas não tem piso: um −21,0 do yfinance (declarado em razão) entra como −2.100%. Sem efeito no score (todo ROE abaixo de `ROE_PENALIDADE_MAX` leva a mesma penalidade); o número sai errado no relatório, no cache e nos mínimos de ROE do Gordon e da lente de bancos.

  **Decisão do Marcos (18/10/2026, [AUDITORIA]):** piso de −2, simétrico ao teto de 2. ROE abaixo do piso vira ausente, com o motivo, como o acima do teto. Vale só na fronteira das fontes de mercado (yfinance e brapi); o ROE dos controladores da CVM não passa por ela.

  **Aceite:**
  - `tests/test_roe_fronteira.py::test_roe_abaixo_do_piso_vira_ausente_com_motivo` passa por xfail estrito → correção → marca retirada → PASS;
  - `::test_roe_negativo_acima_do_piso_passa`;
  - mutation ≥ 80% em `sentinela.data.normalizacao*` (hoje 100%);
  - golden inalterado;
  - gate da fase.

- [ ] **F2B-20** · fix · `fix: refuse non-positive prices in both engines` · **[AUDITORIA]** **[golden]**
  Ressalva da auditoria do Gemini ao F2A-25; revisão do F2A-25 (registrada no diário do F2A-12). O motor de ações recusa só o preço zero e o não finito (`valuation_engine.py:113` e `:118`); o de FII, só `p == 0` e o não finito. Preço negativo passa: no golden, `acoes/preco-negativo` sai com Graham de R$ 12,25 e Bazin de R$ −5,52. Preço ≤ 0 passa a devolver `None`, como o zero (F2A-24).

  **Golden.** Só mudam `acoes/preco-negativo` e `fii/preco-negativo`, para `None`: `--onde "(entrada.get('preco_atual') or 0) < 0"`.

  **Aceite:**
  - `tests/test_saidas_finitas.py::test_preco_negativo_nao_e_analisado`, nos dois motores, passa por xfail estrito → correção → marca retirada → PASS;
  - seções A, B e C intactas;
  - golden pela regra;
  - gate da fase.

- [ ] **F2B-37** · fix · `fix: apply the controlling-interest rule to the trailing twelve months`
  Corrige o BUG-2A-10 (achado 5 do Gemini; destino "antes do F2C-1" no registro). `cvm_provider._acumulados_do_arquivo` lê o lucro dos controladores do TTM direto da conta, sem a decisão 7.2 da ficha nem a D20: com a 3.11.01 zerada (105 companhias na DFP 2025), o TTM soma 0 como lucro dos controladores.
  - Cada documento do TTM passa pela mesma leitura com reservas da série anual (`lucro_controladores_com_reserva`, com o balanço do mesmo documento). Abstenção num documento abstém o TTM do campo, com o motivo.
  - O consumidor de hoje é só informativo (o TTM no relatório); o F2C-1 vai consumi-lo.

  **Aceite:**
  - `tests/regressao/test_bug_2a_10_ttm_sem_regra_7_2.py` com a marca retirada, em PASS, e o registro atualizado;
  - `tests/test_cvm_series.py::test_ttm_abstem_quando_um_documento_se_abstem`;
  - golden inalterado;
  - diário: nas ações atuais do universo inicial, o lucro dos controladores do TTM antes → depois;
  - gate da fase.

- [ ] **F2B-38** · fix · `fix: pick the latest version of a restated FII monthly report`
  Corrige o BUG-2A-14. `cvm_fii_provider.obter_dados_fii` escolhe entre linhas do mesmo fundo e da mesma data de referência sem desempate pela maior `Versao`: o Informe reapresentado pode perder para o original. Passa a valer a maior `Versao` (a regra que o F2B-28 usa nos 12 meses).

  **Aceite:**
  - `tests/regressao/test_bug_2a_14_informe_sem_desempate_por_versao.py` com a marca retirada, em PASS, e o registro atualizado;
  - golden inalterado;
  - gate da fase.

- [ ] **F2B-39** · fix · `fix: keep a valid dividend yield over an out-of-range later source`
  Corrige o BUG-2A-15. No merge da cascata, um DY finito mas fora de 0–25% vindo de fonte posterior (brapi) sobrescreve o DY válido de fonte anterior. Passa a valer o invariante dos motores (`config._normalizar_dy`, armadilha 4) também no merge: DY fora da faixa não entra, com o motivo na proveniência, e o válido anterior fica. Nenhuma conversão nova de percentual: a da fronteira continua a única.

  **Aceite:**
  - `tests/regressao/test_bug_2a_15_dy_invalido_sobrescreve_valido.py` com a marca retirada, em PASS, e o registro atualizado;
  - `tests/test_dy_fronteira.py::test_dy_fora_da_faixa_nao_entra_no_merge`;
  - golden inalterado;
  - gate da fase.

- [ ] **F2B-40** · fix · `fix: treat an empty COTAHIST archive as a failed download`
  Corrige o BUG-2A-16. `b3_cotahist.ler_zip` faz `namelist()[0]` sem tratar ZIP vazio, e o `IndexError` escapa das exceções que `HistoricoRecente.coletar` trata. ZIP vazio passa a seguir o caminho do arquivo corrompido: o mês fica ausente, com o motivo, e o arquivo não conta como completo no cache.

  **Aceite:**
  - `tests/regressao/test_bug_2a_16_cotahist_zip_vazio.py` com a marca retirada, em PASS, e o registro atualizado;
  - `tests/test_cotahist.py::test_zip_vazio_nao_conta_como_completo`;
  - mutation ≥ 80% em `sentinela.data.providers.b3_cotahist*`;
  - golden inalterado;
  - gate da fase.

- [ ] **F2B-41** · fix · `fix: abstain the FII book-value lens on non-positive P/VP`
  Corrige o BUG-2A-17. `sentinela/methods/fii_nav.py` classifica P/VP ≤ 0 como "desconto" quando chamado direto; o motor de FII já transforma esse P/VP em `None` antes da lente (F2A-11), então só chamadas fora do motor veem o erro. A lente passa a se abster ("P/VP ≤ 0"). Guarda de validade de insumo: versão menor, com changelog, sem ficha (decisão do Marcos de 18/10/2026, [AUDITORIA]).

  **Testes que mudam:** `tests/test_methods_fii_nav.py::test_faixa_pelos_limites_estritos_da_v1`, nos casos de P/VP 0,0 e −1,0, que fixavam o desconto (diário do fechamento da 2A); `tests/test_registry.py` (versão).

  **Aceite:**
  - `tests/regressao/test_bug_2a_17_fii_nav_pvp_nao_positivo.py` com a marca retirada, em PASS, e o registro atualizado;
  - mutation de `sentinela.methods*` ≥ 80%;
  - golden inalterado (o motor não passa P/VP ≤ 0 à lente);
  - gate da fase.

- [ ] **F2B-42** · fix · `fix: abstain Graham on non-positive book value per share`
  Corrige o BUG-2A-18. `sentinela/methods/graham.py` com VPA < 0 calcula a raiz de um número negativo (sai um complexo, e o `math.isfinite` quebra). O método passa a se abster com VPA ≤ 0 ("VPA ≤ 0"). Guarda de validade de insumo: versão menor, com changelog, sem ficha (mesma decisão do F2B-41).

  **Testes que mudam:** `tests/test_registry.py` (versão).

  **Aceite:**
  - `tests/regressao/test_bug_2a_18_graham_vpa_negativo.py` com a marca retirada, em PASS, e o registro atualizado;
  - mutation de `sentinela.methods*` ≥ 80%;
  - golden inalterado (no motor, o VPA vem de preço ÷ P/VP com P/VP > 0);
  - gate da fase.

- [ ] **F2B-21** · levantamento · `docs: survey rates, FII yields and bank sources for phase 2B`
  Confere nos arquivos reais os fatos de que as fichas e os itens seguintes dependem. Grava `docs/decisoes/fontes-fase2b.md` e `scripts/levantamento_fase2b.py` (`--secao N` roda só algumas).
  - **Rede e cache.** Só de leitura, com cache em `outputs/levantamento_cache/`. O script não importa `config`, não usa token da brapi e não lê `.env`.
  - **Amostra.** O universo inicial (`docs/decisoes/universo-inicial.md`) e o índice oficial; nunca a carteira.
  - **Formato.** Cada pergunta traz a evidência (arquivo ou URL, coluna, amostra, data) e a consequência para o item afetado.

  As perguntas:
  1. **NTN-B (F2B-1; checkpoint da Fase 0, seção 4, item 2).** A coleta é repetida com o Tesouro respondendo:
     - a API do Tesouro Direto que `config._fetch_ntnb` lê (`config.py:271-301`): status HTTP e data; no dossiê, 403;
     - o arquivo histórico de preços e taxas do Tesouro Direto no Tesouro Transparente: URL, status, colunas, primeira e última data;
     - por fonte que responder: NTN-B e NTN-B Principal, com vencimento, taxas de compra e de venda e data-base; o valor que `MACRO.ntnb_longa` daria hoje (média dos IPCA+ de 2035 em diante) contra a contingência de 7% (`config.py:122`); os vértices candidatos (o mais perto de 10 anos, 2035, 2045, o mais longo e a média de 2035 em diante), com o valor de cada um;
     - sem resposta de nenhuma fonte do Tesouro: "não determinado", e o prêmio não é fixado.
  2. **Inflação da conversão (F2B-1; D22).** IPCA de 12 meses (BCB SGS 433), a expectativa do Focus (12 meses à frente e o ano mais longo publicado) e a inflação implícita no vértice da pergunta 1, se a fonte trouxer o prefixado: valor, data, disponibilidade e começo da série.
  3. **Matriz de sensibilidade (armadilha 5; F-11, item 3; dossiê, seções 2 e 3).** Nas ações atuais do universo inicial, com os dados da 2A e os do F2B-8: mediana do upside por método e a contagem por classificação agrupada para:
     - a V1, com a Selic de 10% a 15% (a grade do dossiê);
     - o Gordon no regime real (k = NTN-B + prêmio) com as três definições de g real da [TAXA] ((i), (ii) e (iii), com o teto candidato da (iii)), e no nominal (k por Fisher), com prêmio de 4%, 5% e 7% e cada inflação da pergunta 2; o regime misto (armadilha 1) como controle, com a razão misto ÷ nominal;
     - o Bazin com a Selic (V1), com a taxa fixa de 6% (F-5) e com o k real sem crescimento real;
     - os FIIs atuais com a Selic líquida (V1) e com NTN-B + spread (1, 2 e 3 pontos e as medianas da pergunta 4).
  4. **DY e spread dos FIIs (F2B-2; checkpoint, seção 4, item 3).**
     - `Percentual_Dividend_Yield_Mes`: representação (o F2A-16 a registrou em percentual; o contrato do F2A-32 lê fração) e base (valor patrimonial ou cotação), pela documentação da CVM e por conta refeita em FIIs públicos;
     - se o Informe traz o rendimento distribuído (por cota ou total) para o DY de 12 meses sobre o preço; primeiro ano publicado;
     - a série mensal do spread (DY de 12 meses − NTN-B) em definições candidatas: mediana dos FIIs listados; tijolo e papel separados (composição do `ativo_passivo`, como no F2A-35); por fundo; janelas de 5 e 10 anos, ou o que a série permitir; mediana, p25, p75 e o valor atual;
     - a Selic líquida nos mesmos meses, como contexto.

     Preços pelo COTAHIST anual, só no levantamento.
  5. **Bancos e financeiras (F2B-3, F2B-4).**
     - inadimplência: a hipótese do F2A-16 (IF.data, relatório 16, Resolução CMN 4.966), com chamada de controle (BB). Sem medida de inadimplência: "não determinado", e a limitação continua;
     - os setores financeiros do índice (Bancos, Intermediação Financeira, Crédito Imobiliário, Seguradoras e Corretoras, e as variantes "Emp. Adm. Part. - …"): tickers, modelo da demonstração (2.03, ou 2.07 e 2.08) e tipo de negócio, insumo da [FINANCEIRAS];
     - o P/VP justificado dos bancos do universo inicial, com ROE e VPA do F2A-9 e do F2A-36: k com prêmio de 4%, 5% e 7% sobre a NTN-B da pergunta 1; g candidatos (ROE × retenção, com o payout pela DVA do F2A-7; inflação + 0, 1 e 2 pontos); nos regimes real e nominal, conferindo que dão o mesmo valor; contra o P/VP de mercado. Banco sem VPA (BBAS3) marcado.
  6. **BTG (F2A-39).** Uma fonte oficial da B3 que traga ISIN e CNPJ juntos: o serviço de empresas listadas (detalhe da companhia pelo código CVM, com códigos de negociação e ISIN) e o cadastro de instrumentos. Por fonte: URL, status, o registro do BTG (30.306.294/0001-45) e o do ISIN `BRBPACUNT006`, e a data. Nada é aceito pelo texto.
  7. **Pontos "não conferidos" da 1ª passada do Gemini** (`docs/loop/historico/fase-2a/auditoria-gemini-completa.md`): regex das descrições do LPA; coluna `MOEDA`; DVA sem `try` no TTM; cache duplicado entre série e TTM; nova tentativa em HTTP 404 do COTAHIST. (O Informe reapresentado e o DY da brapi viraram o BUG-2A-14 e o BUG-2A-15, corrigidos no F2B-38 e no F2B-39.)
  8. **Ressalvas da auditoria externa da 2A sem destino** (`docs/loop/historico/fase-2a/auditoria-externa.md`, correção 6 e relatório da 2ª passada do Gemini). No código e, quando a evidência depender deles, nos arquivos da CVM e do índice:
     - tesouraria: `QT_ACAO_TOTAL_TESOURO` igual a zero com as espécies (`QT_ACAO_ORDIN_TESOURO`, `QT_ACAO_PREF_TESOURO`) diferentes de zero (`cvm_provider.composicao_do_documento`); quantas companhias na DFP 2025;
     - versão e grupo nas linhas 3.99 de `_dados_por_acao`: quantas companhias têm mais de uma `VERSAO` no arquivo, e qual linha o chamador usa; e se algum `GRUPO_DFP` do arquivo `DRE_con` não é consolidado (a leitura não confere a coluna; auditoria externa da 2A, correção 6);
     - o código contra as regras de domínio da ficha por ação 1.1 (seção 4, itens 10 a 12: insumo inválido, zero, prejuízo e PL negativo como dados);
     - divergência de ações com mais de uma classe preferencial (PN total contra a classe do yfinance: USIM5, BRSR5, BRSR6);
     - completude que penaliza bancos e FIIs por campos que o modelo deles não tem (`receita_liquida`, `margem_liquida`, `divida_liq_ebitda`);
     - BTCI11 e TRPL11 no índice como `UNKNOWN` (`cotahist:cota_de_fundo`) à frente das listas conhecidas, e por que faltam no Informe Mensal;
     - `divulgados_coerentes` sem guarda de NaN e zero; pares 3.09.01 e 3.09.02 no modelo empresa; submodelos de banco (2.07/2.08) e de seguradora (3.05/3.07) dando "sem correspondência" no lugar de "linha ausente"; a preposição "a/aos" nas descrições; `series_cvm._meses` ignorando o dia; proventos ausentes quando só dividendos ou só JCP existem; `divida_liquida.medir` com subconta de 3º nível ausente; corrida no arquivo temporário da proveniência e CNPJ com espaços em `entrega_no_indice`; `classe_preferencial` sem caixa alta e validação de ticker na tabela de correções.

     Cada ponto das perguntas 7 e 8: confirmado (com a evidência e a consequência) ou refutado. Os confirmados viram teste de regressão no F2B-43; o destino de cada um é do Marcos, no marcador (item novo nesta fila ou proposta da 2C).

  **Aceite:**
  - cada uma das oito perguntas respondida ou marcada "não determinado", com a consequência escrita para o item afetado, sem decidir nada;
  - script reproduzível;
  - nenhum módulo de produção alterado;
  - gate da fase.

- [ ] **F2B-43** · test · `test: register bugs confirmed by the phase 2B survey`
  Regra do projeto (`tests/regressao/README.md`): todo bug confirmado vira teste antes da correção. Para cada ponto confirmado nas perguntas 7 e 8 do F2B-21, um teste em `tests/regressao/` (`test_bug_2b_NN_<sintoma>.py`), xfail estrito com `reason="BUG-2B-NN · <sintoma> · corrige: a decidir no marcador"`, e a linha no registro. Os refutados ficam só no documento do levantamento.

  **Aceite:**
  - `python -m pytest tests/regressao -q --runxfail` mostra cada teste novo falhando pelo sintoma; sem `--runxfail`, verde;
  - registro com uma linha por bug novo, com a evidência do F2B-21;
  - nenhum código de produção muda; golden inalterado;
  - gate da fase.

- [ ] **F2B-22** · docs · `docs: add methodology sheet for the real cost of equity` · **[ADR-0003]** **[TAXA]**
  ADR-0003, D21 a D23. Escreve `docs/metodologia/taxa-real.md` no modelo de `docs/metodologia/README.md`, com status **rascunho**. O loop nunca marca ficha como aprovada.
  - **Fórmula.** k real = NTN-B do vértice + prêmio; conversão real ↔ nominal por Fisher exato, (1 + nominal) = (1 + real) × (1 + inflação). Referência de finanças com a seção citada.
  - **Insumos.** NTN-B (fonte, tipo de taxa, data-base) e inflação, pelas perguntas 1 e 2 do F2B-21.
  - **Regime.** Real (checkpoint, item 2); D22; a observação do dossiê (seção 3): com Fisher exato, tudo real e tudo nominal dão o mesmo valor.
  - **Abstenção.** NTN-B indisponível ou mais velha que a defasagem máxima; a contingência de 7% (`config.py:122`) não entra.
  - **Exemplo independente.** Conversão de ida e volta com os valores do levantamento, citados.
  - **Sensibilidade.** Prêmio (4%, 5% e 7%) × vértice × inflação; o resumo da matriz (pergunta 3).
  - **Parâmetros, cada um marcado [DECISÃO],** com as opções e o efeito: prêmio (base de 5% e sensibilidade de 4% e 7%, checkpoint, item 2), vértice, tipo de taxa, inflação da conversão e defasagem máxima.

  **Aceite:** as sete seções do modelo preenchidas; todo número com fonte; status "rascunho"; nenhum parâmetro decidido pelo texto; diff só na ficha, no diário e na fila.

- [ ] **F2B-23** · docs · `docs: add methodology sheet for Gordon in the real regime` · **[ADR-0003]** **[TAXA]**
  `docs/metodologia/gordon.md`, rascunho.
  - **Fórmula.** Valor = D1 ÷ (k − g), no regime real, com D1 = D0 × (1 + g real). Referência citada.
  - **g real: [DECISÃO]** (auditoria externa da 2A, correção 1; a definição não pode ser tomada pelo texto). A ficha apresenta as opções da [TAXA], com o efeito de cada uma no exemplo e na matriz do F2B-21: (i) g real = (1 + ROE × retenção) ÷ (1 + inflação) − 1; (ii) g real = ROE real × retenção, com ROE real = (1 + ROE) ÷ (1 + inflação) − 1; (iii) g real limitado por um teto de crescimento real de longo prazo, com a fonte do teto. A mesma escolha vale para a lente de bancos (F2B-26).
  - **Insumos.** DY e preço da cascata (a janela de 12 meses do checkpoint, item 4, é do F2C-1 e fica declarada), LPA dos métodos (D19), ROE dos controladores, k e inflação da ficha da taxa real.
  - **Regime.** Real; armadilha 1; a razão misto ÷ nominal do dossiê (seção 3) e do F2B-21.
  - **Abstenções.** As da 1.1.0, mais a taxa real indisponível.
  - **Exemplo independente.** Uma ação real do universo inicial, com DFP, preço (COTAHIST) e taxa citados, conta à mão; vira teste no F2B-1.
  - **Sensibilidade.** Prêmio, inflação e teto de g.
  - **Parâmetros [DECISÃO].** Definição do g real (acima), teto de g no regime real (hoje 8% nominal, `GORDON_G_MAX`), DY e ROE mínimos (mudar um deles muda ids do golden, e o item declara o `--par`), payout máximo.

  **Aceite:** como o F2B-22.

- [ ] **F2B-24** · docs · `docs: add methodology sheet for the Bazin rate` · **[ADR-0003]** **[BAZIN]**
  `docs/metodologia/bazin.md`, rascunho. F-5: o Bazin da V1 é DY × preço ÷ máx(Selic, 5%) (`sentinela/methods/bazin.py:65`), o preço cancela e a nota segue o Copom. A ficha apresenta as opções da [BAZIN], cada uma com fórmula, regime, referência, efeito pela matriz do F2B-21 e os testes que o F2B-7 marcou com o F-5:
  - (a) manter a Selic; (b) taxa fixa (6% no Bazin original); (c) k real sem crescimento real (o Gordon com g real = 0); (d) adiar para o F2C-5 (lentes);
  - o gate de DY de 5% e o alerta de armadilha ficam em todas;
  - exemplo independente para (b) e (c).

  **Aceite:** como o F2B-22, com as quatro opções e o efeito de cada uma.

- [ ] **F2B-25** · docs · `docs: add methodology sheet for FII yield against NTN-B` · **[ADR-0003]** **[FII]**
  `docs/metodologia/fii.md`, rascunho. Checkpoint, seção 4, item 3: NTN-B + spread, com o spread pela mediana histórica; Selic líquida e P/VP como contexto. F-9.
  - **Fórmula.** Preço justo = preço × DY ÷ (NTN-B + spread); o preço cancela (armadilha 5), e a ficha o declara.
  - **Insumos.** DY (Informe, pelo F2B-28, ou o da cascata), janela de 12 meses e base (pergunta 4); NTN-B (vértice); spread.
  - **Regime.** A justificativa de comparar o DY com a taxa real (D22) e o limite dos fundos de papel indexados ao CDI (F-9).
  - **Abstenções.** DY ausente ou não confiável (V1); NTN-B ou spread indisponíveis.
  - **Exemplo independente.** Um FII público (Informe, preço e NTN-B com data), conta à mão; vira teste no F2B-2.
  - **Sensibilidade.** Definição do spread × janela × vértice.
  - **Parâmetros [DECISÃO].** Os da [FII] (última seção).

  **Aceite:** como o F2B-22.

- [ ] **F2B-26** · docs · `docs: add methodology sheet for the bank lens` · **[ADR-0003]** **[BANCOS]**
  `docs/metodologia/bancos.md`, rascunho. Checkpoint, seção 4, item 5; D22 ("a lente de bancos tem derivação explícita na ficha").
  - **Fórmula.** P/VP justificado = (ROE − g) ÷ (k − g); valor = P/VP justificado × VPA. Derivação nos regimes real e nominal, com a prova de que dão o mesmo valor por Fisher. A equivalência exige converter as quatro taxas, inclusive o ROE contábil, que é nominal (ROE real = (1 + ROE nominal) ÷ (1 + π) − 1); convertendo só k e g, os regimes divergem. A conversão do ROE e a definição de g seguem a decisão do g real da [TAXA], a mesma do Gordon (F2B-23). A ficha diz qual conversão o método usa, e o `::test_real_e_nominal_dao_o_mesmo_pvp` do F2B-3 compara as duas contas independentes, não a fórmula consigo mesma. Referência citada.
  - **Insumos.** ROE e PL dos controladores (F2A-9), VPA (F2A-36), g, k e inflação.
  - **Datas.** A Basileia é da última data-base do IF.data, e o balanço, da DFP (diário do F2A-9): declarado. O `divida_pl` não entra (diário do F2A-9).
  - **Qualidade.** Basileia e inadimplência fora do valor (checkpoint, item 5).
  - **Abstenções.** ROE ≤ g, k ≤ g, VPA ausente ou ≤ 0. Banco fora do índice é lido como empresa (diário do F2A-9): limitação.
  - **Exemplo independente.** O ITUB4, com os valores da DFP 2025 citados ao arquivo; vira teste no F2B-3.
  - **Sensibilidade.** Prêmio × g.
  - **Parâmetros [DECISÃO].** Os da [BANCOS] (última seção).

  **Aceite:** como o F2B-22.

- [ ] **F2B-28** · feat · `feat: add FII trailing distributions from the monthly report` · **[ADR-0003]**
  Pendência "DY do Informe Mensal de FII (F2B-2)" (PLANO, seção 10). É aditivo: quem passa a usar é o F2B-2, se a ficha do FII escolher.
  - **Leitura.** O `CVMFIIProvider` lê os 12 últimos meses do fundo (o Informe do ano e o do anterior), com a maior `Versao` de cada mês.
  - **Conta.** Função pura em `sentinela/data/`: DY de 12 meses sobre o preço, pela base e pela representação que o F2B-21 determinou (pergunta 4). A conversão de percentual passa por `sentinela/data/normalizacao.py`, com a representação do Informe declarada e citada (armadilha 4). Menos de 12 meses: abstenção, com o motivo. Base não determinada no F2B-21: `[!]`.
  - **Cascata.** `dados['rendimento_fii_cvm']` (DY, meses, base e proveniência), fora do prompt. Nenhum motor lê.
  - **Relatório do F1-12.** Uma linha com o DY do Informe ao lado do DY da cascata.

  **Aceite:**
  - `tests/test_fii_rendimentos.py::test_doze_meses_somam_os_rendimentos`, `::test_mes_com_duas_versoes_usa_a_maior`, `::test_menos_de_doze_meses_abstem` e `::test_conversao_pela_fronteira`;
  - mutation ≥ 80% no módulo puro;
  - golden inalterado; nenhum teste existente muda;
  - diário: DY do Informe × DY da cascata nos FIIs atuais do universo inicial;
  - gate da fase.

- [DECISÃO] **Fichas da 2B, taxa e fontes.** O Marcos:
  1. lê `docs/decisoes/fontes-fase2b.md`. Sem NTN-B de fonte do Tesouro, o prêmio não é fixado (checkpoint da Fase 0, seção 4, item 2): repete a coleta (`python scripts/levantamento_fase2b.py --secao 1`) até o Tesouro responder e registra o resultado no documento;
  2. decide os pontos **[DECISÃO]** das fichas: [TAXA] (com o g real do Gordon e dos bancos e o nome dos campos do Tesouro), [BAZIN], [FII] e [BANCOS];
  3. decide a [FINANCEIRAS] e a [BTG], e o destino de cada bug que o F2B-43 registrou (item novo nesta fila, com a decisão escrita, ou proposta da 2C);
  4. roda a auditoria externa em modo FICHA (D30) em cada ficha (`python scripts/auditar.py codex ficha --fase 2b --arquivo docs/metodologia/<ficha>.md`; o Gemini desempata ponto de método em que o Codex e a ficha divergirem) e guarda os relatórios em `docs/loop/historico/fase-2b/auditoria-fichas.md`;
  5. marca cada ficha como aprovada (versão 1.0, data e nome), ou pede correções;
  6. se a [FII] tirar os pontos de P/VP do score, confirma que a asserção do score em `test_b_fii_nao_considera_o_patrimonio_no_fair_value` muda no F2B-2;
  7. retira os itens que as decisões dispensaram: o F2B-31, se a [BAZIN] ficar em (a) ou (d); o F2A-39, se a [BTG] recusar a fonte;
  8. troca este marcador por `[x]` e retoma o loop. Item de método com a ficha não aprovada fica `[!]`.

- [ ] **F2B-27** · feat · `feat: add Tesouro Nacional bond rates provider` · **[ADR-0003]**
  Cria `sentinela/data/providers/tesouro.py`. É aditivo: o consumidor é o F2B-30. Vem depois do marcador porque o nome dos campos de taxa do título é decidido na [TAXA] (vocabulário; auditoria externa da 2A, correção 2).
  - **Fonte.** As do Tesouro Nacional que o F2B-21 confirmou (o dia e a série histórica). Sem fonte confirmada, `[!]`.
  - **Parser puro.** Por título: nome, tipo (NTN-B, NTN-B Principal, prefixado), vencimento, data-base, as duas taxas do título em decimal, com os nomes da [TAXA], com o tipo do `units.py` pelo título (`RateReal` na NTN-B, `RateNominal` no prefixado). Não escolhe vértice.
  - **Download.** Cache em `data/tesouro/`, TTL de um dia para o arquivo do dia; rede fora, vale o cache, com aviso e data. Proveniência (D16) pelo `proveniencia.registrar_sem_falhar`. O instante entra como parâmetro.

  **Aceite:**
  - `tests/test_tesouro.py::test_titulo_segue_o_layout_oficial`, `::test_tipo_da_taxa_pelo_titulo`, `::test_vencimento_e_data_base` e `::test_rede_fora_usa_o_cache_com_aviso`, com arquivos sintéticos em `tmp_path`;
  - `tests/test_contratos_provedores.py::test_contrato_tesouro`, com recorte do arquivo real (D18);
  - mutation ≥ 80% em `sentinela.data.providers.tesouro*`;
  - golden inalterado; nenhum teste existente muda;
  - gate da fase.

- [ ] **F2B-29** · feat · `feat: add real-rate inputs and Fisher conversion to the method contract`
  Aditivo, sem consumidor: nenhum método muda.
  - **`sentinela/domain/units.py`.** O tipo da inflação (variação anual de preços, em decimal) e as conversões real ↔ nominal por Fisher exato, como a ficha da taxa real (seção 1). O docstring que dizia que a conversão não existia de propósito passa a citar a ficha.
  - **`sentinela/methods/base.py`.** `MethodInputs` ganha o custo de capital real (`RateReal`) e a inflação, opcionais. Checagem do contrato: custo de capital real só em método REAL, como a `selic` só em método NOMINAL.

  **Aceite:**
  - `tests/test_units.py::test_fisher_ida_e_volta` (valores do exemplo da ficha) e `::test_inflacao_nao_soma_com_taxa`;
  - `tests/test_methods_contrato.py::test_custo_de_capital_real_so_em_metodo_real`;
  - mutation ≥ 80% em `sentinela.domain.units*` e em `sentinela.methods*`;
  - golden inalterado; nenhum teste existente muda (o diff dos arquivos de teste só tem inclusões);
  - gate da fase.

- [ ] **F2B-30** · feat · `feat: expose the real cost of equity with provenance` · **[TAXA]** **[ADR-0003]**
  A taxa real chega a quem a usa, com proveniência (D16). Nenhum motor a lê ainda: o consumidor é o F2B-1.
  - **`sentinela/data/taxas.py` (puro).** Escolhe a NTN-B do vértice da ficha nos títulos do F2B-27, confere a defasagem máxima e calcula o custo de capital real (NTN-B + prêmio). Devolve o registro (taxa, vértice, data-base, fonte e proveniência) ou abstenção com motivo.
  - **Inflação.** Pela fonte da [TAXA]. Fora do arquivo do F2B-27, um provedor em `sentinela/data/providers/`, com cache, TTL, proveniência e contrato (D18).
  - **Ponto de entrada da V1 em `config.py`,** no padrão do `get_selic_atual`: cache por processo e TTL, sem rede no import e sem valor de contingência (rede fora e cache além da defasagem → `None`). Constantes novas no `MacroContext`: prêmio e regra do vértice.
  - **`tests/conftest.py`.** Semente da taxa real no carregamento, no mesmo contorno da Selic (E-6). Os valores são os das contingências antigas (`NTNB_LONGA_FALLBACK` e `IPCA_12M_FALLBACK`), escritos no arquivo só como semente de teste; a fixture de sessão confere que valem.
  - **Cascata.** `dados['taxa_real']` com o registro, fora do prompt.
  - **Relatório do F1-12.** Ganha a seção "Taxa real" (NTN-B, vértice, data-base, fonte, prêmio e inflação); a "Selic usada" fica enquanto algum método a usar.

  **Aceite:**
  - `tests/test_taxas.py::test_vertice_pela_regra_da_ficha`, `::test_ntnb_alem_da_defasagem_abstem`, `::test_custo_de_capital_e_ntnb_mais_premio` e `::test_sem_valor_de_contingencia`;
  - `tests/test_macro_context.py::test_taxa_real_sem_rede_no_import`;
  - `tests/test_taxa_real_cascata.py::test_registro_entra_em_dados_fora_do_prompt`;
  - `tests/test_rastreabilidade.py::test_relatorio_mostra_a_taxa_real_e_a_fonte`;
  - mutation ≥ 80% em `sentinela.data.taxas*` e no provedor novo, se houver;
  - golden inalterado; nenhum teste existente muda;
  - gate da fase.

- [ ] **F2B-1** · fix · `fix: discount Gordon at the real cost of equity` · **[golden]** **[TAXA]**
  Armadilha 1; F-4 e F-6; checkpoint, seção 4, item 2 (regime real); PLANO, F2B-1. Pré-condição: `docs/metodologia/taxa-real.md` e `docs/metodologia/gordon.md` aprovadas; sem isso, `[!]`.
  - **Gordon 2.0.0.** Regime REAL. k = custo de capital real do F2B-30; g real pela definição aprovada na ficha (decisão do g real da [TAXA]); D1 = D0 × (1 + g real); teto e mínimos pela ficha. `requires` sem `selic`; sem a taxa, "insumo ausente". Changelog.
  - **`cost_of_equity_real`** (`config.py:234-236`) passa a delegar ao F2B-30 (PLANO: "via `cost_of_equity_real`"). O `GordonParams` perde o prêmio, e `valuation_engine.py:106` deixa de ler `GORDON_PREMIO_RISCO`.
  - **Motor.** Passa o k e a inflação ao Gordon; a Selic (`valuation_engine.py:177`) fica só para o Bazin, até o F2B-31.
  - **Regime (F-6).** Um teste calcula o mesmo cenário pelo método (real) e à mão no nominal (k por Fisher); os valores batem.
  - **Seção B.** `test_b_gordon_desconta_pela_selic_nominal_mais_premio` e `test_b_gordon_acompanha_a_selic_um_para_um` (`:115` e `:125`) são reescritos para afirmar a correção (k real; o Gordon não acompanha a Selic), primeiro como xfail estrito, depois sem a marca, em PASS, com o comentário "resolvida no F2B-1".
  - **Seção A.** Não muda: o F2B-7 já levou para a seção B os números que dependem da taxa. Os testes que ele marcou com o F-4 viram aqui, por xfail estrito → marca retirada → PASS, com o valor da conta à mão pela ficha (semente do F2B-30: NTN-B de 7%, inflação de 5,5%, prêmio-base).
  - **Golden.** O harness ganha a taxa por caso e uma grade nova (k real perto do g real; NTN-B de 4% a 8%; inflação de 2% a 6%). Alterados só os casos de ações em que o Gordon calcula antes ou depois: `--onde "caso['motor'] == 'acoes' and 'Gordon' in ((saida_antiga or {}).get('metodos_usados') or '') + ((saida_nova or {}).get('metodos_usados') or '')"`. Inclusões: a grade nova. Remoções: nenhuma.
  - **Relatório do F1-12.** Gordon 2.0.0, k, g real e a fonte da taxa.

  **Testes que mudam:** em `tests/test_methods_gordon.py`, os que fixam k = Selic + prêmio, o regime nominal e a versão, e `::test_formula_igual_a_da_v1` e `::test_mesma_ordem_de_operacoes_da_v1`, que calculam o esperado com uma cópia da fórmula da V1 (auditoria externa da 2A, correção 7): saem, porque a fórmula da V1 deixa de valer, e o valor de referência passa a ser o exemplo da ficha (D28); `tests/test_registry.py` (versão e changelog); `tests/test_macro_context.py::test_cost_of_equity_real`; em `tests/test_valuation_engine.py` e `tests/test_valuation_engine_inputs_taxa.py`, os que fixam o Gordon pela Selic; em `tests/test_rastreabilidade.py`, o texto do Gordon. Lista e justificativa no diário.

  **Aceite:**
  - `tests/test_methods_gordon.py::test_k_e_o_custo_de_capital_real` passa por xfail estrito → correção → marca retirada → PASS;
  - `::test_g_nominal_vira_real_por_fisher`, `::test_real_e_nominal_dao_o_mesmo_valor`, `::test_sem_taxa_real_abstem` e `::test_exemplo_da_ficha` (valor da ficha, D28);
  - os dois testes do F-4 da seção B por xfail estrito → marca retirada → PASS;
  - mutation de `sentinela.methods*` ≥ 80%, por módulo no diário;
  - golden pela regra;
  - diário (gate do PLANO): antes → depois no universo inicial, com prêmio de 4%, 5% e 7%;
  - gate da fase.

- [ ] **F2B-31** · fix · `fix: take the Selic out of the Bazin rate` · **[golden]** **[BAZIN]**
  F-5; armadilha 5. Pré-condição: `docs/metodologia/bazin.md` aprovada com a [BAZIN] em (b) ou (c); em (a) ou (d), o item sai no marcador.
  - **Bazin 2.0.0.** Taxa pela opção: (b) taxa fixa da ficha, constante nova do `MacroContext`; (c) custo de capital real do F2B-30, regime REAL. `requires` sem `selic`; o `BazinParams` perde o piso da Selic. O gate de 5% e o alerta de armadilha ficam. Changelog.
  - **Seção A.** Não muda (F2B-7). Os testes que o F2B-7 marcou com o F-5 viram aqui, por xfail estrito → marca retirada → PASS.
  - **Golden.** Alterados só os casos de ações em que o Bazin calcula antes ou depois: `--onde "caso['motor'] == 'acoes' and 'Bazin: R$' in ((saida_antiga or {}).get('metodos_usados') or '') + ((saida_nova or {}).get('metodos_usados') or '')"`. Inclusões: grade da taxa do Bazin.
  - **Relatório do F1-12.** A taxa do Bazin e a fonte; a seção "Selic usada" sai se nenhum método de ação a usar mais.

  **Testes que mudam:** em `tests/test_methods_bazin.py`, os que fixam a taxa pela Selic e a versão; `tests/test_registry.py`; em `tests/test_valuation_engine.py`, os que fixam o Bazin pela Selic. Lista no diário.

  **Aceite:**
  - `tests/test_methods_bazin.py::test_taxa_do_bazin_nao_e_a_selic` passa por xfail estrito → correção → marca retirada → PASS;
  - `::test_gate_de_5_por_cento_continua` e `::test_exemplo_da_ficha`;
  - mutation de `sentinela.methods*` ≥ 80%;
  - golden pela regra;
  - diário: antes → depois no universo inicial, como no F2B-1;
  - gate da fase.

- [ ] **F2B-2** · fix · `fix: compare FII yield with NTN-B plus the historical spread` · **[golden]** **[FII]**
  PLANO, F2B-2; checkpoint, seção 4, item 3; F-9; pendência "DY do Informe Mensal de FII". Pré-condição: `docs/metodologia/fii.md` aprovada.
  - **Rendimento do FII 2.0.0** (nome da lente pela ficha; o singleton `_FII_YIELD` fica). Preço justo = preço × DY ÷ (NTN-B do vértice + spread). Spread pela ficha, como constante do `MacroContext`, com a data e a janela de cálculo no comentário e na ficha; DY pela fonte da ficha (o Informe do F2B-28 ou o da cascata). `requires` sem `selic` (sai a conta de `sentinela/methods/fii_yield.py:53`).
  - **Contexto.** Selic líquida e P/VP aparecem na saída e no relatório, sem formar o preço justo. O score segue a opção da [FII].
  - **Vacância.** Sem fonte oficial (F2A-23); o risco "vacância não informada" só se a ficha o adotar.
  - **Seção A.** Não muda (F2B-7). Os testes que o F2B-7 marcou com o F-9 (o antigo A4, `:100`) viram aqui, por xfail estrito → marca retirada → PASS.
  - **Seção B.** `test_b_fii_nao_considera_o_patrimonio_no_fair_value` (`:135`) troca o número do benchmark e continua caracterizando o F-9 (o preço justo igual para P/VP 0,5 e 2,0). Se a [FII] tirar os pontos de P/VP do score, a asserção do score (`barato['score_final'] > caro['score_final']`, `:141`) muda neste item, com a justificativa no diário; a do preço justo fica.
  - **Golden.** Alterados só casos de FII: `--onde "caso['motor'] == 'fii'"`. Inclusões: grade da NTN-B e do spread.
  - **Relatório do F1-12.** A taxa da lente e a fonte (PLANO: "cada método documenta a taxa que usa").

  **Testes que mudam:** `tests/test_methods_fii_yield.py` (fórmula pela Selic líquida, nome e versão); em `tests/test_fii_engine*.py`, os que fixam o preço justo ou o score pela Selic líquida; `tests/test_registry.py`; `tests/test_rastreabilidade.py`. Lista no diário.

  **Aceite:**
  - `tests/test_methods_fii_yield.py::test_preco_justo_pela_ntnb_mais_spread` passa por xfail estrito → correção → marca retirada → PASS;
  - `::test_selic_liquida_nao_forma_o_preco_justo`, `::test_sem_ntnb_abstem` e `::test_exemplo_da_ficha`;
  - mutation de `sentinela.methods*` ≥ 80%;
  - golden pela regra;
  - diário: antes → depois nos FIIs atuais do universo inicial (preço justo, upside, score e classificação agrupada), com o spread da ficha e os de sensibilidade;
  - gate da fase.

- [ ] **F2A-39** · fix · `fix: map BTG Pactual unit through the source corrections table` · **[BTG]** **[CORREÇÕES]**
  Veio da 2A (decisão do Marcos de 13/10/2026). O COTAHIST liga o BPAC11 ao ISIN `BRBPACUNT006`, e o FCA traz a unit do BTG com o código `000000`. Pré-condição: a [BTG] aceitou a fonte da B3 da pergunta 6 do F2B-21; recusada, o item sai no marcador, e o BTG segue em exclusão provisória.
  - **Tabela de correções.** Linha do BPAC11: CNPJ 30.306.294/0001-45, código na fonte `000000`, a evidência do defeito (FCA 2025 e 2026, `valor_mobiliario`) e a da ligação (fonte da B3, campo e data). Se a tabela não tiver onde citar a evidência da ligação, o item a acrescenta: obrigatória quando a ligação não vem do próprio arquivo do defeito, e linha sem ela é rejeitada.
  - **Unit.** Composição "1 ON E 2 PNA". O diário registra `acoes_por_unit`, a classe PNA e o LPA da unit (nota do F2A-36: componente de classe única cai no recalculado com marca); composição não reconhecida, o motivo.

  **Aceite:**
  - `tests/test_referencia_correcoes.py::test_unit_entra_pela_tabela_com_a_evidencia_da_ligacao` passa por xfail estrito → correção → marca retirada → PASS;
  - `::test_ligacao_sem_evidencia_e_rejeitada`;
  - mutation ≥ 80% em `sentinela.data.referencia*`;
  - golden inalterado;
  - diário: cobertura (`python -m sentinela.data.referencia --cobertura`) antes → depois, o registro do BPAC11 e o LPA da unit;
  - gate da fase.

- [ ] **F2B-4** · fix · `fix: enforce method scope by asset class and statement model` · **[golden]** **[FINANCEIRAS]**
  PLANO, F2B-4; P7; armadilha 17; `sentinela/methods/registry.py` ("Aplicar e estreitar é o F2B-4").
  - **Contrato.** `MethodInputs` ganha a classe do ativo e o modelo da demonstração (enum novo em `sentinela/domain/enums.py`: empresa, banco, seguradora). `ValuationMethod.calcular` confere o escopo declarado e se abstém com o motivo ("classe <classe> fora do escopo do método", "modelo <modelo> fora do escopo do método"). Sem classe nem modelo nos insumos (chamadas antigas), nada muda.
  - **Escopo.** Graham, Bazin, Lynch e Gordon: STOCK e UNIT, modelo empresa. Rendimento e P/VP do FII: FII. Cada método ganha versão menor no changelog. Sem ficha, pela dispensa do Marcos de 18/10/2026, limitada à aplicação do escopo (gate da fase): o diff de cada método só declara e aplica o escopo; mudança de fórmula, insumo, regime ou parâmetro no mesmo item reprova a revisão.
  - **Modelo** pelo setor do índice (F2A-2), pela regra da [FINANCEIRAS]. Sem setor (fora do índice): empresa, com a limitação gravada pela cascata em `dados['riscos_dados']` (diário do F2A-9), nunca pelo motor: por isso nenhum caso existente do golden muda (auditoria externa da 2A, correção 5).
  - **Motor.** Todos os métodos abstidos por escopo: a abstenção no formato do F2A-29 (sem `fair_value`, `upside` nem `score_final`), com o motivo. A guarda do F2A-29 passa a tirar espaços da classe (" ETF" passava; revisão do F2A-29). Seguradoras ficam em abstenção até lente própria (PLANO, seção 14); bancos, até o F2B-32.
  - **Relatório do F1-12.** O escopo de cada método e o motivo; o cabeçalho deixa de dizer "ação" para classe fora do escopo (revisão do F2A-29).
  - **Golden.** Só inclusões: casos com setor de banco, de seguradora e das variantes da [FINANCEIRAS], com controle de setor não financeiro. Nenhum caso existente tem setor: `--onde "False"`.

  **Testes que mudam:** `tests/test_registry.py` (versões) e, em `tests/test_methods_contrato*.py`, os que fixam o `applies_to` só declarado (lista no diário).

  **Aceite:**
  - `tests/test_valuation_escopo.py::test_banco_e_seguradora_nao_recebem_metodos_de_empresa` passa por xfail estrito → correção → marca retirada → PASS;
  - `tests/test_methods_contrato.py::test_escopo_e_aplicado` e `::test_sem_classe_nem_modelo_nada_muda`; `tests/test_valuation_escopo.py::test_classe_com_espacos_e_reconhecida` e `::test_abstencao_por_escopo_nao_traz_numero`;
  - mutation de `sentinela.methods*` ≥ 80%;
  - golden pela regra;
  - diário: os tickers do índice e do universo inicial que passam a se abster, por setor;
  - gate da fase.

- [ ] **F2B-44** · fix · `fix: record IF.data provenance and the reference instant`
  Corrige o BUG-2A-19 e o BUG-2A-20 (registrados no F2B-36), antes de a Basileia aparecer na lente de bancos (F2B-32).
  - Cada arquivo baixado do IF.data registra a proveniência da D16 por `proveniencia.registrar_sem_falhar`, como os outros provedores, e o `Capital` a carrega.
  - A validade do cache é medida contra o instante de referência recebido (parâmetro), não contra o relógio.
  - Resposta vazia (`value: []`) não é gravada no cache: a data-base ainda não publicada é consultada de novo na próxima análise.

  **Aceite:**
  - os dois testes de `tests/regressao/` com a marca retirada, em PASS, e o registro atualizado;
  - `tests/test_contratos_provedores.py` verde, com a proveniência do IF.data no contrato;
  - mutation ≥ 80% em `sentinela.data.providers.ifdata*`;
  - golden inalterado;
  - gate da fase.

- [ ] **F2B-3** · feat · `feat: add justified price-to-book lens for banks` · **[BANCOS]**
  PLANO, F2B-3 (a lente; a ligação no motor é o F2B-32); checkpoint, seção 4, item 5; D22. Pré-condição: `docs/metodologia/bancos.md` aprovada.
  - `sentinela/methods/bancos.py`: P/VP justificado = (ROE − g) ÷ (k − g), no regime da ficha; valor = P/VP justificado × VPA; escopo STOCK e UNIT com modelo banco; abstenções da ficha; versão 1.0.0 no `registry.py`, com changelog.
  - Insumo que a ficha pedir e o `MethodInputs` não tiver (o payout pela DVA, por exemplo) entra no mesmo item, opcional.
  - Basileia e inadimplência não entram no valor.
  - Nenhum motor chama a lente: golden inalterado.

  **Aceite:**
  - `tests/test_methods_bancos.py::test_pvp_justificado`, `::test_exemplo_da_ficha` (D28), `::test_real_e_nominal_dao_o_mesmo_pvp`, `::test_roe_nao_maior_que_g_abstem`, `::test_k_nao_maior_que_g_abstem` e `::test_vpa_nao_positivo_abstem`;
  - `tests/test_contratos_import.py` verde com o arquivo novo na grade;
  - mutation de `sentinela.methods*` ≥ 80%;
  - golden inalterado;
  - gate da fase.

- [ ] **F2B-32** · fix · `fix: value banks with the bank lens` · **[golden]** **[BANCOS]**
  Armadilha 17. Desde o F2B-4, bancos estão em abstenção.
  - **Motor de ações.** Modelo banco → a lente do F2B-3, com ROE dos controladores (F2A-9), VPA e payout pelas fontes da ficha, k e inflação (F2B-30). Preço justo, upside, score e rótulos pelas regras da V1 (o F2C as refaz); `metodos_usados` com a lente. Singleton novo e relatório do F1-12 no mesmo commit.
  - **Qualidade.** A Basileia aparece, com o alerta pela ficha (limiar e norma citados); a inadimplência, ou a limitação; as datas diferentes da Basileia e da DFP, declaradas. O `divida_pl` não é lido.
  - **Golden.** Alterados só os casos de banco incluídos no F2B-4: `--onde "entrada.get('setor') == 'Bancos'"`, mais os setores que a [FINANCEIRAS] puser no modelo banco. Inclusões: grade de ROE, g e VPA.

  **Aceite:**
  - `tests/test_valuation_bancos.py::test_banco_recebe_a_lente_de_bancos` passa por xfail estrito → correção → marca retirada → PASS;
  - `::test_sem_ifdata_a_limitacao_aparece` e `::test_banco_sem_vpa_se_abstem`; com o alerta adotado, `::test_basileia_abaixo_do_limite_gera_alerta`;
  - golden pela regra;
  - diário: os bancos do universo inicial, com P/VP de mercado, P/VP justificado, preço justo, upside e classificação agrupada, com prêmio de 4%, 5% e 7%;
  - gate da fase.

- [ ] **F2A-10** · fix · `fix: abstain below the liquidity threshold` · **[golden]** **[LIQUIDEZ]** **[D7]**
  Veio da 2A. Insumo: a distribuição do diário do F2A-26. **Regra decidida pelo Marcos em 18/10/2026 ([LIQUIDEZ]):**
  - **janela:** 63 pregões (a de 252 depende da série anual do COTAHIST, F3-4);
  - **métrica:** presença (pregões com negócio ÷ pregões da janela) e volume financeiro diário mediano, as duas condições juntas. Referência: o critério do NEFIN (FEA-USP) para os fatores de risco, "negociada em mais de 80% dos pregões do ano anterior, com volume diário acima de R$ 500 mil" (`nefin.com.br`, metodologia, seção 3);
  - **valor:** ações e units, presença ≥ 80% e mediana ≥ R$ 500 mil; FIIs, presença ≥ 80% e mediana ≥ R$ 100 mil (o NEFIN não cobre FII, e o volume deles é menor);
  - **texto:** "liquidez abaixo do mínimo para análise: presença de X% e volume mediano de R$ Y nos últimos 63 pregões (mínimo: 80% e R$ Z)";
  - **sem dado:** falha de coleta (mês ausente, download com erro) segue sem o gate, com o aviso "liquidez não medida: <motivo>"; ticker sem negócio na janela tem presença 0 e se abstém;
  - **sem exceção de listagem recente** (decisão de 18/10/2026, depois da auditoria DOCUMENTO: o bloco de liquidez não traz a data de estreia, e o COTAHIST não distingue estreia de volta após suspensão). Papel recém-listado segue a janela de 63 pregões e se abstém até ter presença ≥ 80%; o texto da abstenção mostra a presença.
  - **Regra.** Função pura em `sentinela/data/liquidez.py`: recebe o bloco `dados['liquidez']` e a regra decidida, e devolve o motivo da abstenção, o aviso ou nada. Olha `incompleta` e `meses_ausentes` juntos (diário do F2A-26), separa falha de coleta de ausência de negócio (ressalva da 2ª passada do Gemini a `liquidez.py`: papel que parou de negociar não pode sair com presença zero sem se abster) e trata o ativo listado no meio da janela como os demais (sem exceção).
  - **Parâmetros** no `MacroContext`.
  - **Motores (ações e FII).** Guarda depois da de classe e antes da de distressed. Abstenção no formato do F2A-29, sem número, com o texto decidido. Sem a chave `liquidez` (chamada que não mede), nada muda. Bloco sem dado: pela parte 5 da decisão.
  - **Relatório do F1-12.** A linha de liquidez deixa de dizer "ainda sem uso nos métodos" e mostra a regra.
  - **Golden.** Só inclusões (acima, no limite e abaixo, sem dado, janela incompleta, mês ausente): `--onde "False"`.

  **Aceite:**
  - `tests/test_liquidez_gate.py::test_abaixo_do_limiar_se_abstem` (ações e FII) passa por xfail estrito → correção → marca retirada → PASS;
  - `::test_sem_chave_nada_muda`, `::test_falha_de_coleta_segue_com_aviso`, `::test_sem_negocio_na_janela_se_abstem`, `::test_recem_listado_com_presenca_baixa_se_abstem`, `::test_limiar_por_classe` e `::test_abstencao_sem_numero`;
  - mutation ≥ 80% em `sentinela.data.liquidez*`;
  - golden pela regra;
  - diário: ativos do índice e do universo inicial abaixo da regra, por classe e por condição (presença, volume, as duas);
  - gate da fase.

- [ ] **F2B-33** · docs · `docs: sync agent instructions with phase 2B rates and scope`
  Valida contra o código e corrige `CLAUDE.md`, `AGENTS.md` (menos a seção "Fase atual", que é do Marcos), a tabela da Fase 2B do `docs/PLANO.md` (IDs finais e a ordem desta fila) e, se o F2A-39 foi feito, a exclusão provisória do BTG em `docs/decisoes/universo-inicial.md`.

  **No `CLAUDE.md`:**
  - "Arquitetura real": contagens de linha e os módulos novos (taxa real, Tesouro, rendimento do FII, lente de bancos);
  - "Fluxo de dados real": a taxa real e o rendimento do FII;
  - regras econômicas: taxa real e prêmio, Bazin, benchmark do FII, lente de bancos, escopo e liquidez; o "Alvo (D15, Fase 2B)" vira regra vigente;
  - armadilhas 1, 2 (o trecho do FII), 5, 9 e 17;
  - a contagem da suíte e as "Fases".

  **No `AGENTS.md`:** a contagem da suíte e o "Contexto que evita retrabalho".

  Se algo divergir, corrige o documento, nunca o código.

  **Aceite:**
  - diff só nesses arquivos;
  - cada linha citada conferida com `grep -n` e listada no diário;
  - `CLAUDE.md` e `AGENTS.md` sem contradição entre si.

- [ ] **F2B-34** · levantamento · `docs: propose phase 2C queue`
  O `fable-architect` propõe a fila da 2C em `docs/loop/fila-fase2c-proposta.md`, no formato desta. Partes:
  - a seção "Fase 2C" do PLANO e a seção 15 (histerese, lentes e valuation reverso);
  - o checkpoint da Fase 0, seção 4, item 4 (janela por método), e o dossiê, pergunta 4;
  - ADR-0003, D24 a D26;
  - o diário desta fase e o da 2A, nas pendências com destino na 2C: F2C-1 (TTM, proventos da DVA, JCP bruto, ações do TTM), F2C-2 (EBITDA ≤ 0, margens), F2C-3 (ROE e P/L no score, penalidades em dobro), F2C-4, F2C-9 e F2C-10;
  - os candidatos da auditoria do Gemini que a [AUDITORIA] mandou para a 2C (achado 5, decisões A e D) e a pergunta 7 do F2B-21.

  Nada é implementado.

  **Aceite:** arquivo no formato desta fila; todo item com aceite verificável; nenhuma decisão do Marcos tomada pelo texto.

- [ ] **F2B-45** · fix · `fix: stop parsing Portuguese debt text in the stock engine` · **[golden]**
  Saiu do F2B-5: limpeza não muda golden (auditoria externa da 2A, correção 4). PLANO, seção 10 (texto de dívida). No motor de ações (`valuation_engine.py:278-291`), a conversão de `divida_liq_ebitda` em texto pt-BR ("1.234,56") não tem fonte desde o F2A-22. Sai a conversão; valor que não é número finito segue "alavancagem não avaliada", sem penalidade, como hoje o texto inválido.

  **Testes que mudam:** `tests/test_valuation_engine.py::test_divida_liq_ebitda_brazilian_format` e os outros que passam dívida em texto. A auditoria da 2A apontou que eles só conferiam `0 <= score_final <= 100`; passam a afirmar "alavancagem não avaliada" e a ausência da penalidade.

  **Aceite:**
  - `tests/test_valuation_engine.py::test_divida_em_texto_nao_e_avaliada` passa por xfail estrito → correção → marca retirada → PASS;
  - diário: `git grep` confirma que nenhuma fonte da cascata entrega texto nesse campo;
  - golden: só mudam casos com dívida em texto, `--onde "isinstance(entrada.get('divida_liq_ebitda'), str)"`;
  - gate da fase.

- [ ] **F2B-5** · limpeza · `chore: clean up phase 2B residue`
  Faz só o que segue, conforme o PLANO (seção 10: texto de dívida; seção 11: "Selic como taxa de desconto"), o inventário (propriedades do `MacroContext` sem leitor) e a decisão de 5/10/2026 (script de invalidação):
  - **Selic como taxa de desconto,** sem leitor depois desta fase: `GORDON_PREMIO_RISCO` (`config.py:159`); `BAZIN_TAXA_MIN` (`:147`), se o F2B-31 foi feito; `FII_DY_SELIC_RATIO_MIN` (`:184`), se a [FII] trocou o benchmark do score; o campo `selic` do `MethodInputs` e a checagem dele no contrato, se nenhum método o exigir. Saem também os testes que só cobriam o que sai.
  - **NTN-B antiga:** `_fetch_ntnb` (`:271-301`), `ntnb_longa` e `NTNB_LONGA_FALLBACK` (`:122`), com os testes deles em `tests/test_macro_context.py`. `cdi`, `ipca_12m` e as contingências deles ficam para o F3-1, como o inventário prevê.
  - **Script de invalidação:** `scripts/invalidar_cache_cvm.py` e `tests/test_invalidar_cache_cvm.py` saem com `git rm` (decisão de 5/10/2026; ver [CACHE]).
  - **Correções automáticas seguras** (inventário, seção 3.1) em `valuation_engine.py` e `config.py`.
  - **Não saem nesta fase:**
    - `get_selic_atual` e `SELIC_FALLBACK` (contexto do FII, Markowitz até o F2C-9, E-6 no F3-1);
    - `FII_FATOR_IR`, se a Selic líquida ficou como contexto;
    - `FII_MANUAL_FALLBACK` e `DY_PERCENTUAL_THRESHOLD` (F2C-10; o harness lê o segundo para as ids);
    - a reimplementação dos métodos no `auditoria.py`, com a Selic (F2C-8).

  Depois, roda de novo o vulture, o `ruff check . --statistics` e o deptry, e atualiza `docs/limpeza/inventario.md` (antes → depois), com os resíduos que ficaram para outras fases.

  **Aceite:**
  - gate da fase;
  - golden inalterado (`git diff --exit-code HEAD -- tests/fixtures/golden_motores.jsonl`);
  - testes alterados só nos pontos listados, sem asserção enfraquecida (conferido no diff);
  - `git grep` de cada nome removido sem resultado fora de `docs/`, do `README.md` (arquivo do ticket C-A do Jules) e dos scripts de levantamento de fases anteriores (`scripts/dossie_fase2.py`, `scripts/levantamento_fase2a.py`), que se reproduzem no checkout da tag da fase deles; o diário lista as ocorrências que ficaram (auditoria externa da 2A, correção 4);
  - referências de linha do `CLAUDE.md` e do `AGENTS.md` para os arquivos tocados conferidas;
  - inventário atualizado;
  - lista para o Marcos apagar à mão: `data/tesouro/`, o cache do provedor de inflação (se houver) e os arquivos do F2B-21 em `outputs/levantamento_cache/`.

- [ ] **F2B-6** · docs · `docs: add phase 2B summary and archive loop files`
  Nesta ordem:
  1. escrever `docs/loop/pr-fase-2b.md` a partir do diário, com:
     - itens e commits;
     - testes antes → depois;
     - mutação dos módulos novos e de `sentinela/methods/`;
     - cada mudança de comportamento, com o efeito medido e o diff do golden (predicado e contagem);
     - o antes → depois da taxa real no universo inicial, com prêmio de 4%, 5% e 7% (gate do PLANO);
     - as fichas aprovadas e as auditorias delas;
     - decisões pendentes;
     - resíduos que ficaram para o Marcos;
     - o que revisar primeiro;
  2. registrar este item no diário e marcá-lo `[x]`;
  3. mover com `git mv` os arquivos `fila.md`, `diario.md` e `pr-fase-2b.md` para `docs/loop/historico/fase-2b/`;
  4. criar um `docs/loop/fila.md` novo contendo só:
     `[DECISÃO] Fase 2B encerrada. Histórico em docs/loop/historico/fase-2b/. Próxima fila aguardando aprovação: docs/loop/fila-fase2c-proposta.md.`
  5. commitar e rodar `cat docs/loop/fila.md`.

  **Aceite:**
  - `docs/loop/historico/fase-2b/` com `fila.md`, `diario.md` e `pr-fase-2b.md`, movidos por `git mv` (`git log --follow` mostra o histórico de cada um);
  - `docs/loop/fila.md` com só a linha acima;
  - o resumo traz cada seção listada no passo 1, e cada commit citado existe no `git log`.

- [DECISÃO] **Fim da Fase 2B.** O Marcos, pelo ciclo (`docs/loop/ciclo-de-fase.md`, etapas 6 a 8):
  1. revisa as mudanças de comportamento na ordem do resumo, com o diff do golden de cada uma, e o antes → depois da taxa real (gate do PLANO);
  2. gera relatórios reais com o F1-12 para uma ação pagadora de dividendos, um banco, uma seguradora, um FII de tijolo, um de papel, um ativo abaixo do limiar de liquidez e o BPAC11 (se o F2A-39 foi feito). Confere NTN-B, vértice, data-base, fonte, prêmio, inflação, spread e os motivos de abstenção. Os relatórios saem em `outputs/`, fora do git;
  3. reconstrói o índice (`python -m sentinela.data.referencia`), se a tabela de correções mudou (F2B-13, F2A-39), e limpa o cache de fundamentos inteiro, porque o script por ticker saiu no F2B-5: `python -c "import sqlite3; c = sqlite3.connect('sentinela_v6.db'); c.execute('DELETE FROM fundamentals_cache'); c.commit()"`. Sem lista de tickers, nada da carteira em arquivo;
  4. faz o push do branch `v2/fase-2b`, confere o CI e roda a auditoria da fase (etapa 6): `python scripts/auditar.py codex fase --fase 2b` e `python scripts/auditar.py gemini fase --fase 2b`. O Claude (chat) consolida em `docs/loop/historico/fase-2b/auditoria-externa.md`; todo bug confirmado vira teste de regressão; bloqueio que a fase criou vai para uma fila de fechamento, e o resto ganha destino na proposta da 2C;
  5. revisa a proposta da 2C (F2B-34) pela etapa 2 do ciclo;
  6. fecha a fase (etapa 7): auditoria rápida da fila de fechamento, se houver; PR com `docs/loop/historico/fase-2b/pr-fase-2b.md` como descrição e CI verde; merge com "Create a merge commit"; tag `v2-fase-2b`; branch apagado; "Fase atual" do `AGENTS.md`; caches listados no F2B-5 apagados à mão;
  7. faz a retro (etapa 8) e decide o piloto do ai-memory (`docs/loop/workflow-multiagente.md`, seção 8).

## Riscos e decisões do Marcos

- **Decisões da ativação** (respondidas pelo Marcos em 18/10/2026, com as opções e a sugestão do Claude no chat):
  - **[SEÇÃO A]** (gate do PLANO para a 2B). Quatro testes da seção A fixam números que dependem da Selic como taxa (`tests/test_financeiro_pre_refactor.py`): A1 (`:71`, mediana de 60 no Bazin), A2 (`:81`, Graham + Bazin = 105), A3 (`:92`, Bazin de 50 no limite de 5%) e A4 (`:100`, FII de 110 pela Selic líquida). Opções: (a) seção A literal, com o F2B-2 e o F2B-31 travados; (b) reescrita controlada em cada item de taxa; (c) mover antes para a seção B.
    **Decisão: (c).** O F2B-7 move os números para a seção B, com `quebra_esperada` e a marca do achado; os itens de taxa os viram por xfail estrito → PASS (D27), e a seção A não muda depois dele.
  - **[LIQUIDEZ]** (F2A-10; PLANO, seção 15). Dados do diário do F2A-26 (jul–set/2026), na janela de 63 pregões e, entre parênteses, na de 21:
    - ações (390) abaixo de R$ 100 mil, 500 mil, 1 milhão e 5 milhões por dia: 157 (145), 190 (180), 203 (191) e 252 (231);
    - units (13): 4, 4, 4 e 5;
    - FIIs (382): 241 (209), 303 (273), 323 (292) e 368 (331);
    - presença abaixo de 80%, 90% e 95%: ações 87, 98 e 105 (74, 78 e 82); units 2, 3 e 3 (2, 2 e 2); FIIs 133, 140 e 150 (96, 105 e 114).

    **Decisão:** janela de 63 pregões; presença e volume mediano juntos; ações e units com presença ≥ 80% e mediana ≥ R$ 500 mil (critério do NEFIN, FEA-USP); FIIs com presença ≥ 80% e mediana ≥ R$ 100 mil; texto e regra sem dado no F2A-10. Revisão do mesmo dia, depois da auditoria DOCUMENTO: sai a exceção de listagem recente, porque o bloco não traz a data de estreia; papel recém-listado se abstém até ter presença ≥ 80%. O ativo abaixo da regra não recebe nenhum método; a contagem da união das duas condições sai no diário do F2A-10.
  - **[FICHA 1.1]** (passo 6 do [DECISÃO] da 2A; D21). **Decisão: os quatro pontos adotados**, escritos na ficha por ação, versão 1.1 (seções 7.7 a 7.10), que passa por auditoria FICHA antes da ativação:
    - (a) escala pelo lucro consolidado quando o dos controladores se abstém, confirmada pela quantidade de ações do yfinance (7.7, revista depois da auditoria): F2B-10. Efeito: das 9 companhias, 7 candidatas a ter o VPA de volta, a KLBN11 entre elas;
    - (b) linha agregada como LPA da espécie em companhia de espécie única, com a 3.99 aceita só com o recalculado a até 10% (7.8, revista depois da auditoria): F2B-11. Efeito: BBAS3 com LPA 2,40 e VPA; o Pine segue em abstenção;
    - (c) a linha "PN" única vale para todas as classes preferenciais, na ação avulsa e na unit (7.9, opção (i)): F2B-12. Efeito: USIM5 com LPA;
    - (d) espécie corrigida pela tabela de correções, com a Composição do Capital e a DRE do mesmo documento como evidência (7.10): F2B-13. Efeito: MGLU3 com o LPA divulgado da ON.

    Sem decisão nova: a D20 à letra (antigo F2B-9) foi corrigida no F2A-41; a conferência só com o divulgado coerente (achado 6; ficha, 7.3 e 7.5) é o F2B-14 (BUG-2A-11).
  - **[AUDITORIA]** (auditorias da 2A: Gemini em duas passadas e Codex; consolidação em `docs/loop/historico/fase-2a/auditoria-externa.md`). **Decisões:** achado 1 em (a); alerta do achado 7 acima de 10%; piso do ROE em −2; guardas de validade de insumo nos métodos sem ficha (F2B-41 e F2B-42); destinos da tabela:

    | Origem | Achado | Destino |
    |---|---|---|
    | BUG-2A-01 (achado 1) | valores ≤ 0 da CVM descartados no merge; prejuízo como dado ausente | F2B-8, opção (a) |
    | BUG-2A-02 a 05 (achados 2 e 9) | reservas dos controladores contra a D20 | corrigidos no F2A-41 (o F2B-9 saiu) |
    | BUG-2A-06 (achado 3) | P/VP não finito na saída do motor de FII | corrigido no F2A-42 (o F2B-19 saiu) |
    | BUG-2A-07 (achado 4) | ativo fora do índice recebe métodos de ação | corrigido no F2A-43 (o F2B-15 saiu) |
    | BUG-2A-08 e 09 | textos do relatório de rastreabilidade | corrigidos no F2A-44 |
    | BUG-2A-10 (achado 5) | TTM sem a regra 7.2 | F2B-37 |
    | BUG-2A-11 (achado 6) | conferência com o divulgado antes do filtro de coerência | F2B-14 |
    | BUG-2A-12 (achado 7) | FII sem `valores_por_fonte['CVM']` | F2B-16, com o alerta de 10% |
    | BUG-2A-13 (achado 8) | FII com o aviso de cobertura das companhias | F2B-17 |
    | BUG-2A-14 a 18 | Informe sem desempate por versão; DY inválido sobrescrevendo válido; ZIP vazio do COTAHIST; `FiiNav` com P/VP ≤ 0; `Graham` com VPA < 0 | F2B-38 a F2B-42 |
    | BUG-2A-19 e 20 (2ª passada; conferidos pelo Claude em 18/10/2026) | IF.data sem a proveniência da D16; cache pelo relógio e resposta vazia guardada por 7 dias | registro no F2B-36; correção no F2B-44 |
    | decisão A | dívida positiva com EBITDA ≤ 0 escapa da penalidade | F2C-2 |
    | decisão B | holdings financeiras no modelo de empresa | [FINANCEIRAS], no marcador (F2B-4 e F2B-32) |
    | decisão C | ROE sem piso | F2B-18, piso de −2 |
    | decisão D | margem consolidada ao lado do ROE dos controladores | F2C-2 |
    | ressalva ao F2A-25 | preço negativo nos motores | F2B-20 |
    | correções 6 e 7 da auditoria, e ressalvas da 2ª passada sem destino | tesouraria, versão das linhas 3.99, PNA/PNB na divergência, completude de bancos e FIIs, BTCI11 e TRPL11, e as demais | conferência no F2B-21 (perguntas 7 e 8); confirmadas viram teste no F2B-43; destino no marcador |
    | correção 7 | testes do Gordon com o esperado copiado da V1 | F2B-1 |
    | correção 7 | rótulo "QUALIDADE — AGUARDAR" inalcançável, testado com `math.exp` simulado; teste do Lynch com o esperado copiado da V1 | proposta da 2C (F2C-3 e F2C-4; Lynch na ficha dele) |
    | 2ª passada | composição da unit reduz "PNA" a "PN" | F2B-12 |
    | 2ª passada | ticker sem negócio na janela sai com presença zero | F2A-10 (regra da [LIQUIDEZ]) |

    Efeito do achado 1 em (a): empresa com prejuízo deixa de levar −30 de confiança e "Dados fundamentais obrigatórios ausentes", o P/L negativo chega ao motor, e o Gordon e o Graham se abstêm pelas regras deles.
- **Decisões do marcador "Fichas da 2B, taxa e fontes".**
  - **[TAXA]** (F2B-22, F2B-23, F2B-26, F2B-27, F2B-30 e F2B-1; checkpoint, seção 4, item 2; PLANO, seção 15):
    - **g real (Gordon e lente de bancos;** auditoria externa da 2A, correção 1). Exemplo da 2ª passada do Gemini, conferido pelo Claude: preço 100, LPA 10, DY 6% (D0 = 6), payout 60% (retenção b = 40%), ROE 12%, NTN-B 7%, prêmio 5% (k real 12%), inflação 5,5%:
      - (i) g real = (1 + ROE × b) ÷ (1 + π) − 1 = 1,048 ÷ 1,055 − 1 = −0,66%; valor R$ 47,07. Equivale ao modelo nominal com k nominal por Fisher (1,12 × 1,055 − 1 = 18,16%) e g nominal de 4,8%: os dividendos crescem menos que a inflação sempre que ROE × b < π;
      - (ii) g real = ROE real × b, com ROE real = 1,12 ÷ 1,055 − 1 = 6,16%: g real = +2,46%; valor R$ 64,47 (+37%). Supõe que o patrimônio existente acompanha a inflação, e só a retenção gera crescimento real;
      - (iii) g real com teto de crescimento real de longo prazo (por exemplo, o do PIB), com a fonte do teto;

      a matriz do F2B-21 mostra o efeito no universo inicial;
    - **nome dos campos do Tesouro** ("taxa de compra" e "taxa de venda"): nomes neutros no código, com o nome oficial na proveniência, ou exceção à regra de vocabulário só para o título público (seção "Vocabulário");
    - **prêmio:** base de 5%, com 4% e 7% de sensibilidade, já decididos; o valor só é fixado depois da coleta da NTN-B com o Tesouro respondendo. Pelo dossiê (seção 2, com a NTN-B de contingência), k real de 11%, 12% e 14%, contra 20,75% hoje (Selic + 7%);
    - **vértice:** o mais perto de 10 anos, 2035, 2045, o mais longo, ou a média de 2035 em diante (o código de hoje). Efeito: os valores da pergunta 1 do F2B-21;
    - **tipo de taxa:** compra (a que o investidor recebe) ou venda;
    - **inflação da conversão:** IPCA de 12 meses (realizado), Focus (expectativa) ou implícita (mercado, no mesmo vértice). Com Fisher exato, tudo real e tudo nominal dão o mesmo valor (dossiê, seção 3); a escolha muda o g real do Gordon e da lente de bancos;
    - **defasagem máxima** da NTN-B: só a última data-base, ou N dias úteis com a data exibida. Além dela, abstenção, sem contingência;
    - **fonte:** Tesouro Nacional (oficial). Outra fonte, como a ANBIMA, só por decisão.
  - **[BAZIN]** (F2B-24 e F2B-31; F-5):
    - (a) manter a Selic: os testes que o F2B-7 marcou com o F-5 seguem como quebra esperada, a nota do Bazin segue o Copom (princípio 9 do PLANO) e o F-5 fica aberto;
    - (b) taxa fixa (6% no original): âncora estável no ciclo; regime e justificativa na ficha (D23); os testes marcados com o F-5 viram no F2B-31;
    - (c) k real sem crescimento real: coerente com o Gordon (g real = 0); os testes marcados com o F-5 viram no F2B-31;
    - (d) adiar para o F2C-5 (lentes): a Selic fica como taxa do Bazin até lá, e o F2B-5 não tira a `selic` do contrato.

    Efeito: a matriz do F2B-21 (pergunta 3).
  - **[FII]** (F2B-25, F2B-28 e F2B-2; checkpoint, seção 4, item 3):
    - **spread:** definição (mediana dos FIIs listados, por tipo, tijolo e papel, ou por fundo), janela (5 anos, 10 anos ou a série inteira) e atualização (constante datada, revista por versão da ficha, ou recalculada a cada análise, o que exige as séries em produção, da Fase 3). Pelo dossiê (seção 4), o spread desloca o nível e não a ordem;
    - **vértice:** o mesmo da taxa real, ou outro;
    - **DY:** o do Informe (F2B-28, oficial) ou o da cascata (yfinance e brapi), e a base (sobre o preço);
    - **benchmark do score** (hoje ±20 pela Selic líquida): (a) manter a Selic líquida, e a nota segue o ciclo, contra o princípio 9; (b) o mesmo benchmark do preço justo; (c) a Selic só exibida;
    - **papel e tijolo:** benchmark único, ou papel indexado ao CDI comparado com o CDI (F-9);
    - **vacância:** sem fonte oficial (F2A-23); o risco "vacância não informada" na saída, ou não;
    - **P/VP:** contexto pelo checkpoint; os pontos de score das faixas da V1 ficam ou saem.
  - **[BANCOS]** (F2B-26, F2B-3 e F2B-32; checkpoint, seção 4, item 5):
    - **g:** ROE × retenção, com o payout pela DVA (F2A-7) ou pelo DY da cascata (o do yfinance diverge nos bancos: F2A-16, pergunta 8), ou inflação + x;
    - **VPA:** só o da CVM (banco sem VPA se abstém; hoje o BBAS3, até a ficha 1.1 (b)), ou o de outras fontes como reserva;
    - **Basileia:** só exibida, ou alerta abaixo do mínimo regulatório, com a norma citada;
    - **inadimplência:** pela pergunta 5 do F2B-21, ou a limitação declarada;
    - **holdings de banco** (desconto sobre as participações, opcional no PLANO): fora desta fila; se o Marcos as quiser na 2B, item novo, com ficha própria.
  - **[FINANCEIRAS]** (decisão B do Gemini; F2B-4 e F2B-32). Hoje `contas_cvm.modelo_do_setor` põe no modelo banco só o setor "Bancos", e no de seguradora quem tem "seguradoras" no setor. Opções para o escopo dos métodos:
    - (a) o mapeamento de hoje: "Emp. Adm. Part. - Bancos", "Intermediação Financeira" e "Crédito Imobiliário" seguem como empresa, com os métodos de empresa e a alavancagem;
    - (b) os setores financeiros e as holdings deles saem dos métodos de empresa (abstenção), mesmo com balanço comum;
    - (c) pelo modelo da demonstração medido (2.07 ou 2.08 → banco), não pelo setor (o caso da XP, F2A-33).

    Efeito: a contagem da pergunta 5 do F2B-21. No cadastro, o F2A-16 contou Emp. Adm. Part. - Bancos 1, Intermediação Financeira 10, Emp. Adm. Part. - Intermediação Financeira 16, Crédito Imobiliário 6 e a holding dele 5 (companhias do cadastro, não só listadas).
  - **[BTG]** (F2A-39). Aceitar a fonte da B3 que o F2B-21 trouxer (ISIN e CNPJ no mesmo registro) como evidência da ligação na tabela de correções. Recusada: o BTG segue em exclusão provisória, e o F2A-39 vai para a 2C ou para a Fase 3. A ligação indireta (prefixo do ISIN e composição) já foi recusada em 13/10/2026.
- **Regra do golden.** A da 2A (opção (a), decidida em 5/10/2026) continua, com a taxa acrescentada ao harness no F2B-1. As alternativas recusadas na 2A (congelar o golden como registro da V1; regenerar só no fim da fase) valem igual aqui.
- **[CACHE].** O script de invalidação sai no F2B-5 (decisão de 5/10/2026). Itens desta fase mudam valores que a cascata grava no cache de fundamentos (F2B-8, F2B-10 a F2B-13, F2B-18, F2B-39 e F2A-39), então o passo 3 do [DECISÃO] final limpa a tabela inteira, com um comando e sem lista de tickers. Decisão de 5/10/2026 mantida na revisão de 18/10/2026; não é pergunta do marcador.
- **Escolhas de desenho que a aprovação confirma:**
  - **Taxa real pelo ponto de entrada da V1** (`config.py`, padrão do `get_selic_atual`), com semente no `tests/conftest.py` e o mesmo registro gravado em `dados['taxa_real']` para a proveniência. Alternativa: os motores lerem só `dados['taxa_real']`. Ela tira a rede do caminho do motor, mas sem a chave os métodos de taxa se abstêm em toda chamada fora da cascata: a seção C deixa de exercitar Gordon, Bazin e FII sem nenhum teste mudar, e a seção A muda mais. As duas viram macro por data no F3-1 e no F3-6.
  - **k calculado uma vez, fora dos métodos** (o `cost_of_equity_real` do PLANO), insumo do Gordon e da lente de bancos; o prêmio sai do `GordonParams`.
  - **Inflação como tipo** no `units.py`, com Fisher exato; nenhuma conversão por subtração.
  - **NTN-B sem contingência:** rede fora e cache além da defasagem viram abstenção (contrato de método). A Selic mantém a contingência dela até o F3-1 (E-6).
  - **Semente de teste da taxa** igual às contingências antigas do `config.py` (7% e 5,5%), como a semente da Selic é igual ao `SELIC_FALLBACK`: valor anterior, não escolhido pelo resultado.
  - **Lente de bancos em dois itens** (F2B-3 `feat:` e F2B-32 `fix:`), para o `feat:` não mudar saída; bancos ficam em abstenção entre o F2B-4 e o F2B-32.
  - **Abstenção por escopo e por liquidez no formato do F2A-29,** sem número no lugar; ordem das guardas: classe, liquidez, distressed.
  - **Gate de liquidez só com a chave `liquidez` presente** (precedente do F2A-29): chamadas fora da cascata (backtest, `auditoria.py`) não medem liquidez e não mudam.
  - **Correções de dados primeiro** (F2B-8 a F2B-42): o levantamento e a matriz do F2B-21 medem sobre os dados corrigidos.
  - **Dado novo antes do marcador** (F2B-28), sem consumidor; vértice e fonte do DY ficam com as fichas. O F2B-27 vem logo depois do marcador, porque o nome dos campos do Tesouro é da [TAXA] (auditoria externa da 2A, correção 2).
  - **Fichas escritas pelo loop como rascunho** e auditadas em modo FICHA, como a ficha por ação (D21, D30). A do Bazin não está na lista do ADR-0003 (taxa real, Gordon, FII e bancos), mas versão nova de método exige ficha (D21).
  - **Texto de dívida num `fix:` próprio** (F2B-45), antes da limpeza: o PLANO o punha no F2B-5, mas limpeza não muda golden (auditoria externa da 2A, correção 4).
- **Fora da fase, pendente:**
  - as notas do F2A-7 para o F2C-1 (o TTM com a regra 7.2 chega pelo F2B-37); JCP no DY (F-7, F2C-1); o motor que refaz LPA e VPA por P/L e P/VP em vez de ler os da CVM (2ª passada do Gemini; F2C-1);
  - decisões A e D (F2C-2); ROE e P/L no score e as penalidades em dobro do F2A-22 (F2C-3), com o insumo ausente que o motor converte em 0 e penaliza, e o NaN que escapa das penalidades (2ª passada do Gemini); o rótulo "QUALIDADE — AGUARDAR", inalcançável com a sigmoide atual (score ≤ 60 com upside ≤ 0), e os dois testes que o simulam com `math.exp` (F2C-3 e F2C-4);
  - vocabulário (F2C-4); Markowitz, que ainda lê a Selic (F2C-9); `auditoria.py` com Selic + 4% e média simples (F2C-8); `FII_MANUAL_FALLBACK` (F2C-10);
  - Selic sem proveniência e rede no import (E-6, F3-1): a semente da taxa real no `conftest.py` é o mesmo contorno;
  - `analisar(ticker, as_of)`, o `date.today()` dos motores e a taxa real na tela (F3-6); backtest real (F3-8);
  - pendências do diário da 2A sem destino, para a proposta da 2C decidir: conferência do LPA da unit pela soma ponderada dos divulgados (ressalva do Gemini ao F2A-5); textos dos motivos das reservas e a reserva na proveniência do `lpa` e do `vpa` (revisão do F2A-37); falha do Informe sem rastro em `riscos_dados` (F2A-11); primeira análise lenta pela liquidez síncrona (F2A-26); `CodInst` sem escape (F2A-9); versão de esquema do `indice.json` (sugestão do Gemini ao F2A-2); o prompt da IA mostra a classe do classificador sem dizer que é inferida (revisão do F2A-43); o caso inverso da sigla preferencial (DRE com "PNA" e FCA sem sigla; revisão do F2A-36);
  - testes fracos que a 2ª passada do Gemini apontou fora desta fase: asserts triviais em `tests/test_technical_engine.py` (ticket B1 do Jules, se aberto) e os mocks que testam o próprio mock em `tests/test_macro_context.py` (os da NTN-B saem no F2B-5; os do IPCA, no F3-1); o teste do Lynch com o esperado copiado da V1 (2C).
- **Riscos:**
  - **Tesouro sem resposta.** O prêmio não é fixado, e F2B-1, F2B-2 e F2B-32 ficam `[!]`: a fase para no marcador até a coleta.
  - **Números mudam de uma vez** (PLANO, seção 13): o k do Gordon cai de 20,75% para cerca de 12% real (dossiê, seção 2), o FII troca de benchmark e os bancos ganham lente. O antes → depois no diário de cada item é o controle.
  - **Contorno do E-6 cresce:** a semente da taxa real esconde a rede nos testes como a da Selic, até o F3-1.
  - **Golden.** Com as grades novas, pode passar de 1,2 MB; o diário registra o tamanho a cada item **[golden]**.
  - **Muitos testes mudam por decisão.** Todos estão listados nos itens; o `/review-diff` confere que nenhuma asserção foi enfraquecida.
  - **Série do FII.** O começo do Informe Mensal e do COTAHIST anual limita a janela da mediana do spread; o download do levantamento soma centenas de MB em `outputs/`.
  - **Fontes sem contrato publicado** (o serviço da B3, o arquivo do Tesouro) podem mudar de formato; o teste de contrato (D18) avisa.
  - **Resíduos do `app.py`** (travado): a tela segue com os rótulos da V1 e sem a taxa real; o relatório do F1-12 é onde a taxa aparece.
  - **Jules:** C-C na última janela; nenhum item toca `peers_engine.py`.
