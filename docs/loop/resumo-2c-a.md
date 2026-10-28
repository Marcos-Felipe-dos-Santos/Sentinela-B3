# Resumo da Fase 2C-a para auditoria externa

**Status:** execução 2C-a concluída até F2C-9; auditoria final e fichas pendentes. Branch `v2/fase-2c`, base `5da63b2`, último item de código `0d4c408`. Executor Codex (GPT-6); auditor externo Claude, outra família (D30). Não houve push nem ativação da implementação 2C-b. Este resumo não arquiva a fase e não declara as fichas aprovadas.

## Entrega e commits

| Item | Commit | Entrega |
|---|---|---|
| ETAPA 0 | `8ef7402` | docs: activate phase 2C-a with approved decisions |
| F2C-13 | `d0d8170` | refactor: share CVM parse cache entries |
| F2C-14 | `af02a3c` | fix: stop retrying missing CVM downloads |
| F2C-15 | `c4a981b` | fix: compare share quantities within the same preferred class |
| F2C-16 | `aa4818a` | fix: reject invalid reported EPS at the public boundary |
| F2C-17 | `ec8f9e4` | fix: validate complete reporting periods by calendar boundaries |
| F2C-18 | `1788d99` | fix: isolate concurrent provenance writes |
| F2C-19 | `4cfeb39` | fix: trim CNPJ before provenance lookup |
| F2C-20 | `6ddeb94` | fix: normalize preferred share class casing |
| F2C-21 | `668ca48` | fix: enrich listed fund classes with official identities |
| F2C-26 | `cc0c3cf` | refactor: cache repeated public data reads without changing outputs |
| F2C-27 | `fb601c3` | docs: bound persisted analysis payloads |
| F2C-28 | `2a8009d` | fix: preserve valid cached multiples after invalid market inputs |
| F2C-29 | `dbc4df2` | docs: specify annual and trailing CVM input contracts |
| F2C-30 | `f01b802` | fix: require readable matching statements for TTM fallbacks |
| F2C-31 | `79e4355` | fix: preserve independent CVM series and trailing inputs |
| F2C-32 | `cb4ab9c` | docs: define remaining data boundary contracts |
| F2C-33 | `4dd79cf` | docs: confirm or refute the FII COTAHIST quote caveat |
| F2C-34 | `aefd483` | docs: decide the share-count confirmation of the recent composition |
| F2C-35 | `33e94e6` | test: cover extraordinary DVA lines in the bank layout |
| F2C-36 | `fd51cd4` | fix: choose the IF.data institution by the statement model |
| F2C-37 | `a4f7175` | fix: date IF.data default rates by the official publication calendar |
| F2C-38 | `bc8fb86` | docs: scope separate valuation of common shares with several preferred classes |
| F2C-39 | `0b2a393` | fix: describe the insurer and scope abstentions precisely |
| F2C-40 | `41786aa` | fix: say why leverage was not measured in the leverage notice |
| F2C-41 | `1599606` | test: close the FII and report coverage gaps from the 2B closing |
| F2C-42 | `e160b09` | test: prove the Selic independence at the engine boundary |
| F2C-43 | `ec6118b` | test: exercise the full cascade in the statement model regression |
| F2C-44 | `aedfbc6` | fix: align the traceability report with what the lenses used |
| F2C-45 | `a6ef2d0` | docs: decide the open scope and notice questions from phase 2B |
| F2C-46 | `ca295a7` | fix: keep rounded liquidity volumes apart from the minimum in the notice |
| F2C-47 | `4cc210a` | docs: decide the open FII report edge rules |
| F2C-7 | `3c7a200` | fix: derive peer groups from official reference data |
| F2C-8 | `35e0451` | refactor: retire duplicated valuation formulas from audits |
| F2C-9 | `0d4c408` | chore: retire portfolio allocation optimization |

O próprio commit deste resumo é identificado por `git log -- docs/loop/resumo-2c-a.md`; os quatro rascunhos documentais seguintes terão commits próprios. A fila é a autoridade sobre a parada final.

## Verificação e limites dos gates

Baseline de ativação: **2575 passed, 1 skipped, 14 xfailed**. Gate final do código, F2C-9: **2992 passed, 1 skipped, 8 xfailed**, um aviso antigo do Pydantic. O F2C-8 chegou a3001passed; o9 aposenta nove testes exclusivos do otimizador (sete do módulo, dois da seçãoB). A retirada do caso Gestor na parametrização de telas foi compensada pelo teste do menu mantido. Avisos da quarentena e proibição de alocação permanecem nos testes das três telas existentes. Contraprovas reintroduzindo import/chamada/rota de otimização falharam como esperado. O arquivo aposentado não continha uma camada independente de risco: a volatilidade individual da auditoria e a tela Carteira permanecem, camada completa continua Fase4.

Ruff CI (`E9,F63,F7,F82`) e Ruff completo data/methods verdes, diffcheck limpo. Ruff completo do repositório conserva dívida legada: não se declara o repositório inteiro sem apontamentos. O diário distingue cada medição e o gate bloqueante. Golden byte a byte preservado, SHA256 `3d66c53a5703ff49ef1a45b64c2eaf0d2e602a0504e0334282d961138eb7e428`. Seções A/C do harness financeiro preservadas; no9 só saem dois testesB exclusivos e imports exclusivos. Nenhum método/fórmula foi alterado nesta metade. Há mudanças de validade/diagnóstico nas fronteiras, que não equivalem a manter todo comportamento do sistema.

### Mutação — recortes e ressalvas

As medidas abaixo são históricas por item, com mutmut3 e exportação após término, não uma nova medição conjunta nem soma de mortes atribuíveis a esta fase. Detalhes/denominadores no diário; logs persistentes recentes em outputs/validacao-fase2c, primeiros logs em /tmp podem não sobreviver ao desligamento. Sobreviventes/sem cobertura/timeouts não foram excluídos do denominador.

| Item | Alvo e medida final |
|---|---|
|13|Dois parsers CVM141/148=95,27%; não todo provedor|
|14|cvm_download64/99=64,65%; transporte, declarado abaixo de80%|
|15|acoes_cvm502/551=91,11%; função _por_acao_cvm298/337=88,43%|
|16|acoes_cvm514/566=90,81%|
|17|series_cvm413/442=93,44%|
|18|proveniencia162/205=79,02%; IO, declarado abaixo de80%|
|19|proveniencia178/221=80,54%|
|20|acoes_cvm516/568=90,85%; montagem640/691=92,62%|
|21|correcoes286/310=92,26%; montagem705/774=91,09%; fontes394/457=86,21%|
|26|cache28/33=84,85%; cvm2032/2327=87,32%; cvm_fii422/507=83,23% (2timeouts); b3_fundos55/55; b3_proventos128/196=65,31% transporte; fronteira nova20/21|
|30|cvm2108/2415=87,29%; series456/491=92,87%|
|31|cvm2184/2504=87,22%; market2274/3019=75,32% (fronteiras/orquestração), não se declarou80% no mercado|
|35|gordon_cvm511/579=88,26%|
|36|market2444/3018=80,98%|
|37|ifdata395/451=87,58%|
|39|data_quality443/537=82,50%; valuation1011/1149=87,99%|
|40/42|valuation1023/1161=88,11%; contraprovas nominais no42, não atribuir mortes antigas ao teste novo|
|41|rendimento518/558=92,83%; elegibilidade181/205=88,29%; cvm_fii422/507=83,23%; relatório1200/1488=80,65% (60sem cobertura)|
|43|market2462/3018=81,58%; data_quality443/537=82,50%|
|44|relatório1247/1533=81,34%,60sem cobertura|
|46|liquidez219/228=96,05%|
|7|peers203/246=82,52%|

Revisor deve conferir explicitamente a interpretação do gate G nos itens de IO/transporte abaixo de80% (14,18,26,31). Não foram tratados como itens de teste nem mudança de módulo de cálculo financeiro nesse recorte. Módulos de cálculo tocados e itens de teste foram medidos no escopo declarado; a tabela não substitui essa conferência. Itens documentais e aposentadoria não ganharam score artificial. F2C-8 fez contraprova de invariantes aceitando tudo (5FAIL), sem se atribuir validação econômica das lentes ao mock da orquestração.

Interrupções/rodadas inválidas de mutação não contam como gates: incidente de inodes no31, regeneração dos módulos instrumentados, fixtures ainda em revisão no36/43/44 e processos reiniciados estão no diário. Rodadas finais válidas foram aguardadas, depois exportadas. TMPDIR do projeto adotado após o incidente; não se removeu material não rastreado do mantenedor.

## Bugs e regressão D27

Registro canônico: [tests/regressao/README.md](../../tests/regressao/README.md). Cada correção relatada tem regressão permanente; bugs adiados continuam estritos. Os bugs da2B fechados nesta metade estão nos itens13–21; nomes/IDs e reaberturas constam do registro. BUG-2C-01 a29: **24 corrigidos e cinco abertos** (11–14 e27). O número de casos xfail é diferente do número de IDs.

| Abertos | Destino escrito, sem ativação |
|---|---|
|BUG-2B-29, nome de pregão com barra|F2C-23; não foi antecipado aqui|
|BUG-2C-11, conferência da unit|F2C-50|
|BUG-2C-12, risco do Informe|F2C-51|
|BUG-2C-13, literal OData|F2C-52 (dois casos)|
|BUG-2C-14, classe inferida no prompt|F2C-53|
|BUG-2C-27, versão ilegível do FII|F2C-55, todos os candidatos explicitamente ilegíveis; não amplia política para ausência legada|

O oitavo xfail é legado: `tests/test_database_posicoes.py::test_venda_parcial_preserva_preco_medio`, já presente na baseline, fora do escopo desta fila. O relatório `resumo2ca-suite.txt` foi executado com `-rx` e enumera os oito casos; não é um bug novo descoberto nesta execução.

O BUG-2C-27 foi confirmado no47, regressão --runxfail vermelha, sem correção de produção no levantamento. BUG-2C-28 corrigido no7 (P/L negativo deixa comparação indisponível) e29 no8 (FII abstido não ganha FV/preço). Próximo ID livre30. Não converter xfail em PASS por esperado copiado do código. Auditoria deve conferir o registro e os logs D27, inclusive as provas negativas dos itens com regressão reaberta.

## Decisões provisórias para ratificação

| Item | Caso → escolha conservadora registrada |
|---|---|
|17|Período fora de meses civis completos → não promover a trimestre neste contrato|
|21|Mais de uma identidade complementar do ticker, mesmo equivalente → UNKNOWN|
|26|Validade B3 entre instantes não aprovada → compartilhar só a mesma coleta explícita|
|29|BPP correspondente não demonstrado como lido → não autorizar reserva pela ausência aparente da rubrica|
|30|Comparabilidade estrutural não demonstrada → abster TTM afetado, preservar acumulados e motivos|
|37|Prazo geral60/90dias ou trel.ge não prova publicação → sem calendário demonstrado, abster inadimplência|
|47|Registro da taxa em outro dia local → manter abstenção até prova temporal recalculada (confirmação provisória F2B-58)|
|47|Sem resposta B3 de eventos → manter abstenção por eventos indisponíveis (confirmação provisória F2B-58)|
|7|P/L não positivo/ausente/inválido entre pares utilizados → comparação indisponível com motivo|

São nove escolhas/ratificações operacionais, não nove novas regras econômicas aprovadas. Permanecem as decisões econômicas dos levantamentos: classes preferenciais/ON isolada, saúde/modeloBPP/escopo, contratos FII e vínculo documental, fontes de proventos/eventos, mudança estrutural e histórico estrito. Documentos de referência em docs/decisoes; não se implementa uma opção porque foi descrita.

## Auditoria Claude do primeiro lote e destino F2C-10

Relatório fornecido pelo Marcos: `C:\Users\marcos\Downloads\auditoria-2c-a-lote1-claude-relatorio.md`, lido pelo caminho WSL equivalente. Cobriu de8ef7402 a ca295a7, 31commits; veredito permite seguir e não substitui a auditoria final destes últimos itens ou a auditoria FICHA. Não se atribui a ele aprovação do7/8/9 ou de fichas futuras.

**Ressalva com destino explícito F2C-10:** evidências FNET de BTCI11/TRPL11 guardam páginas inteiras em base64, incluindo scripts de telemetria não executados pelo consumidor. Na limpeza futura, guardar só o trecho necessário das evidências oficiais, mantendo **o hash da página original** como proveniência; vincular o trecho ao documento/fundo/campos e preservar integridade verificável, sem trocar o hash original pelo do fragmento. Atualizar os leitores/testes de evidência no próprio item, sem perder a verificação cadastral. Nenhuma evidência é removida neste resumo.

## Prioridade da auditoria final e resíduos

1. Conferir D27 dos fixes e as interpretações de G acima; grupos oficiais sem média tácita de prejuízo, abstenção/diagnóstico FII e captura única da auditoria.
2. Rever validade temporal: IF.data por publicação efetiva; CVM, TTM, eventos e coleta por as_of sem afirmar garantia PIT.
3. Ratificar as nove escolhas provisórias e pendências dos levantamentos; conferir os destinos não ativados50–55 e escopo econômico das fichas.
4. Revisar remoções do9, depois os quatro rascunhos via auditoria FICHA por Claude. Permanecem para limpeza F2C-10 os marcadores f15 e referências históricas do otimizador, além da ressalva FNET.

A UI atual ainda não apresenta Cobertura/Avisos/Motivo_PL dos pares; revisão interna7 registrou essa limitação, sem ampliar permissões de app.py. Código legado de classificação/sigmoide nos motores continua para2C-b; a saída separada futura não está implementada. Não ler credenciais, carteira real ou banco do mantenedor para auditar. Nenhum arquivo de outputs/mutants entra no git. Nada foi publicado.
