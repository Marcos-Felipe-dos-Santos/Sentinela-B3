# Fase 2C — qualidade e apresentação

A fase remove a síntese única de preço/score e passa a apresentar lentes independentes, com valor ou motivo de abstenção, regime, janela, fonte e distância ao preço. Bazin é critério de rendimento de 6%, com preço-limite informativo. Qualidade descreve cinco exercícios sem pesos, nota ou efeito sobre o valor das lentes. Não há banda ou sinal por lente nesta fase.

## Entregas e commits

A lista abaixo é extraída do git, incluindo os registros de bloqueio e o merge pós-2B. A fila arquivada é a lista de aceite; o diário conserva evidências e ressalvas por item. F2C-6 foi dispensado, estudos22–25/38 e propostas50–55 não foram convertidos em implementação automática.

```
c2f4037 docs: update README snapshot to main after phase 2B closure
ed00f53 test: register post-closing bugs 2B-51 and 2B-52 with phase 2C destinations
7838ded docs: update phase 2C proposal status and add Bazin-in-median decision
26b4cb4 docs: record why the FII spread constant was kept after fractional-share recalibration
4ef23a7 docs: record 2B closure, FII spread rationale and F2C-49 output preference
8ef7402 docs: activate phase 2C-a with approved decisions
d0d8170 refactor: share CVM parse cache entries
af02a3c fix: stop retrying missing CVM downloads
c4a981b fix: compare share quantities within the same preferred class
aa4818a fix: reject invalid reported EPS at the public boundary
ec8f9e4 fix: validate complete reporting periods by calendar boundaries
1788d99 fix: isolate concurrent provenance writes
4cfeb39 fix: trim CNPJ before provenance lookup
6ddeb94 fix: normalize preferred share class casing
668ca48 fix: enrich listed fund classes with official identities
cc0c3cf refactor: cache repeated public data reads without changing outputs
fb601c3 docs: bound persisted analysis payloads
2a8009d fix: preserve valid cached multiples after invalid market inputs
dbc4df2 docs: specify annual and trailing CVM input contracts
f01b802 fix: require readable matching statements for TTM fallbacks
79e4355 fix: preserve independent CVM series and trailing inputs
cb4ab9c docs: define remaining data boundary contracts
4dd79cf docs: confirm or refute the FII COTAHIST quote caveat
aefd483 docs: decide the share-count confirmation of the recent composition
33e94e6 test: cover extraordinary DVA lines in the bank layout
fd51cd4 fix: choose the IF.data institution by the statement model
a4f7175 fix: date IF.data default rates by the official publication calendar
bc8fb86 docs: scope separate valuation of common shares with several preferred classes
0b2a393 fix: describe the insurer and scope abstentions precisely
41786aa fix: say why leverage was not measured in the leverage notice
1599606 test: close the FII and report coverage gaps from the 2B closing
e160b09 test: prove the Selic independence at the engine boundary
ec6118b test: exercise the full cascade in the statement model regression
aedfbc6 fix: align the traceability report with what the lenses used
a6ef2d0 docs: decide the open scope and notice questions from phase 2B
ca295a7 fix: keep rounded liquidity volumes apart from the minimum in the notice
4cc210a docs: decide the open FII report edge rules
3c7a200 fix: derive peer groups from official reference data
35e0451 refactor: retire duplicated valuation formulas from audits
0d4c408 chore: retire portfolio allocation optimization
3048673 docs: summarize phase 2C-a for external audit
1e24869 docs: draft Graham methodology 2.0
cc2bc7c docs: draft Lynch methodology 2.0
c815e37 docs: draft descriptive quality methodology 1.0
f991d82 docs: draft separate lens presentation methodology 1.0
149bb78 docs: approve methodology sheets and activate phase 2C-b
58391ea fix: use approved normalized fundamental windows
a7db414 fix: align Lynch payout with its approved input profile
548110f feat: add an independent five-year quality lens
b211f44 docs: record protected financial test conflict before presentation changes
ed706d4 fix: separate price distance from alert state
6004f02 docs: record F2C-5 block on protected scale invariant
12df823 fix: present valuation outputs as separate lenses
e01ffef refactor: use price distance vocabulary consistently
3227f5b Merge pull request #26 from Marcos-Felipe-dos-Santos/docs/pos-2b
a7d4fc6 chore: merge main before phase 2C closing
be44f39 chore: clean up phase 2C residue
```

## Decisões e limites

Pacote de26/10, ratificações28/10 e substituições protegidas29/10 em `docs/decisoes/decisoes-2c.md` são a autoridade. Graham2.1: média de cinco LPAs por ações/documento, IPCA até último exercício, VPA final. Lynch2.1: cinco observações/quatro intervalos, nominal, m1, teto25%, payout só contexto. Razão de ações estritamente(0,9;1,1) demonstra compatibilidade; fora exige fator oficial ou abstenção. Reorganização recebe aviso fixo, detecção destinada à Fase3. Gordon e bancos mantêm DFP anual; Bazin mantém12meses data-exB3. Sem nova lente de seguradora, papel ou FoF. Reverso dispensado.

D24: qualidade empresarial, resultados das lentes e qualidade dos dados aparecem separadamente. Cobertura de cinco documentos não certifica comparabilidade; dado ausente não vira zero. D26: somente contrato de alertas em `docs/metodologia/apresentacao.md`§7, sem estado no motor. Entrada e saída usam bandas distintas a aprovar na F4-2; zona de retenção sem nova entrada, cruzamento direto gera transição única, abstenção suspende com motivo e recuperação reavalia entrada. Idempotência/cadência pertencem à F4-2, sem implementação nesta fase.

## Golden e testes protegidos

Predicados e IDs foram registrados ANTES em `docs/decisoes/predicados-golden-2c.md` e no diário: mudanças de janelas, contexto Lynch, bloco de qualidade e apresentação; não houve regeneração indiscriminada. Na apresentação5,2291casos/2280objetos alterados no predicado/11errosouNone preservados, zero valores individuais antigos alterados. Na limpeza,2003casos de ação perdem somente selic sem leitor; entradas, IDs, ordem e saídas preservados,288casos FII intactos. Limites numéricos não foram recalibrados na limpeza.

Cinco substituições A/C foram expressamente autorizadas em29/10: dois testes de score passam a validar lentes/abstenções e ausência de agregado; dois de mediana mantêm insumos/taxas e conferem valores individuais distintos sem síntese; escala conserva as grades e limites0,1–20 por lente com controle não vazio. Demais A/C preservados; nenhuma consolidação adicional foi feita no10.

## Cobertura D32 e limitações de fontes

Baseline cadastral26/10:2545registros (446STOCK,9UNIT,704FII,1043BDR,343UNKNOWN), índice SHA256b29e5b882f7a585517594afa1e8113f9211195cd07eb386f0527b7ecdc952a2b. Universo documental89tickers distintos,81noíndice; isso não é cobertura de valuation. Amostra pública de51ações/units e25FIIs não representa todo o índice nem carteira do mantenedor.

Na comparação pública da apresentação5, mesmo snapshot de51ações/units e corte28/10: Graham18/Bazin7/Lynch2/Gordon12/Bancos0,39distâncias, zero valores individuais alterados versus6004f02. Cobertura condicionada às fontes disponíveis, não replay ponto-no-tempo nem medição atual da B3. Na qualidade,250documentos tiveram hash conferido,247PL iniciais obtidos:51quadros parciais,zero agregados comparáveis. Observações individuais:ROE236,lucro245,margem195,alavancagem193;zero anosB3 com calendário anual comprovado. Isso é ausência de evidência para agregação, não qualidade econômica zero. Qualidade continua parcial quando faltam calendário B3 anual, PL inicial ou prova de comparabilidade. O diário discrimina motivos e hashes; não extrapolar essas contagens.

## Compatibilidade e migrações

Sem migração SQLite. Adaptador de leitura identifica apresentação1.0, histórico e versão desconhecida, preservando números/rótulos/preços/motivos literais; não converte histórico em sinal novo e não sobrescreve namespace do usuário. Colunas legadas podem ficar nulas nas novas análises, registros antigos não são regravados. Schema/backup/restauração D29 ficam paraFase3. API/web/backtesting permanecem fora do escopo.

## Validação e ressalvas

Baseline da fase2575PASS/1skip/14xfail. Antes do merge3503PASS no último gate deF2C-4; em09/11dois testes passaram a falhar por relógio real. Correção autorizada somente nesses testes usa AGORA08/10, sem mudar asserções/fixtures/produção, incorporada ao merge já aberto. BUG-2B-52 integrado deu XPASSestrito porque F2C-5 já corrige a síntese; marca retirada e registro atualizado. BUG-2B-51 permanece aberto/xfail, destinoF2C-48: não esconder como entregue.

Gate final da limpeza:3503PASS/1skip/8xfail/1warning antigo; RuffCI e completos data/methods verdes. RendimentoFII509/549=92,71%; bancos339/388=87,37%, ambos integrais, sempendências/timeout/semcobertura, exportados após o fim. Vulture3→3,Deptry83→83,Ruff161→161; dívida anterior discriminada no inventário. Resultados deF2C-5:valuation1146/1323=86,62%;FII292/329=88,75%;apresentação108/111=97,30%;relatório1625/2007=80,97%. F2C-4apresentação163/166=98,19%. Demais scores por módulo/rodada constam no diário e resumo2C-a. Não confundir resultados globais do mutmut com os módulos alvo.

Ressalvas D27: F2C-1 teve dois testes B contraprovados após implementação, conforme registro cronológico do diário; BUG-2C-54 e59 também têm sequência real discriminada, sem alegar vermelho original quando posterior. Auditoria externa D30 da2C-b ainda deve julgar essas ressalvas. Não constitui dispensa implícita do protocolo.

## Resíduos e ordem de revisão

Marcadores de estimativa manual ficam apenas por leitura/compatibilidade histórica; nenhum produtor manual foi reativado. DY_PERCENTUAL_THRESHOLD permanece usado pela grade golden. Sem exclusão de arquivos não rastreados, outputs ou mutants; caches/artefatos locais não entram no commit. FNET guarda trechos de identidade com hash original e hash do recorte; conferir a ligação cadastral antes de aceitar.

Revisar primeiro decisões/fichas e predicados A/C; depois produtores de janela/comparabilidade/ausência; apresentação e histórico; integridadeFNET; gates/mutação e ressalvas D27. Auditoria externa por família diferente do executorCodex (D30) e decisão do Marcos são pendentes no Checkpoint. Nenhum push/PR/tag ou ativação de próxima fase autorizado.

O próprio F2C-11 fecha este resumo e arquiva fila/diário/resumo no commit `docs: summarize phase 2C and archive the loop`; seu hash consta no git, sem autoalteração do commit. A fila ativa passa a conter apenas o Checkpoint.

## Ressalva de fechamento resolvida — 09/11/2026

Auditoria externa Claude sobre `bece683`: “pode seguir com uma ressalva”, achado 1 no backtest. Marcos aprovou a opção (a). BUG-2C-60 reproduzido antes da correção com xfail estrito e falha explícita com `--runxfail`: análise real pós-F2C-3 sem score era rotulada FORA_DO_ESCOPO. Corrigido no commit `fix: distinguish unavailable backtests from scope abstentions` (hash no git).

Agora essa análise retorna status `INDISPONIVEL` e motivo “backtest indisponível desde a 2C: sem score agregado; reconstrução na Fase 3”. FORA_DO_ESCOPO fica para abstenção explícita do motor, com riscos/motivo preservados. Dublês do caminho atual usam lentes sem score; métricas históricas mantêm o contrato legado. Não se reconstrói backtest nesta fase.

Gate após correção: 3507 passed / 1 skipped / 8 xfailed, um warning antigo; Ruff CI e data/methods verdes, Ruff completo com as mesmas 161 dívidas. Regressão permanente sem xfail, controles de escopo preservados. Checkpoint mantido, sem push ou ativação da próxima fase.

## Auditoria FASE — fechamento complementar em andamento (09/11/2026)

Decisões do Marcos e fila complementar em `docs/loop/fila.md`, diário em `docs/loop/diario.md`. Ativação78b0d4e; fixes commitados:4e4f649 (TTM com prova documental),0901dce (qualidade anual com prova),d7f0c6e (motivo de alavancagem realmente coletado). Cada fix teve xfail estrito e falha explícita com --runxfail ANTES da produção; integrações percorrem produtor real, transporte e consumidor.

No mesmo universo público inicial de51ações/units, mesmos ZIPs2021–2025/hash/corte28/10, comparáveis0→45 e médiasROE0→44; anos de proventosB3 com cobertura continuam0. Não é replay PIT, nem cobertura de todaB3, nem qualidade econômica. Último commit verde:d7f0c6e,3514PASS/1skip/8xfail.

**Fechamento bloqueado em FC2C-64:** omissão aprovada do aviso bancário está implementada localmente com regressão anterior, mas diverge do golden protegido em40casos; suíte local3514PASS/1FAIL/1skip/8xfail. Conferência independente prova que basta retirar exclusivamente aviso_alavancagem dessas40saídas; outros2251casos, entradas/IDs/ordem e valores individuais preservados. Fixture/harness/comparador não alterados. Aguarda liberação específica do predicado [golden]; nenhum fix parcial commitado. FC2C-65–72 pendentes, sem declarar Checkpoint concluído, sem push.

**Desbloqueio FC2C-64 em09/11:** Marcos autorizou explicitamente retirar somente aviso_alavancagem dos40IDs enumerados. Aplicação preserva byte a byte os outros2251casos. Hashes antes/depois e lista integral constam no diário complementar; harness/comparador intactos. Gate3515PASS/1skip/8xfail; fila continua65–72 atéCheckpoint.
