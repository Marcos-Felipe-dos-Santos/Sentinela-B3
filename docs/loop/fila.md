# Fila do loop — Fase 1 (Fundação: tipos, contratos e extração)

> **Proposta, não ativa.** Escrita no F0-10 pelo `fable-architect`. Quem a coloca em `docs/loop/fila.md` é o Marcos, depois de aprovar.

Branch: `v2/fase-1` · Protocolo: `docs/loop/protocolo.md` · Diário: `docs/loop/diario.md`
Plano: `docs/PLANO.md` (seção 6, "Fase 1") · Decisões: `docs/adr/0001-refactor-v2.md` e `docs/adr/0002-loop-tempo-dados.md`
Auditoria: `docs/auditoria/2026-09-red-team.md` · Dossiê: `docs/decisoes/dossie-fase2.md` · Inventário: `docs/limpeza/inventario.md` · Jules: `docs/jules-backlog.md`

**Comportamento:** igual ao da V1, com duas exceções declaradas. Cada uma tem um item `fix:` próprio (xfail → XPASS): o F1-15 (mapa ticker → CD_CVM) e o F1-11 (`tecnico_negativo`). Nenhum outro item muda número, texto ou ordem na saída dos motores.

**IDs e ordem:** os itens F1-1 a F1-14 mantêm o significado da tabela do PLANO. O `CLAUDE.md` cita o F1-10, o PLANO cita o F1-11 e o F1-13, e o inventário cita o F1-13. Os itens novos são F1-15 a F1-19. A execução segue a ordem da lista, não a numérica:
1. as duas correções (só o F1-11 precisa vir antes do golden; os motores não leem o mapa CVM);
2. o golden, que vira o juiz;
3. os tipos e o contrato de método;
4. o contrato de import, antes da primeira extração;
5. as seis extrações;
6. o registro e a mutação;
7. o relatório;
8. a documentação;
9. a proposta da 2A;
10. a limpeza e o resumo.

**Intocáveis nesta fase:**
- `tests/test_financeiro_pre_refactor.py` (o gate). Depois do F1-16, também `tests/fixtures/golden_motores.jsonl`.
- `config.py` inteiro, por três motivos:
  - o `MacroContext` é a fonte única dos parâmetros da V1 nesta fase (o E-6 é o F3-1);
  - o `_normalizar_dy` é do F2A-4;
  - os comentários de `FIIS_CONHECIDOS` são do ticket C-E do Jules.
- `market_engine.py`, `brapi_provider.py` e `cvm_fii_map.py` (Fase 2A), `portfolio_engine.py` (F2C-9) e `app.py` (Fases 3 e 7).
- Os arquivos dos tickets do Jules com janela nesta fase: `cvm_provider.py`, `cvm_fii_provider.py`, `data_quality.py`, `peers_engine.py`, `README.md` e `.env.example`. Também os testes deles: `tests/test_cvm_provider.py`, `tests/test_cvm_fii_provider.py`, `tests/test_data_quality.py` e `tests/test_peers_engine.py`.
- Itens que podem mexer em cada arquivo restrito:
  - `valuation_engine.py`: F1-11, F1-3 a F1-6 e F1-13;
  - `fii_engine.py`: F1-7, F1-8 e F1-13 (só para tirar sobras da extração);
  - `cvm_ticker_map.py`: só o F1-15.
- Teste existente só muda onde o item manda: no F1-15, no F1-11 e nas correções automáticas do F1-13.

**Gate da fase (todo item):**
- `git diff --exit-code v2-fase-0 -- tests/test_financeiro_pre_refactor.py` sem diferença (`v2-fase-0` é a tag do merge da Fase 0);
- depois do F1-16, `git log --oneline -- tests/fixtures/golden_motores.jsonl` mostra um único commit;
- `python -m pytest -q` e `ruff check --select E9,F63,F7,F82 .` verdes.

**Gate de refactor (F1-3 a F1-8):** o gate da fase, e nenhum teste existente alterado: `git diff --cached --name-status -- tests/` só mostra `A`.

**Rito da extração (F1-3 a F1-8):**
- **Mover, não copiar.** A fórmula e as condições saem do motor e vão para `sentinela/methods/<método>.py`, versão `1.0.0`. O motor converte `dados` em `MethodInputs` uma única vez, monta os parâmetros a partir do `MacroContext` e delega. Uma `Abstention` corresponde exatamente ao "método não calculado" da V1.
- **Selic.** Continua lida por `valuation_engine.get_selic_atual()` e `fii_engine.get_selic_atual()`, que são o ponto de patch das seções A/B/C, de `tests/test_valuation_engine.py`, de `tests/test_fii_engine.py` e de `scripts/dossie_fase2.py`. Entra no método como `RateNominal`.
- **Mesma ordem de operações da V1.** O golden compara float com `==`.
  - Não mudam: a ordem e os rótulos de `metodos_usados` ("Graham", "Bazin", "Lynch", "Gordon", "Bazin FII") nem a ordem de `riscos`.
  - Valor não finito vira `None` no motor, antes de montar `MethodInputs`.
- **Fallbacks da V1** são reproduzidos e declarados em `assumptions`. Nenhum vira abstenção nesta fase.
- **Log.** Métodos não fazem log; o motor mantém as mensagens da V1, montadas a partir do motivo da abstenção.
- **Testes.** Cada método ganha testes novos (fórmula, cada motivo de abstenção, metadados), e o mutation do módulo vai para o diário. A meta de 80% fecha no F1-17.
- **Sobras.** O que ficar no motor de propósito vai para o diário e sai no F1-13.

**Paralelo do Jules (o loop não executa nenhum desses tickets nem toca nos arquivos deles):**
- B4.1 → B4.2 → B4.3, em `cvm_provider.py` e `cvm_fii_provider.py`. São sequenciais, e o B4.2 só abre com o critério do E-8 decidido.
- C-D, em `data_quality.py`.
- C-E, só nos comentários de `config.py`.
- B4.1 a B4.3 e C-D precisam estar mergeados antes de ativar a 2A. O C-E só tem janela nesta fase.
- B1, B2, B3, C-A, C-B e C-C podem correr em paralelo.

**Decisões:** as marcas `[D5]`, `[D9]` e `[D11]` indicam itens que dependem das propostas do ADR-0002. O efeito de cada recusa está na última seção.

**Privacidade:** o repositório é público. Nenhum dado da carteira do Marcos (posições, pesos, lista de ativos) entra em arquivo versionado — nem em fixture, nem no golden, nem no diário.
- Fixtures usam tickers genéricos (`TST3`, `TST11`) ou os dos mapas públicos do código.
- O relatório do F1-12 grava em `outputs/` e nunca lê a carteira.

Legenda: `[ ]` pendente · `[x]` feito · `[!]` bloqueado · `[DECISÃO]` o loop para aqui

## Itens

- [x] **F1-15** · fix · `fix: regenerate CVM ticker map from official registry`
  **Decidido pelo Marcos (pergunta 0 do dossiê, 2/10/2026).** O mapa de `cvm_ticker_map.py` passa a ser gerado do caminho oficial (FCA → CNPJ → cadastro da CVM), sem digitação à mão.

  **Geração (`scripts/gerar_mapa_cvm.py`):**
  - reaproveita `cd_oficial` de `scripts/dossie_fase2.py` por import, sem movê-lo nem alterá-lo;
  - lê o cache de 1/10 em `outputs/dossie_cache/` (`cad_cia_aberta.csv` e `fca_valor_mobiliario.csv`, este o FCA de 2026);
  - o FCA do ano anterior (2025) não está nesse cache: o script o baixa uma única vez para a mesma pasta (rede só de leitura, CVM) e registra a data no diário;
  - grava `tests/fixtures/cvm_codigos_oficiais.csv` só com `ticker`, `cnpj`, `cd_cvm` e `situacao`;
  - regenera o bloco `_MANUAL_MAP` de `cvm_ticker_map.py` a partir da fixture; rodar o script de novo não produz diff.

  **Regra por ticker do mapa atual (coluna `situacao`):**
  - `fca_2026`: código de negociação ativo no FCA de 2026 → CD_CVM oficial;
  - `fca_2025`: ausente em 2026 e ativo no FCA de 2025 → CD_CVM oficial pelo FCA de 2025;
  - `codigo_proprio`: ausente nos dois anos, mas o código do mapa é da própria empresa (a empresa do código já teve ticker com a mesma raiz de 4 letras no FCA, em qualquer data, a mesma regra da seção 0 do dossiê) → o código fica (é o caso do GOLL4);
  - `fora`: ausente nos dois anos e com código de outra empresa ou inexistente → sai do mapa, com `cd_cvm` vazio na fixture.

  Situação de negociação é filtro de universo e de liquidez (F2A-10, F3-5), não de mapa. O diário lista os tickers `fora`, com CSNA3 e AZUL4 destacados, e os `fca_2025`. Ticker novo depois de evento societário é decisão do F2A-1.

  **Cache de fundamentos (`scripts/invalidar_cache_cvm.py`):**
  - apaga de `fundamentals_cache` só os tickers passados na linha de comando, com SQL parametrizado;
  - sem `--aplicar`, só lista o que apagaria;
  - o loop **nunca** roda o script contra o banco local: o diário traz a linha de comando com os tickers cujo código mudou ou que saíram, e o Marcos roda no checkpoint;
  - teste próprio, com banco em `tmp_path`: apaga só os tickers pedidos e nada sem `--aplicar`.

  **Teste primeiro:** `tests/test_cvm_ticker_map.py::test_mapa_manual_bate_com_cadastro_oficial`, um único teste para o mapa inteiro, contra a fixture (sem rede): o mapa tem exatamente os tickers não `fora`, cada um com o `cd_cvm` da fixture. Não parametrizar: com `xfail_strict`, a PETR4, que já bate, viraria XPASS.

  **Testes que mudam:** `tests/test_cvm_ticker_map.py:12` e `:45` fixam 19348 (Itaú) como código da VALE3; passam a 4170, com justificativa no diário. Nenhum outro teste existente muda.

  **Cuidados:**
  - importar `scripts/dossie_fase2.py` executa o topo do módulo (pasta de cache, `config` com a chamada ao BCB, yfinance), mas não o `main()`; nenhum arquivo do dossiê é regravado;
  - o mapa é indexado pelo código, então nenhuma chave pode se repetir. Exemplo: o 22470, da Magazine Luiza, hoje está com JBSS3;
  - nenhum código fora da fixture é inventado.

  **Fora do item (para o F2A-1, registrado no diário para o F1-19 levar à proposta da 2A):**
  - `_seed_manual_map` (`INSERT OR IGNORE`) e o resto da classe `CVMTickerMap`, que só os testes instanciam;
  - `cvm_fii_map.py`: a conferência pela regra do ISIN e os 3 FIIs ausentes do Informe Mensal.

  **Aceite:**
  - `test_mapa_manual_bate_com_cadastro_oficial` passa por xfail estrito → XPASS → marca retirada;
  - `python scripts/gerar_mapa_cvm.py` rodado de novo não altera `cvm_ticker_map.py` nem a fixture;
  - o diário lista os tickers cujos fundamentos CVM mudam (o único leitor do mapa em produção é `market_engine.py:481`), os que saíram e a linha de comando do `invalidar_cache_cvm.py`;
  - gate da fase.

- [x] **F1-11** · fix · `fix: stop valuation engine from reading technical signal`
  `valuation_engine.py:196-199` lê `tecnico_negativo`, mas nenhum código de produção escreve essa chave. Só `tests/test_valuation_engine.py:368` a usa, e o cache de fundamentos não a restaura (só aceita `FUNDAMENTAL_KEYS`). No app, nada muda.

  No contrato de `processar`, porém, a chave tem efeito: com ela, `riscos` ganha "Técnico negativo", a confiança cai 10 e, por esses dois caminhos, a classificação pode mudar (linhas 201-213). Por isso o item é `fix`, fica fora da extração e vem antes do golden.

  No teste existente, a chave da linha 368 sai e o comentário da linha 373 deixa de citá-la; a asserção não muda. O item não depende da D11: é caminho morto (armadilha 12).

  **Aceite:**
  - `tests/test_valuation_engine.py::test_sinal_tecnico_nao_altera_resultado` passa por xfail estrito → XPASS;
  - `git grep -n tecnico_negativo -- '*.py'` só encontra o teste novo;
  - gate da fase.

- [x] **F1-16** · test · `test: pin valuation engine outputs on a boundary grid`
  **Por quê.** As seções A, B e C checam poucas propriedades. Não pegam a maioria das fronteiras (`>` × `>=`) nem a ordem de `riscos`: com a suíte inteira, o mutation do `valuation_engine` foi de 60,2% no F0-3.

  **O que o item faz.** Grava as saídas atuais de `ValuationEngine().processar` e `FIIEngine().analisar` em `tests/fixtures/golden_motores.jsonl`: uma linha por caso, com entrada e saída, até ~1 MB. O teste compara por igualdade exata: o dict inteiro, incluindo a ordem de `riscos` e o texto de `metodos_usados`. Como `nan == nan` é falso depois de ler o JSONL, o item traz um comparador próprio (recursivo, com NaN igual a NaN e `==` nos demais floats); `pytest.approx` não é permitido.

  **Grade:**
  - cada constante do `MacroContext` lida pelos motores, com valor abaixo, no limite e acima, nos perfis renda e crescimento;
  - `pl_confiavel` e `erro_scraper`;
  - ticker distressed;
  - DY percentual e DY suspeito;
  - `divida_liq_ebitda` como número, como texto pt-BR e malformado;
  - NaN;
  - Selic abaixo e acima de 5%, e uma baixa o bastante para k ≤ g;
  - FII com provedor CVM falso: com e sem `valor_cota` e `vacancia_fisica`, e um provedor que levanta exceção;
  - vacância manual;
  - P/VP ausente.

  **Como rodar a grade:**
  - A Selic entra por patch em `valuation_engine.get_selic_atual` e `fii_engine.get_selic_atual`.
  - Tabelas e mapas entram por `monkeypatch`, sempre com tickers genéricos.
  - O gerador reusa o harness do teste e a semente do `conftest.py`, sem rede, e roda uma única vez na fase. O diário registra como acioná-lo.

  **Aceite:**
  - `tests/test_equivalencia_motores.py::test_acoes_iguais_ao_golden` e `::test_fii_iguais_ao_golden`;
  - mutation de `valuation_engine*` e de `fii_engine*` ≥ 80%, descontados os mutantes que só alteram mensagem de log (listados no diário);
  - a rodada limpa do mutmut encontra o fixture. Se não encontrar, acrescentar o caminho em `also_copy` no `[tool.mutmut]`.

- [ ] **F1-1** · feat · `feat: add unit types for money, ratios, rates and share counts`
  Cria `sentinela/domain/units.py`. É aditivo, sem consumidor em produção.
  - Tipos: `BRL`, `Ratio`, `Percent`, `RateNominal`, `RateReal` e `QuantidadeAcoes`, esta com `Escala` (unidade ou mil, sempre informada — armadilha 10).
  - Os tipos são imutáveis, e a construção rejeita NaN e infinito.
  - As conversões são explícitas: `Percent` ↔ `Ratio` e quantidade em unidades.
  - Soma e subtração só valem entre o mesmo tipo. Misturar `RateReal` com `RateNominal` levanta `TypeError` (armadilha 1).
  - A conversão real ↔ nominal fica para o F2B-1, junto com a decisão da inflação.

  **Aceite:**
  - `tests/test_units.py::test_taxa_real_e_nominal_nao_se_misturam`, `::test_percentual_vira_razao`, `::test_quantidade_em_milhares_vira_unidades`, `::test_valor_nao_finito_e_rejeitado` e `::test_tipos_sao_imutaveis`;
  - mutation ≥ 80% em `sentinela.domain.units*`;
  - gate da fase.

- [ ] **F1-2** · feat · `feat: add valuation method contract with frozen inputs` · **[D5]**
  Cria `sentinela/methods/__init__.py` e `base.py`, e acrescenta `Regime` (`REAL`, `NOMINAL`, `SEM_TAXA`) a `sentinela/domain/enums.py`.
  - **`MethodInputs`** é uma dataclass congelada, com `as_of: date` obrigatório [D5]. Os campos são tipados pelo `units.py`: preço, LPA, VPA, P/L, P/VP, DY, ROE, Selic (`RateNominal`), vacância, perfil e as flags de confiabilidade da V1.
  - **Resultado:** ou `MethodResult` (método, versão, valor com unidade, intermediários nomeados, alertas), ou `Abstention` (método, versão, motivo).
  - **Metadados:** todo `ValuationMethod` declara `nome`, `version`, `regime`, `requires`, `assumptions` e `applies_to`. Se falta um insumo exigido, o método devolve `Abstention`, nunca um número conservador.
  - **Parâmetros** entram como argumento explícito: uma dataclass congelada por método, sem valor padrão.
    - Nesta fase, o motor V1 monta os parâmetros a partir do `MacroContext`, que continua sendo a fonte única dos valores.
    - Métodos nunca importam `config`, que faz rede e configura log no import (armadilha 8).
    - Os parâmetros mudam de casa na primeira versão nova de cada método, já na Fase 2, junto com as limpezas do F2B-5 e do F2C-10.

  **Aceite:**
  - `tests/test_methods_contrato.py::test_inputs_sao_congelados`, `::test_inputs_exigem_as_of`, `::test_insumo_ausente_vira_abstencao` e `::test_regime_bate_com_o_tipo_da_taxa`;
  - mutation ≥ 80% em `sentinela.methods.base*`;
  - gate da fase.

- [ ] **F1-10** · test · `test: enforce purity contract on valuation methods` · **[D11]**
  Entra antes da primeira extração, para que cada método já nasça verificado. Cria `tests/test_contratos_import.py`, com duas verificações:
  1. **Pela AST** de `sentinela/methods/**/*.py` e dos módulos de `sentinela/domain/` que eles importam:
     - não há import de `sentinela.news`, `sentinela.data`, `sentinela.services`, `sentinela.repositories`, `sentinela.reports`, `technical_engine`, `config`, `market_engine`, `database`, provedores e mapas da raiz, `ai_core`, `requests`, `urllib`, `http`, `socket`, `sqlite3`, `yfinance`, `logging`, `os`, `pathlib` ou `time`;
     - não há chamada a `now`, `today`, `utcnow` ou `open`.
  2. **Por import isolado:** cada módulo é importado num subprocesso com `socket` bloqueado, e nenhum desses módulos aparece em `sys.modules`. Isso pega import transitivo.

  Roda no `pytest` do CI, sem dependência nova.

  **Aceite:**
  - `::test_metodos_nao_importam_modulos_proibidos`, `::test_metodos_nao_leem_relogio_nem_arquivo` e `::test_import_isolado_nao_carrega_modulos_proibidos` verdes;
  - um módulo temporário que importa `config` derruba o teste. Isso é feito uma vez, não é commitado e fica registrado no diário;
  - gate da fase.

- [ ] **F1-3** · refactor · `refactor: extract Graham method`
  Move `valuation_engine.py:83-95` para `sentinela/methods/graham.py`, com regime `SEM_TAXA`:
  - piso de P/L 7 (linha 87);
  - limite de P/VP pelo perfil (linha 85);
  - `pl_confiavel` falso vira `Abstention`.

  O perfil (linhas 71-79) continua calculado no motor e entra em `MethodInputs`. Este item cria no motor o passo que monta `MethodInputs` e devolve o resultado de cada método. `processar` passa a usar esse passo, e os itens seguintes também.

  **Aceite:** gate de refactor; `tests/test_methods_graham.py`; mutation de `sentinela.methods.graham*` no diário.

- [ ] **F1-4** · refactor · `refactor: extract Bazin method`
  Move `valuation_engine.py:97-107` para `bazin.py`, com regime `NOMINAL`:
  - DY mínimo de 5% (seção A);
  - só no perfil renda e com DY confiável;
  - taxa = máx(Selic, 5%).

  O alerta de DY acima de 15% sai como alerta do resultado. O motor mantém "DY muito alto (possível armadilha)" e a confiança −10 no mesmo ponto de `riscos`.

  **Aceite:** gate de refactor; `tests/test_methods_bazin.py`; mutation de `sentinela.methods.bazin*` no diário.

- [ ] **F1-5** · refactor · `refactor: extract Lynch method`
  Move `valuation_engine.py:109-118` para `lynch.py`, com regime `NOMINAL` (g = ROE × retenção é nominal):
  - só no perfil crescimento;
  - exige P/L, LPA e ROE positivos e DY confiável;
  - tetos: payout 0,95, g de 25% e P/L justo 35;
  - multiplicador 1,5.

  **Aceite:** gate de refactor; `tests/test_methods_lynch.py`; mutation de `sentinela.methods.lynch*` no diário.

- [ ] **F1-6** · refactor · `refactor: extract Gordon method`
  Move `valuation_engine.py:120-130` para `gordon.py`, com regime `NOMINAL`:
  - exige `dy_confiavel`, DY acima de 4% e ROE acima de 10%;
  - k = Selic + 7%;
  - g = ROE × retenção, com teto de 8%;
  - k ≤ g vira `Abstention`.

  Com LPA ≤ 0, o payout é 0,5 (linha 123). Esse fallback da V1 fica e é declarado em `assumptions`; só vira abstenção na Fase 2, com versão nova. Não há taxa real aqui: a seção B (F-4) fixa o regime nominal, e a troca é o F2B-1 (armadilha 1).

  **Aceite:** gate de refactor; `tests/test_methods_gordon.py`; mutation de `sentinela.methods.gordon*` no diário.

- [ ] **F1-7** · refactor · `refactor: extract FII yield method`
  Move `fii_engine.py:96-107` para `fii_yield.py`, com regime `NOMINAL`:
  - preço justo = preço × DY efetivo ÷ (Selic × 0,85);
  - DY efetivo = DY × (1 − vacância), quando há vacância;
  - DY efetivo e Selic líquida voltam como intermediários para o score, que fica no motor.

  Como no F1-3, o motor de FII ganha o passo que monta `MethodInputs`. O teste de DY e a resolução da vacância (CVM > `VACANCIA_CONHECIDA`) ficam no motor, na mesma ordem: o provedor CVM só é chamado depois do teste de DY (linhas 62-73). `VACANCIA_CONHECIDA` continua em `fii_engine.py`, porque `tests/test_fii_engine.py:2` e `:56` a importam e alteram; ela sai no F2A-13.

  **Aceite:** gate de refactor; `tests/test_methods_fii_yield.py`; mutation de `sentinela.methods.fii_yield*` no diário.

- [ ] **F1-8** · refactor · `refactor: extract FII price-to-book lens`
  Na V1, o patrimônio não forma valor justo: o P/VP só pesa no score (`fii_engine.py:116-121`), e a seção B (F-9) fixa isso. Por isso, o `fii_nav.py` 1.0.0 é a lente de P/VP, com regime `SEM_TAXA`.
  - Devolve o P/VP e a faixa: prêmio alto (acima de 1,15), prêmio moderado (acima de 1,05), desconto (abaixo de 0,85) ou neutra.
  - O motor converte a faixa em pontos: −15, −7, +10 e 0.
  - A resolução do P/VP (`valor_cota` da CVM > `dados['pvp']` > 1,0, linhas 76-80) fica no motor até o F2A-11.
  - Valor justo ancorado no patrimônio depende da pergunta 3 do dossiê (Fase 2B) e não é antecipado aqui.

  **Aceite:** gate de refactor; `tests/test_methods_fii_nav.py`; mutation de `sentinela.methods.fii_nav*` no diário.

- [ ] **F1-9** · feat · `feat: add method registry pinned to V1 behavior`
  Cria `sentinela/methods/registry.py`, com o catálogo dos seis métodos (nome, versão, regime, `requires`, `assumptions`, `applies_to`) e o changelog. A entrada 1.0.0 diz: "comportamento da V1, extraído na Fase 1, sem mudança de número".
  - `applies_to` é declarado, mas não aplicado. Descreve o roteamento da V1: ações para `STOCK` e `UNIT`, FII para `FII`. O classificador atual nunca devolve `ETF` nem `BDR`. Aplicar e estreitar é o F2B-4.
  - Um teste fixa os valores dos parâmetros da 1.0.0 lidos do `MacroContext`: mudar uma constante sem criar versão nova quebra a suíte.

  **Aceite:**
  - `tests/test_registry.py::test_registro_tem_os_seis_metodos`, `::test_todo_modulo_de_metodo_esta_registrado`, `::test_regime_coerente_com_a_taxa`, `::test_parametros_da_1_0_0_fixados` e `::test_changelog_tem_a_1_0_0`;
  - gate da fase.

- [ ] **F1-17** · test · `test: raise mutation score of valuation methods to 80%`
  Fecha o gate de mutação da fase:
  - roda a mutação no pacote;
  - escreve testes para os sobreviventes não equivalentes (a especificação da 1.0.0 é o comportamento da V1, fixado pelo golden);
  - lista no diário os mutantes equivalentes, com o motivo.

  A meta não baixa, e teste que asserta sem verificar não entra.

  **Aceite:**
  - `python -m mutmut run "sentinela.methods*"` e `python -m mutmut export-cicd-stats` dão mortos ÷ (mortos + sobreviventes) ≥ 80% no pacote, com o número de cada módulo no diário;
  - gate da fase.

- [ ] **F1-12** · feat · `feat: add static traceability report v0` · **[D9]**
  `python -m sentinela.reports.rastreabilidade <TICKER>` grava `outputs/rastreabilidade/<TICKER>-<data>.html`, fora do git.

  **Fonte dos dados.** Lê a cascata e os motores da V1 como estão: a mesma sequência do `app.py`, sem IA e sem gravar análise. A cascata ainda grava o cache de fundamentos, como no app. O detalhe por método vem do passo interno criado no F1-3 e no F1-7, sem cálculo novo.

  **O relatório mostra:**
  - cada insumo, com valor, unidade e a proveniência que a cascata já registra (`field_provenance` cobre cinco campos; os demais herdam `fonte_fundamentos`);
  - a Selic usada;
  - cada método, com versão, regime, premissas, parâmetros e resultado ou abstenção com motivo;
  - a mediana e o score.

  **Limites e avisos:**
  - declara os limites conhecidos: Selic sem proveniência (E-6) e LPA/VPA sem reconciliação (E-1);
  - traz o aviso de revisão do F0-9;
  - omite o rótulo de classificação da V1;
  - se o F1-15 não estiver na fila, os campos de fonte CVM levam o aviso "mapa manual não conferido".

  Usa Jinja2 com autoescape, declarado no `requirements.txt`.

  **Aceite:**
  - `tests/test_rastreabilidade.py::test_relatorio_mostra_cada_metodo_com_versao`, `::test_relatorio_mostra_motivo_da_abstencao`, `::test_relatorio_escapa_html` e `::test_relatorio_sem_vocabulario_proibido` ("recomendação", "compra", "venda", "alocação sugerida"), com dados de fixture e sem rede;
  - `deptry .` sem achado novo;
  - gate da fase.

- [ ] **F1-18** · docs · `docs: sync agent instructions with extracted methods`
  Valida contra o código e corrige três arquivos: `CLAUDE.md`, `AGENTS.md` (menos a seção "Fase atual", que é do Marcos) e a tabela da Fase 1 do `docs/PLANO.md` (IDs finais, e a lente de P/VP no lugar do "FII NAV").

  **No `CLAUDE.md`:**
  - contagens da tabela "Arquitetura real" e da suíte;
  - o parágrafo da camada `sentinela/`: os motores V1 agora chamam `sentinela/methods/`, enquanto `services/` e `repositories/` seguem desconectados;
  - a faixa do `app.py` que o `AnalysisService` duplica;
  - a armadilha 1 passa a apontar para `sentinela/methods/gordon.py`;
  - as armadilhas 4 e 8 e as regras econômicas citam as linhas atuais de `config.py`;
  - a armadilha 12 aparece como resolvida;
  - `SEM_TAXA` entra no contrato de método;
  - em "Testes", o golden aparece ao lado das seções A, B e C;
  - o estado das Fases 0 e 1.

  **No `AGENTS.md`:** a contagem da suíte, e o golden entre os arquivos proibidos.

  Se algo divergir, corrige o documento, nunca o código.

  **Aceite:**
  - diff só nesses três arquivos;
  - cada linha citada conferida com `grep -n` e listada no diário;
  - `CLAUDE.md` e `AGENTS.md` sem contradição entre si.

- [ ] **F1-19** · levantamento · `docs: propose phase 2A queue`
  O `fable-architect` propõe a fila da Fase 2A em `docs/loop/fila-fase2a-proposta.md`, a partir da seção "Fase 2A" do PLANO, do dossiê, do inventário e das decisões do checkpoint da Fase 0. A proposta precisa ler `docs/decisoes/checkpoint-fase0.md` e seguir o que ele já decidiu. A proposta traz:
  - um item por commit, com tipo, escopo e aceite;
  - teste xfail antes de cada correção;
  - marcação do que depende de pergunta do dossiê (1, 5, 6 e 7) ou de limiar ainda aberto (divergência de ações, liquidez), com o efeito de cada resposta;
  - os merges do Jules (B4.1 a B4.3 e C-D) como condição de ativação;
  - limpeza (F2A-13) como penúltimo item e resumo como último.

  Nada é implementado.

  **Aceite:** arquivo no formato desta fila; todo item com aceite verificável; nenhuma decisão do Marcos tomada pelo texto.

- [ ] **F1-13** · limpeza · `chore: clean up phase 1 residue`
  Faz só o que segue, conforme o inventário (seções 3.1 e 3.3) e o PLANO (seção 11):
  - **Sobras de método** no `valuation_engine.py` e no `fii_engine.py` que estejam registradas no diário das extrações, e imports que perderam uso.
  - **Correções automáticas seguras** da seção 3.1 do inventário (UP045, UP006, UP037, I001, F541, FURB188, PYI041), nestes arquivos:
    - `sentinela/`, `valuation_engine.py`, `technical_engine.py`, `database.py`, `ai_core.py`, `fundamentus_scraper.py` e `auditar_recomendacoes.py`;
    - `auditoria.py` e `limpar_banco.py`, mas sem I001: com cobertura 0%, uma mudança na ordem de import com efeito colateral não seria pega;
    - `backtesting/`, mas sem RUF046, que é do F3-8;
    - `scripts/` e `tests/`, fora os intocáveis.

    Os arquivos travados na 2A, inclusive `fii_engine.py` e `cvm_ticker_map.py`, ficam para o F2A-13.
  - **`[tool.ruff]` no `pyproject.toml`:** reproduz o conjunto efetivo de regras que gerou o inventário (`ruff check --show-settings`), com `target-version = "py313"`, excluindo `venv`, `mutants`, `outputs` e `data`, e sem regra nova.
  - **CI:** passa a instalar `requirements-dev.txt` e ganha passos em modo relatório, com `continue-on-error`: `ruff check . --statistics --exit-zero`, `python -m vulture . vulture_whitelist.py --min-confidence 80 --exclude venv,mutants,outputs,data` e `deptry .`. O gate bloqueante continua o do protocolo: `ruff check --select E9,F63,F7,F82 .` e pytest.
  - **`scripts/dossie_fase2.py`:** só as correções automáticas. B023, PLR0124 (`x != x` é teste de NaN) e os campos sem leitor de `mercado()` ficam no inventário, porque o script só se valida com rede.
  - **Itens *investigar*** decididos no checkpoint da Fase 0 (`docs/decisoes/checkpoint-fase0.md`, seção 3): remove `reportlab` e `openpyxl` do `requirements.txt` e `docs/cleanup_report.md` com `git rm`. `buscar_noticias` e `get_quote` ficam para o F2A-13.
  - **`vulture_whitelist.py`:** recebe só falsos positivos novos, cada um com o motivo.

  Depois, roda de novo o vulture, o `ruff check . --statistics` e o deptry, e atualiza `docs/limpeza/inventario.md` (antes → depois).

  **Aceite:**
  - gate da fase;
  - testes alterados só por correção automática de estilo, sem asserção mudada (conferido no diff);
  - `ruff check sentinela/methods sentinela/domain/units.py` sem achados;
  - workflow válido;
  - referências de linha do `CLAUDE.md` e do `AGENTS.md` para os arquivos tocados conferidas;
  - inventário atualizado.

- [ ] **F1-14** · docs · `docs: add phase 1 summary and archive loop files`
  Nesta ordem:
  1. escrever `docs/loop/pr-fase-1.md` a partir do diário, com:
     - itens e commits;
     - testes antes → depois;
     - mutation por módulo, da linha de base do F0-3 ao final;
     - as duas mudanças de comportamento (F1-15 e F1-11), com o efeito medido;
     - decisões pendentes;
     - resíduos que ficaram para o Marcos;
     - o que revisar primeiro;
  2. registrar este item no diário e marcá-lo `[x]`;
  3. mover com `git mv` os arquivos `fila.md`, `diario.md` e `pr-fase-1.md` para `docs/loop/historico/fase-1/`;
  4. criar um `docs/loop/fila.md` novo contendo só:
     `[DECISÃO] Fase 1 encerrada. Histórico em docs/loop/historico/fase-1/. Próxima fila aguardando aprovação: docs/loop/fila-fase2a-proposta.md.`
  5. commitar e rodar `cat docs/loop/fila.md`.

- [DECISÃO] **Fim da Fase 1.** O Marcos:
  1. revisa as duas mudanças de comportamento da fase: o F1-15 (mapa) e o F1-11;
  2. confere a grade do golden (F1-16) e a mutação, da linha de base ao valor final;
  3. gera um relatório real com o F1-12 e confere a proveniência (sai em `outputs/`, fora do git);
  4. lê a proposta da 2A (F1-19) e responde às perguntas do dossiê que ela marcar;
  5. confirma no GitHub que B4.1, B4.2, B4.3 e C-D do Jules estão na `main`;
  6. decide o destino do golden a partir da 2A;
  7. faz o push do branch `v2/fase-1`, com PR da fase se quiser (usando `docs/loop/historico/fase-1/pr-fase-1.md` como corpo);
  8. depois do merge, marca a tag `v2-fase-1`, apaga o branch e atualiza a "Fase atual" do `AGENTS.md`.

## Riscos e decisões do Marcos

- **ADR-0002.** O que muda se cada proposta for recusada:
  - **D5 recusada:** o F1-2 sai sem `as_of` (nem como campo opcional) e sem `test_inputs_exigem_as_of`, e o F1-18 ajusta o `CLAUDE.md`. O resto da fase não muda.
  - **D9 recusada:** o F1-12 sai. Nada na fase depende dele, mas some a única entrega visível (PLANO, seção 13).
  - **D11 recusada:** o F1-10 fica só com o contrato do ADR-0001 (sem `sentinela/news`) e com a regra dura do protocolo (sem rede, banco e relógio). `technical_engine`, `sentinela/data` e provedores deixam de ser barrados no CI, e o F1-18 ajusta o contrato de isolamento do `CLAUDE.md`. O F1-11 não depende da D11.
- **Pergunta 0 do dossiê (F1-15).** Respondida em 2/10/2026: a correção está autorizada e as regras estão no próprio item (FCA de dois anos, GOLL4 fica, cache invalidado pelo Marcos no checkpoint).
- **Mistura no PR da fase.** A regra "refactor e mudança de comportamento nunca juntos" vale por commit (PLANO e `CLAUDE.md`). O ADR-0001 falava em PR. Se o Marcos preferir PR sem mistura, o F1-15 e o F1-11 vão num PR próprio, antes do PR da fase.
- **Jules.**
  - B4.1 → B4.2 → B4.3 e C-D precisam estar mergeados antes de ativar a 2A.
  - O B4.2 só abre com o critério do E-8 (`VERSAO` × `DT_REFER`). Convém decidir no começo da fase, para não atrasar a 2A.
  - O C-E só tem janela nesta fase. Ele cita `config.py:41-53`, de antes do F0-8; hoje o bloco está em 39-52.
  - Na ativação, atualizar a "Fase atual" do `AGENTS.md` e somar à trava da Fase 1: `cvm_ticker_map.py`, `tests/test_cvm_ticker_map.py`, `tests/fixtures/` e `sentinela/reports/`.
- **F0-4 (scraper).** Se a decisão for declarar o `cloudscraper`, entra um `chore` próprio antes do F1-13, só no `requirements.txt`. Se for remover o scraper, isso muda a cascata e vai para a 2A.
- **Golden depois da fase.** Proposta: a partir da 2A, cada correção que muda saída regenera só as linhas afetadas do golden, no mesmo commit, e o diff do golden vira a evidência do escopo da mudança. Decidir ao aprovar a 2A.
- **Ruff bloqueante em `sentinela/methods/`.** Fica em modo relatório nesta fase. Para promovê-lo, é preciso mudar junto o passo 4 do protocolo e a skill `/safe-commit` (sugestão: no início da 2A).
- **Fora da Fase 1:**
  - qualquer número novo de valuation: taxa real, k e g, piso de P/L do Graham, taxa mínima do Bazin (Fases 2B e 2C);
  - o normalizador único de DY e o xfail do DY acima de 30% (F2A-4);
  - aplicar `applies_to` e a lente de bancos (F2B-3 e F2B-4);
  - valor justo do FII pelo patrimônio (pergunta 3, Fase 2B);
  - injeção do `CVMFIIProvider` e P/VP ausente como abstenção (F2A-11);
  - rede no import do `config` (E-6, F3-1);
  - `AnalysisService` conectado (F3-6);
  - troca do vocabulário da V1 (F2C-4);
  - duplicatas do `auditoria.py` (F2C-8);
  - o `AttributeError` do `app.py` quando `otimizar` devolve `None`, apontado na revisão do F0-9 (some com o F2C-9).
