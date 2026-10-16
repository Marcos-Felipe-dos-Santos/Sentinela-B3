# Fila do loop — Fase 2A, fechamento das auditorias

Branch: `v2/fase-2a` (já publicado; o loop continua sem push) · Protocolo: `docs/loop/protocolo.md` · Diário: `docs/loop/diario.md`
Origem: auditorias externas da fase (Codex, modo FASE, e Gemini 4 Argon, duas passadas), consolidadas em `docs/loop/historico/fase-2a/auditoria-externa.md`. Decisão do Marcos de 15/10/2026: **todo bug confirmado vira teste de regressão**; os bloqueios criados pela própria 2A são corrigidos agora; os demais ficam como xfail estrito apontando o item que corrige (dispensa escrita da D30).

**Regras desta fila:**
- Golden: só o F2A-42 pode mudar, e só no campo `pvp` de casos de FII com P/VP não finito na entrada (`python scripts/golden_diff.py --onde "<predicado>"`). Os demais itens: `git diff --exit-code HEAD -- tests/fixtures/golden_motores.jsonl` antes do stage.
- `tests/test_financeiro_pre_refactor.py` não muda.
- Nenhum item decide método, taxa, janela ou limiar. As decisões A a D da auditoria seguem para a 2B.
- Cada `fix:` desta fila começa pelo teste do bug em `tests/regressao/` (criado no F2A-40) e termina com a marca retirada e o teste em PASS; o registro `tests/regressao/README.md` muda o estado do bug para "corrigido" no mesmo commit.

Legenda: `[ ]` pendente · `[x]` feito · `[!]` bloqueado · `[DECISÃO]` o loop para aqui

## Itens

- [x] **F2A-40** · test · `test: register audited bugs as strict regression tests`
  Cria a prática "todo bug vira teste" e registra os bugs confirmados pelas auditorias.
  - **Diretório** `tests/regressao/`, um arquivo por bug: `test_bug_2a_NN_<descricao>.py`. Cada teste exercita o comportamento correto esperado e falha hoje pelo motivo do bug. Marca: `@pytest.mark.xfail(strict=True, reason="BUG-2A-NN · <sintoma> · corrige: <item>")`.
  - **Registro** `tests/regressao/README.md`: a regra (abaixo) e uma tabela com ID, sintoma, evidência (arquivo:linha), origem (auditoria e data), teste, item que corrige e estado (aberto | corrigido).
  - **Regra** (no README e numa seção nova "Bugs e regressão" do `docs/loop/protocolo.md` e do `AGENTS.md`, fora da "Fase atual"):
    1. bug confirmado (auditoria, revisão ou uso) vira teste em `tests/regressao/` no mesmo dia, antes de qualquer correção;
    2. bug ainda não corrigido fica xfail estrito com ID e item que corrige; o `xfail_strict` do `pytest.ini` faz o CI quebrar se ele passar sem a marca ser retirada;
    3. a correção retira a marca, o teste fica para sempre e o registro muda para "corrigido";
    4. nenhum item `fix:` fecha sem o teste de regressão do bug que corrige.
  - **CI** (`.github/workflows/ci.yml`): o passo de testes passa a rodar `python -m pytest tests/ --tb=short -rxX`, para listar os bugs abertos em cada execução.
  - **Bugs a registrar** (evidência no `auditoria-externa.md`; "Destino 2B" = item a definir na revisão da proposta da 2B, escrito como `proposta da 2B`):

    | ID | Sintoma | Onde | Corrige |
    |---|---|---|---|
    | BUG-2A-01 | LPA, VPA, ROE, P/L ou P/VP ≤ 0 da CVM descartados no merge; valor positivo anterior ou do cache fica; prejuízo conta como dado ausente | `market_engine.py` `_is_field_missing`, `merge_if_valid` | F2B-8 |
    | BUG-2A-02 | reserva dos controladores liberada quando a conta existe com outra descrição (`MOTIVO_SEM_CORRESPONDENCIA`), contra a D20 | `sentinela/data/controladores.py` `_AUSENTE` | F2A-41 |
    | BUG-2A-03 | linha dos controladores ausente devolve o lucro consolidado mesmo com minoritários no balanço (2.03.09 ≠ 0) | `controladores.py` `lucro_dos_controladores` | F2A-41 |
    | BUG-2A-04 | minoritários do balanço lidos só no modelo do setor, enquanto as outras leituras da reserva usam todos os modelos | `cvm_provider.py` `lucro_controladores_com_reserva` | F2A-41 |
    | BUG-2A-05 | PL total inválido (NaN, linhas divergentes) devolve `None` sem motivo | `controladores.py` `pl_dos_controladores` | F2A-41 |
    | BUG-2A-06 | P/VP NaN ou infinito sai na saída do motor de FII | `fii_engine.py` `analisar` | F2A-42 |
    | BUG-2A-07 | ativo fora do índice oficial (ex.: BPAC11) recebe métodos de ação: `classe_ativo` não é preenchido e a guarda do F2A-29 não dispara | `market_engine.py` `_aplicar_referencia`; `valuation_engine.py` | F2A-43 |
    | BUG-2A-08 | relatório de rastreabilidade diz que o FII sem P/VP usa 1,0 | `sentinela/reports/rastreabilidade.py` | F2A-44 |
    | BUG-2A-09 | relatório de rastreabilidade diz que o LPA da CVM é lucro ÷ ações, quando desde o F2A-36 é o LPA divulgado da espécie | `rastreabilidade.py` (`LIMITES`, `_proveniencia_derivada`) | F2A-44 |
    | BUG-2A-10 | TTM lê o lucro dos controladores sem a regra 7.2 da ficha | `cvm_provider.py` `_acumulados_do_arquivo` | proposta da 2B (antes do F2C-1) |
    | BUG-2A-11 | alerta do F2A-5 compara com o LPA divulgado antes do filtro de coerência | `market_engine.py` `_lpa_divulgado_comparado` | proposta da 2B |
    | BUG-2A-12 | FII da CVM não registra `valores_por_fonte['CVM']`: checagem cruzada do P/VP vira identidade | `market_engine.py` `_buscar_cvm_fii` | proposta da 2B |
    | BUG-2A-13 | FII sem `cd_cvm` recebe o risco "ticker fora da cobertura da CVM" antes da busca do Informe | `market_engine.py` `_buscar_cvm` | proposta da 2B |
    | BUG-2A-14 | Informe Mensal reapresentado na mesma data escolhido sem desempate pela maior `Versao` | `cvm_fii_provider.py` `obter_dados_fii` | proposta da 2B |
    | BUG-2A-15 | DY finito mas fora de 0–25% de uma fonte posterior sobrescreve DY válido anterior | `market_engine.py` merge do DY | proposta da 2B |
    | BUG-2A-16 | ZIP vazio do COTAHIST levanta `IndexError` fora das exceções tratadas | `sentinela/data/providers/b3_cotahist.py` `ler_zip` | proposta da 2B |
    | BUG-2A-17 | método `FiiNav` classifica P/VP ≤ 0 como desconto | `sentinela/methods/fii_nav.py` | proposta da 2B |
    | BUG-2A-18 | método `Graham` com VPA < 0 calcula raiz de negativo (número complexo) em vez de se abster | `sentinela/methods/graham.py` | proposta da 2B |

    Se, ao escrever o teste, um bug não se reproduzir, ele **não** entra como xfail: vai para o diário com a evidência ("não reproduzido") e para a lista do Marcos.

  **Aceite:**
  - 18 arquivos em `tests/regressao/` (ou menos, com os não reproduzidos no diário), todos xfail estrito, cada um falhando pelo sintoma descrito: rodar `python -m pytest tests/regressao -q --runxfail` e colar no diário a linha de falha de cada um;
  - `tests/regressao/README.md` com a regra e a tabela; protocolo e `AGENTS.md` com a seção "Bugs e regressão"; CI com `-rxX`;
  - nenhum código de produção alterado (`git diff --cached --name-status` sem arquivo fora de `tests/`, `docs/`, `AGENTS.md` e `.github/`);
  - golden inalterado; suíte verde (os novos aparecem como xfailed);
  - mutação não se aplica a teste xfail: registre no diário que o rito `test` foi cumprido pela execução com `--runxfail`;
  - gate da fase.

- [x] **F2A-41** · fix · `fix: apply D20 to controlling-interest fallbacks without exceptions`
  Corrige BUG-2A-02 a BUG-2A-05, pela D20 e pela decisão 7.2 da ficha (`docs/metodologia/por-acao.md`), sem decisão nova:
  - "par sem correspondência" é abstenção, não linha ausente (D20: "par sem correspondência vira abstenção com motivo");
  - com a linha dos controladores ausente, o lucro total só entra se não houver minoritários na DRE **nem** no balanço;
  - os minoritários do balanço são lidos em qualquer modelo, como as demais leituras da reserva;
  - PL total inválido devolve o motivo de valor inválido.
  **Testes que mudam:** `tests/test_controladores.py::test_linha_de_outra_conta_conta_como_ausente`, `tests/test_contas_cvm_consumidores.py::test_controladora_zerada_e_minoritarios_nao_lidos_valem_o_total_como_no_f2a_3` e `tests/test_market_engine_acoes_cvm.py::test_sem_linha_da_controladora_vale_o_lucro_total` (fixavam o comportamento revogado; justificativa no diário).
  **Aceite:** os quatro testes de `tests/regressao/` passam a PASS com a marca retirada; registro atualizado; diário com quantas companhias da DFP 2025 mudam de lado (levantamento só de leitura, script e saída em `outputs/`); golden inalterado; mutation ≥ 80% em `sentinela.data.controladores*`; gate da fase.

- [x] **F2A-42** · fix · `fix: keep non-finite P/VP out of the FII engine output` · **[golden]**
  Corrige BUG-2A-06 (furo do F2A-24): P/VP NaN ou infinito vira `None` antes da lente, e o comentário provisório "NaN e infinito seguem como antes (F2A-24)" sai.
  **Aceite:** teste de regressão em PASS; `tests/test_saidas_finitas.py` cobre NaN e infinito no P/VP do FII; golden só no `pvp` dos casos de FII com P/VP não finito na entrada (predicado e contagem no diário); gate da fase.

- [ ] **F2A-43** · fix · `fix: classify assets outside the official index before valuation`
  Corrige BUG-2A-07 (furo do F2A-29): quando o índice não preenche `classe_ativo`, a cascata grava a classe do `AssetClassifier` (UNKNOWN para final 11 sem dado oficial), e a guarda do `ValuationEngine` passa a valer. Sem mudança no classificador nem na guarda.
  **Aceite:** teste de regressão em PASS, com índice falso sem o ticker e ticker terminado em 11; um teste confirma que ticker do índice segue igual; golden inalterado (o harness já passa `classe_ativo`); gate da fase.

- [ ] **F2A-44** · fix · `fix: describe current per-share and FII P/VP sources in the traceability report`
  Corrige BUG-2A-08 e BUG-2A-09: o relatório passa a dizer o que o código faz desde o F2A-11, o F2A-13 e o F2A-36 (FII sem P/VP: lente abstida; LPA da CVM: LPA básico divulgado da espécie, com o recalculado como conferência ou reserva marcada). Valide cada frase contra o código.
  **Testes que mudam:** `tests/test_rastreabilidade.py::test_pvp_ausente_do_fii_e_sinalizado` (exigia o texto antigo).
  **Aceite:** os dois testes de regressão em PASS; nenhuma outra saída muda; golden inalterado; gate da fase.

- [ ] **F2A-45** · docs · `docs: add audit closure summary`
  Acrescenta ao fim de `docs/loop/historico/fase-2a/pr-fase-2a.md` a seção "Fechamento das auditorias": itens F2A-40 a F2A-44 e commits, testes antes → depois, o estado de cada BUG-2A no registro, e as correções do resumo apontadas pelas auditorias ("efeito nulo" do F2A-13 refutado para o relatório de qualidade: confiança 40 → 10 em dado antigo com fonte fundamentus; "ROE negativo passa" depende da fonte, BUG-2A-01; "76 módulos" → contagem real). Depois move com `git mv` esta fila e este diário para `docs/loop/historico/fase-2a/fila-fechamento.md` e `diario-fechamento.md`, e recria `docs/loop/fila.md` só com a linha `[DECISÃO]` do fim da fase.
  **Aceite:** cada número conferido com comando; diff só nesses arquivos.

- [DECISÃO] **Fim da Fase 2A.** O Marcos: confere o CI verde no GitHub depois do push; roda a auditoria rápida (modo FASE, só `F2A-40..HEAD`) num auditor de outra família; abre o PR da fase com `pr-fase-2a.md` como corpo; faz o merge, a tag `v2-fase-2a` e atualiza a "Fase atual" do `AGENTS.md`; revisa a proposta da 2B com a lista de correções da auditoria.
