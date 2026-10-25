# Revisão da continuação — pendências da Fase 2B

**22/10/2026 · Executor: codex.** Pedido: executar toda a lista pendente e anotar o feito para revisão. Base desta execução: `9490d66`, árvore limpa. Este registro é parcial da execução da fase, não é encerramento nem aprovação de metodologia. Não houve push, alteração de código, alteração de teste executável, remoção ou mudança de golden nesta continuação.

## Itens conferidos

| Item | Resultado | Evidência / condição para prosseguir |
|---|---|---|
| F2B-4 | bloqueio anterior preservado | Definir evidência que distingue seguradora de empresa/holding no BPP; decisão de 21/10 autoriza só os independentes |
| F2B-32 | pendente, dependente de F2B-4 | Faltam modelo/evidência e casos bancários no harness, além da ponte e relatórios; lente pura não equivale a integração |
| F2B-34 | entregue em `1ef0dc1` | Proposta 2C não ativa, 32 itens com aceites/matriz de fontes; dez bugs abertos ganharam destinos propostos no registro |
| F2B-45 | bloqueio de aceite identificado, sem implementação | Predicado do golden só permite texto, mas o aviso exigido para não finitos/ausência muda outros casos; aguardando definição |
| F2B-5 | bloqueio de aceite identificado, sem remoções | Constantes a remover ainda citadas pelo levantamento histórico 2B não incluído nas exceções do aceite; aguardando definição |
| F2B-6 | bloqueado por dependências | Não arquivar nem declarar encerramento enquanto F4/32/45/5 não forem resolvidos ou dispensados por escrito |

A atualização documental anterior está no `9490d66` (F2B-33): taxas, escopo efetivamente entregue, liquidez, arquitetura e BTG. A seção “Fase atual” de AGENTS.md permaneceu intacta.

## O que revisar no F2B-34

1. Condições de ativação e marcadores econômicos na proposta: janelas por lente, qualidade/classificação/histerese, Lynch/perfil, escopos individuais/FII, reverso e proventos/eventos. Nenhuma dessas decisões foi tomada pelo texto.
2. Matriz fonte → destino: PLANO/ADRs, checkpoint/dossiê, diários 2A/2B, pareceres/ressalvas e regressões. A auditoria final da 2B ainda deve ser incorporada antes da ativação.
3. BUG-2B-02/03/05/07/08/09/10/11/21/29: os dez continuam **abertos**, com xfail intacto. A coluna de destino não é correção.
4. Realizar auditoria DOCUMENTO da proposta e aprovação do Marcos antes de ativar. O levantamento atual não substitui auditoria externa da fase (D30).

## Evidência do bloqueio F2B-45

A regressão existente `tests/regressao/test_bug_2a_23_divida_em_texto_avaliada.py`, executada com `--runxfail`, falhou: “9,5” ainda gera “Dívida elevada”. BUG-2A-23 segue aberto e marcado xfail.

`git grep` confirma que dívida da cascata vem como número/None: `market_engine.py:109` restringe o campo à CVM; `cvm_provider.py:664` recebe `Alavancagem.divida_liq_ebitda`, tipada `float | None` em `sentinela/data/divida_liquida.py:41`. A brapi também converte com `_to_float`, sem fornecer texto no campo ao motor pelo caminho CVM.

O experimento compilou uma cópia do motor **somente em memória**, com o aviso exigido para todo valor que não seja int/float finito (bool excluído). Rodou a grade existente com as sementes de teste, sem gravar módulo ou golden. Resultado:

| Medida | Contagem |
|---|---:|
| Saídas alteradas | 1.630 |
| Alteradas com dívida em texto | 19 |
| Alteradas com dívida ausente/None | 1.607 |
| Alteradas com NaN/infinito | 4 |
| Fora do predicado atual `isinstance(entrada.get('divida_liq_ebitda'), str)` | 1.611 |
| Casos com alteração em riscos | 1.630 |
| Casos com alteração em rótulo | 246 |
| Casos com alteração em score/confiança | 9 cada |

Exemplos fora do predicado: base-renda, renda-dy-0.0, renda-dy-0.01. O efeito nos rótulos vem da regra vigente que rebaixa o rótulo mais forte quando há riscos; não se propôs outra regra. Não executar a alteração parcial só para caber no predicado, nem alterar o golden para esconder essa divergência.

**Definição pendente:** ampliar explicitamente o predicado aos inválidos/ausência e aceitar o efeito no rótulo, ou especificar tratamento de ausência/não finitos diferente, com aceite completo. A pergunta enviada não recebeu resposta; não é autorização presumida.

## Evidência do bloqueio F2B-5 e inventário

`git grep` encontra `scripts/levantamento_fase2b.py:533,539` lendo BAZIN_TAXA_MIN e GORDON_PREMIO_RISCO por AST. O aceite do F2B-5 só permite ocorrências históricas no dossiê e no levantamento 2A. O script 2B já contém construtores das versões antigas dos métodos; atualizar só duas constantes não torna o estudo atual. Não removê-lo, não reescrever resultados históricos nem excluir suas referências da busca silenciosamente.

**Definição pendente:** documentar exceção histórica equivalente, reproduzindo o levantamento no commit original, ou autorizar um item próprio de atualização do script. Nenhum arquivo de produção/teste foi removido enquanto o aceite diverge.

Inventário inicial reproduzido com venv e exclusões do projeto:

| Ferramenta | Antes | Depois desta execução |
|---|---:|---:|
| Ruff completo (`ruff check . --statistics`) | 166 | 166, sem código alterado |
| Vulture ≥80%, com whitelist | 7 | 7, sem código alterado |
| Deptry | 33 | 33, sem dependências alteradas |

São débitos preexistentes. Vulture aponta parâmetros de dublês; Deptry inclui imports locais de apoio dos testes. Não foram corrigidos fora do escopo. Ruff CI e completo data/methods continuam verdes.

## Validação e arquivos para revisão

Baseline: **2429 passed, 1 skipped, 21 xfailed**, 1 aviso antigo do Pydantic (9,54 s). F2B-34: mesma contagem (9,73 s), repetida no safe-commit; Ruff CI/completo data-methods e diff --check verdes; golden byte a byte inalterado. Revisão interna do stage F2B-34: **PODE COMMITAR**, primeira rodada. Não houve mutação nova porque não houve mudança de cálculo/teste executável; medições anteriores não são declaradas reexecutadas.

Artefatos locais auxiliares: `/tmp/f2b34-suite.txt`, `/tmp/f2b34-safe-suite.txt`, `/tmp/f2b45-preflight-red.txt`, `/tmp/f2b45-impacto.json`, `/tmp/f2b5-ruff-antes.txt`, `/tmp/f2b5-vulture-antes.txt`, `/tmp/f2b5-deptry-antes.txt`. /tmp pode desaparecer; números relevantes estão neste documento. Nenhum cache ou arquivo não rastreado foi apagado.

## Prioridade na revisão geral da 2B

Preservar como primeiros pontos do fechamento: spread FII de 3,5058%, cotas fracionárias/exclusões e diferenças da calibração contra o plano; score/contexto de FII abstido; decisões provisórias F2B-54/F2B-2; desvios D27/safe-commit registrados no diário; comprovação da base acionária Gordon/bancos. Este relatório não aceita nem corrige esses pontos por menção. O resumo final F2B-6 ainda deve reunir medições, golden e sensibilidades de 4%/5%/7% quando a fase puder fechar.
