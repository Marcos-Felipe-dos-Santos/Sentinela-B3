> Cópia do relatório `auditoria-fase-3-claude-4-relatorio.md` (Downloads do Marcos), checkpoint da 3-a, 11/11/2026, pelo passo 6 do `/goal`. Única mudança: caminhos locais absolutos trocados pelo caminho relativo à raiz ou por `~`.

# Auditoria externa: Fase 3 (3-a), commits marcados `Executor: codex`

**Modo:** FASE, restrito por autoria (decisão 23). Branch `v2/fase-3`, intervalo `da0a78c..cf76415`, HEAD `cf76415`. Auditei só seis commits: `9ae3006`, `917994e`, `33acf20`, `c57e34b`, `a8265d4` e `89fcaa6`. O `89fcaa6` traz os dois executores e foi auditado inteiro. Usei só Read, Grep e Glob sobre a cópia e o `evidencias.txt`. A suíte e o mutmut não rodaram.

O ruff (`E9,F63,F7,F82`) passa, conforme `evidencias.txt:4888-4889`.

---

## 9ae3006 · F3-2d · feat: resultados imutáveis

- **ressalva**: o aceite "teste vermelho antes" não foi cumprido. O próprio diário (`diario.md`, F3-2d, "desvio cronológico") diz que o teste por remoção do módulo só prova dependência. Para fechar: ratificação explícita do Marcos.
- **ressalva**: a mutação deu 189/250 = 75,6% bruto, abaixo dos 80% de `AGENTS.md:130`. Os 81,12% saem de 17 "equivalentes de caixa SQL" que o próprio executor declarou, listados em `outputs/` (não versionado). Para fechar: o Marcos aceita ou recusa a exclusão (ver Perguntas).
- **ressalva**: a chave `as_of` é o texto ISO do instante (`resultados.py:82-89`). O mesmo instante com fusos diferentes (`…T18:00+00:00` × `…T15:00-03:00`), ou `date` contra `datetime` do mesmo dia, vira chaves distintas. Isso permite dois `original` para a mesma referência e contorna o índice `idx_resultados_analise_original` (`002_resultados_analise.sql:22-23`). Para fechar: normalizar `as_of` antes de gravar e testar dois offsets do mesmo instante. Depende da Pergunta 2.
- **sugestão**: o hash não cobre a proveniência (`resultados.py:102-105`, DD-12). Duas gravações com o mesmo resultado e fontes diferentes têm o mesmo hash. Vale registrar isso como limite na DD-12.
- Os gatilhos conferem. UPDATE, DELETE, REPLACE por id e por execução, segundo `original` e `recalculo` sem original são todos recusados por `BEFORE INSERT`, antes do REPLACE resolver conflito (`002…sql:26-67`). Os 30 casos do diário (27 + 3) batem com `test_store_resultados.py`.

## 917994e · F3-6a · feat: AnalysisService.analisar(ticker, as_of)

- **ressalva, bug proposto BUG-3-15**: a proveniência gravada sai sem a data do preço. `_gravar_resultados` lê `raw["data_preco"]` (`analyze_asset.py:137-140`), mas nenhum produtor escreve `data_preco`. O grep em `*.py` só acha leitores: `apresentacao.py:61`, `app.py:105` e `rastreabilidade.py:692`. `tests/test_apresentacao_separada.py:52` ainda afirma que o campo é `None`. O teste `test_original_e_recalculo_preservam_resultado_e_proveniencia` (`test_analysis_service_as_of.py:85`) confere `"2026-11-09"`, que só existe no mock. O teste prova o mock, não a cascata.
  - O teste de regressão `tests/regressao/test_bug_3_15_resultado_sem_data_do_preco.py` deve afirmar o seguinte. Na cascata real, com o yfinance simulado e histórico terminando em D-1, o registro em `resultados_analise` traz `proveniencia["data_preco"]` igual à data ISO do último fechamento usado. Ou então traz um motivo explícito de ausência, nunca `None` silencioso.
- **ressalva (não verificado)**: a gravação no store roda depois do cálculo, com `json.dumps(allow_nan=False)` e sem `default` (`resultados.py:92-93`). Um `NaN`, `date` ou tipo numpy numa lente ou num bloco de `proveniencia` derruba `analisar` depois da análise pronta. O legado usa `default=str` (`database.py:139,176`), sinal de que `dados` tem tipos não JSON. Para fechar: um teste com a cascata real (fixtures oficiais de FII e banco) gravando sem exceção, mais a decisão da Pergunta 7.
- **sugestão**: com `as_of` passado, a recusa grava um `original` do método técnico `analise` (`analyze_asset.py:146-162`). Convém registrar que a recusa vira registro permanente.
- Conferências que passaram:
  - A guarda de data recusa passado e futuro antes de qualquer fonte. A fronteira UTC/São Paulo está testada.
  - O golden tem 2291 casos (contei as linhas do `.jsonl`), o mesmo número do diário.
  - Regressão BUG-3-11: sem marca, e a asserção depende da assinatura (TypeError). Confere.

## 33acf20 · F3-6b · refactor: app chama o serviço

- **ressalva (checklist 7)**: o commit `refactor:` muda efeitos colaterais.
  - O app deixa de gravar na tabela `analises`. A antiga linha `db.salvar_analise` saiu do caminho executado (`app.py:282` agora está só em `_orquestrar_analise_legada`, sem chamador), e o teste novo afirma `COUNT(*) FROM analises == 0` (`test_app_analysis_service.py:283`).
  - O app passa a gravar em `resultados_analise`.
  - Ganha um modo de falha novo: a exceção na gravação, descrita no item anterior.
  - Os pares passam a ser consultados mesmo quando o motor devolve `None`: `analyze_asset.py:226-230` roda antes do teste da linha 232, e o legado parava antes.
  - Para fechar: registrar a troca de persistência como mudança de comportamento, num item próprio ou na ratificação (Pergunta 4).
- A tela não mudou: há hash da renderização e comparação AppTest em 5 cenários. O relógio é lido só na borda (`app.py`, `datetime.now(UTC)`). Nenhum teste existente foi alterado. Confere.

## c57e34b · F3-6c · feat: as_of até a cascata e os motores

- **ressalva**: o caminho de produção da Selic do FII mudou e a suíte não o executa.
  - Antes, `get_selic_atual()` fazia `ultimos/1`, com timeout de 5 s e cache de 24 h.
  - Agora, `MacroContext(as_of=dia).selic` (`fii_engine.py:188-190`) baixa a série completa do SGS 432 em 3 janelas (1999 até hoje, `macro_por_data.py:20,40-48`), cada uma com timeout de 60 s (`providers/macro.py:211`).
  - A fixture `autouse` nova em `tests/conftest.py:125-137` troca `fii_engine.MacroContext` em todos os testes por `MacroContext(selic=get_selic_atual(), …)`. Os 288 casos FII do golden (conferido por contagem) passam pela semente, não pela produção.
  - Por isso o aceite "com `as_of` = hoje, o comportamento é idêntico" não está demonstrado no caminho real.
  - Para fechar: um teste com `MacroProvider` sobre as fixtures SGS e `as_of` = hoje, mostrando valor igual a `ultimos/1` e o fallback de 14,75% na falha.
- **ressalva**: `tests/conftest.py` é infraestrutura de todos os testes. O aceite diz "nenhum teste existente muda", e a fixture `autouse` muda o objeto testado em toda a suíte. Está registrado na DD-19, mas é desvio do aceite.
- **ressalva (não verificado)**: com `as_of` passado, `_buscar_taxa_real` ainda usa `datetime.now` (`market_engine.py:830-832`), e `ipca_serie` filtra a publicação pelo dia da coleta (`market_engine.py:814-816`, `providers/macro.py:308`). Isso só não vaza hoje porque o serviço recusa `as_of` passado. A DD-18 afirma que o consumidor se abstém; não achei o teste disso para `taxa_real`. Para fechar: um teste com `as_of` passado e `taxa_real.as_of` posterior, esperando abstenção do Gordon.
- O inventário de 34 leituras de relógio está no diário. Não conferi contra o `284165f` (sem git).

## a8265d4 · F3-P13 · fix: corte explícito da série CVM

- **ressalva, que bloqueia o F3-3d; bug proposto BUG-3-14**: o corte usa o fim do período, não a data de entrega.
  - `exercicio_anual_mais_recente` aceita `fim <= referencia` (`cvm_provider.py:1097`), e `series_cvm.ttm(acumulados, hoje)` corta pelo período.
  - A própria fixture usada nos testes grava `DT_RECEB = {ano+1}-03-01` (`tests/regressao/test_bug_2c_62_qualidade_produtor.py:48`).
  - Mesmo assim, `test_bug_3_12` aceita o exercício 2023 e `lucro_liquido == -2` num corte de 31/12/2023 (`test_bug_3_12_serie_cvm_ignora_as_of.py:902-906`). A DFP de 2023 foi entregue em 01/03/2024, depois do corte.
  - `test_cvm_corte_explicito.py` faz o mesmo em dois pontos. Aceita TTM com `fim == "2025-06-30"` no corte de 30/06/2025 (linha 4026). E aceita a DFP de exercício não civil no próprio dia do encerramento (linhas 4032-4068).
  - Isso contraria a decisão 3 e o histórico estrito (`decisoes-fase3.md:42,108`, `DT_RECEB ≤ as_of`) e o D17. Os testes "ficam para sempre" e prendem a antecipação como se fosse o valor correto.
  - O teste de regressão `tests/regressao/test_bug_3_14_serie_cvm_documento_entregue_apos_corte.py` deve afirmar o seguinte, com `fonte_anual`:
    - no corte `2024-01-01T02:00Z`, a série não contém 2023 e o snapshot não usa o lucro −2; o resultado é 2022 ou uma abstenção com motivo de entrega;
    - no corte de 02/03/2024 (São Paulo), 2023 entra;
    - o TTM não usa um ITR com `DT_RECEB` posterior ao corte.
  - Destino e destino das asserções atuais: Pergunta 1.
- BUG-3-12 e BUG-3-13: as marcas foram retiradas e o registro diz "corrigido". Pela leitura do código, o 3-12 falharia sem a correção (relógio simulado em 13/10/2026 dá 2025, diferente de 2023). O 3-13 também (a palavra-chave `as_of` provoca TypeError na assinatura antiga). Confere.

## 89fcaa6 · F3-P06 · fix: classe inferida no contexto da IA

- **ressalva**: o gate de mutação não chegou a 80% no módulo. O `ai_core` inteiro deu 237/345 = 68,7%. A DD-23, do claude-code, encolheu o alcance do gate para duas funções (95/97). É uma decisão de executor que enfraquece um gate (Pergunta 3).
- **sugestão**: `ai_core.py:11` agora importa `sentinela.services.analyze_asset`, que carrega pandas e o store. É dependência invertida (o cliente LLM depende do orquestrador). O lugar natural de `contexto_classe_ia` é `domain/`.
- **sugestão**: o motivo da classe inferida vem de um filtro por substring "referência"/"índice" (`analyze_asset.py:42-52`). Já está registrado no diário.
- BUG-2C-14: só a marca saiu e a asserção ficou igual (`test_bug_2c_14_prompt_classe_inferida.py:18`). O registro está como "corrigido (F3-P06)". Confere.

## Transversal

- **Regressão (prioridade 2)**:
  - Nenhum xfail estrito virou não estrito, skip ou teste mais fraco nos seis commits.
  - Os testes existentes que mudaram têm justificativa: `test_store_migracoes.py` (`_so_001`), `test_store_unico.py` (versões `[1, 2]` e 99) e `test_macro_por_data.py` (decisão 31).
  - Os bugs com destino nestes commits estão corrigidos: BUG-2C-14, 3-11, 3-12 e 3-13.
- **Privacidade**: nenhum dado de carteira, `.env`, `data/` ou `outputs/` versionado nos diffs. O diário cita caminhos locais `~/...` e "Downloads", o que é inofensivo.
- **Vocabulário**: nenhum termo proibido em código novo.
- **Achados anteriores**: `docs/loop/historico/fase-2c/auditoria-externa.md` não existe nesta cópia, então não pude conferir duplicação contra ele. Conferi contra `tests/regressao/README.md` e `pendencias.md`, e nenhum achado acima está registrado lá.

## Recalculado por mim

- **Selic no teste SGS → FII**: a fixture `bcdata_sgs_432.json` traz `20/10/2026 = 13.75`, e `AS_OF_GORDON` cai em 20/10/2026 (`tests/apoio_gordon.py:8`). 0,1375 × 0,85 = **0,116875**. Confere com `test_macro_por_data.py`.
- **Bazin ponta a ponta (ABEV)**: 0,0713 + 0,0449 + 0,269 + 0,4612 = **0,8464**, e 0,8464 / 0,06 = **14,1067**. Os quatro valores existem na fixture. Não verifiquei se só esses quatro caem na janela de 12 meses.
- **TTM do F3-P13**: com DFP 2024 = 15 (`fonte_anual`, `zip(range(2021, 2026), (10, 12, -2, 15, 15))`) e ITR com 1º semestre de 2024 = 25 e de 2025 = 30, o TTM é 15 − 25 + 30 = **20**. Confere, ressalvada a antecipação descrita no BUG-3-14.
- **Contagens**: o golden tem 2291 casos, dos quais 288 de FII.

## Não verificado

- Todo número de suíte, por exemplo 3929, 3966, 3973, 3992 e 4091 passed. A suíte não rodou.
- Todos os scores de mutação e as listas de equivalentes, que estão em `outputs/` (fora do git).
- Os "vermelhos antes" de F3-6a, F3-6c, F3-P13 e F3-P06 (logs em `outputs/`).
- Se alguma lente ou bloco de proveniência real traz `NaN`, `date` ou tipo numpy (o risco de quebra do store).
- O inventário de relógios em `284165f`, porque não tenho git.
- A abstenção do consumidor diante de `taxa_real` e `ipca_serie` posteriores ao `as_of` (DD-18).
- A ausência do arquivo de auditoria da 2C, já descrita na seção Transversal.

## Perguntas para o Marcos

1. **Corte da série CVM.** Opção (a): abrir o BUG-3-14 agora, com `DT_RECEB ≤ as_of`, e reescrever as asserções do BUG-3-12 e do `test_cvm_corte_explicito`. Opção (b): manter o corte por período até a 3-b, renomeando os testes como "corte por período, não estrito" e aceitando que mudem na 3-b. O dado que separa as duas está na própria fixture: `DT_RECEB = ano+1-03-01`.
2. **Granularidade do `as_of` no store.** Opção (a): instante, como hoje, e então cada clique é um `original`. Opção (b): dia de São Paulo, e então repetir no mesmo dia vira `recalculo`. Separa as duas saber se o F3-7 e o F3-8b consultam por dia ou por instante.
3. **Gate de mutação.** Aceitar os 81,12% do F3-2d com equivalentes autodeclarados, ou exigir 80% bruto? E aceitar a DD-23 (funções do item) em vez do `ai_core` inteiro (68,7%)?
4. **F3-6b como `refactor:`.** Aceitar que o app deixe de gravar em `analises` e passe a gravar em `resultados_analise` sem um item próprio? Hoje o único leitor de `analises` é `auditoria.py:488`, que ainda aponta para o banco antigo.
5. **`data_preco` no registro.** Produzir o campo na cascata (data do último fechamento usado) ou gravar um motivo explícito de ausência?
6. **Selic do FII com `as_of` = hoje.** Manter a série completa do SGS (3 requisições, timeout de 60 s) ou usar `get_selic_atual` quando `as_of` é hoje?
7. **Falha ao gravar no store.** Derruba a análise exibida, como hoje, ou a tela mostra a análise com um aviso de "não registrada"?

## Os 10 maiores riscos

1. Os testes do F3-P13 prendem como correta a leitura de DFP/ITR entregue depois do `as_of` (antecipação).
2. A semente `autouse` do conftest esconde o caminho de produção da Selic do FII de toda a suíte.
3. A gravação no store sem tolerância a `NaN`, `date` ou numpy pode derrubar o app depois da análise calculada.
4. O registro imutável grava `data_preco` nula em todas as análises reais; o teste só prova o mock.
5. Um `as_of` por instante textual permite dois `original` para a mesma referência (fusos ou `date` × `datetime`).
6. A persistência do app mudou num commit `refactor:` sem registro como mudança de comportamento.
7. Mutação abaixo de 80%: F3-2d bruto e `ai_core`, com equivalentes e alcance do gate decididos pelo executor.
8. `taxa_real` e `ipca_serie` ainda usam o relógio real sob `as_of` passado; a dependência é da recusa do serviço.
9. A Selic do FII agora depende de 3 downloads com timeout de 60 s por análise (latência e disponibilidade).
10. A dependência invertida `ai_core` → serviço → store e pandas acopla o cliente LLM à orquestração.

**Veredito: pode seguir com ressalvas.** Para a 3-a basta o serviço continuar recusando `as_of` passado. O BUG-3-14 e o caminho real da Selic do FII precisam estar resolvidos antes do F3-3d.
