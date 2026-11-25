> Conferido para caminhos locais do autor em 25/11/2026: nenhum encontrado; cópia sem edição.

## Modo FASE — segunda rodada do checkpoint do bloco 0

**Dois bloqueios permanecem.** O F4-C01 ainda admite uma DFP entregue em D quando a análise usa o exercício anterior. O F4-C02 fecha a corrida até a conferência do hash, mas a CVM ainda pode reabrir o arquivo depois de outra execução substituí-lo. Os bloqueios originais do Bazin e do relatório técnico foram fechados.

Auditei os 17 commits Claude Code indicados, em `v2/fase-4`, no recorte `2eac281..f681c56` dentro de `v2-fase-3..HEAD`. Para a DD-98, consultei o diff anterior que originou a decisão, conforme solicitado. A árvore de trabalho terminou limpa.

## Itens da fila

### F4-C01 · `5aebcf1` · Corte da DFP

- **Bloqueia — o corte se perde quando o exercício final é o anterior.** O seletor comprova a versão quando encontra uma DFP elegível do ano corrente. Quando recua um ano, devolve `(ano anterior, None)` e o snapshot e a série voltam a escolher a maior `VERSAO`. Em sonda sintética com corte em 16/06/2026, exercício 2025, V1 entregue em 15/06 com lucro de R$ 100 mil e V2 entregue em 16/06 com R$ 900 mil, **ambos devolveram R$ 900 mil**. Pelo corte aprovado sobre `DT_RECEB` no índice da DFP da CVM, a versão elegível é V1. O teste atual cobre a promoção do exercício de 2026. `tests/regressao/test_bug_4_NN_dfp_ano_anterior_fora_do_corte.py` deve exigir V1 no snapshot e na série quando o seletor recua para 2025. `cvm_provider.py:1139`, `cvm_provider.py:1188`, `cvm_provider.py:565`, `market_engine.py:1277`, `market_engine.py:1519`, `tests/regressao/test_bug_4_15_versao_dfp_fora_do_corte.py:84`
- **Ressalva — a prova retém a versão e perde a data de referência.** O índice é consultado por `CNPJ_CIA`, `DT_REFER` e `VERSAO`. O seletor devolve ano e versão, e a leitura volta a escolher o `DT_REFER` mais recente para aquela versão. A identidade completa do documento precisa permanecer verificável caso o ZIP contenha mais de um período com a mesma versão. `cvm_provider.py:1172`, `cvm_provider.py:1185`, `cvm_provider.py:577`

### F4-C02 · `b2785ad` · Download concorrente

- **Bloqueia — a conferência e o consumo da CVM ainda podem usar arquivos distintos.** Os temporários agora são exclusivos, e a marca vem dos bytes gravados pela própria execução. Isso fecha a troca antes da marcação coberta pela BUG-4-16. A janela registrada pelo executor permanece: depois de conferir o hash de A, o código volta a abrir o caminho compartilhado. Se B publicar nesse intervalo, a leitura pode consumir B com a prova de A. `tests/regressao/test_bug_4_NN_cvm_zip_trocado_apos_conferencia.py` deve intercalar dois ZIPs válidos com valores distintos, publicar B **depois** da conferência de A e exigir que a execução consuma A com sua própria proveniência ou se abstenha. `cvm_download.py:38`, `cvm_download.py:60`, `sentinela/data/proveniencia.py:96`, `cvm_provider.py:322`, `cvm_provider.py:344`, `docs/loop/pendencias.md:253`

### F4-C03 · `46aa114`, `9b4a41f` · ISIN no Bazin

- **Bloqueio fechado.** O descarte por espécie exige ISIN legível. Executei diretamente os seis casos da BUG-4-17, incluindo a abstenção sem conjunto do emissor e o controle com PNA legível. A troca autorizada dos dígitos das preferenciais C a H preserva as asserções da BUG-4-03. `sentinela/data/proventos_b3.py:319`, `tests/regressao/test_bug_4_17_isin_invalido_outra_especie_bazin.py:25`
- **Ressalva já registrada.** O controle de evento próprio ON usa `BRTESTACNOR0`, que falha no dígito verificador. Para isolar a regra de evento próprio ON, o controle precisa usar um ISIN legível. `tests/regressao/test_bug_4_17_isin_invalido_outra_especie_bazin.py:67`, `docs/loop/pendencias.md:256`

### F4-C04 · `65f1b7a` · Relatório técnico

**Bloqueio fechado.** A auditoria passa só `Close` ao motor. Com 60 fechamentos e `High` textual, executei a função anterior a `e29ade6` e a atual. O texto e o objeto de relatório coincidiram. `auditoria.py:374`, `tests/regressao/test_bug_4_18_auditoria_tecnica_ohlc_parcial.py:41`

### F4-C05 · `d4dfc6a` · Quantidade e preço médio

**Ressalvas originais fechadas por inspeção.** A quantidade aceita é convertida em `int` antes do SQLite. O preço médio não finito gera `ValueError` antes do `UPDATE`, preservando a posição anterior. A regressão verifica o tipo SQLite, a redução posterior e a rejeição sem alteração. O limite de inteiros do SQLite e o estouro intermediário com média matematicamente finita já constam das pendências. `database.py:92`, `database.py:120`, `tests/regressao/test_bug_4_19_carteira_tipos_e_media.py:34`, `docs/loop/pendencias.md:257`

### F4-C06 · `6ad2910` · Hora da coleta B3

**Ressalva original fechada por inspeção.** Os dois provedores guardam `obtida_em` no resultado cacheado e o motor o encaminha para `baixado_em`. A regressão avança o relógio, exige que a contagem de chamadas permaneça igual e verifica a hora original nos dois caminhos. A inclusão do provedor de fundos é necessária para o cenário do complemento, embora ele não conste da lista de arquivos do item. Essa ampliação fica como ressalva de escopo. `sentinela/data/providers/b3_proventos.py:116`, `sentinela/data/providers/b3_fundos.py:49`, `market_engine.py:905`, `market_engine.py:994`, `tests/regressao/test_bug_4_20_hora_download_b3_em_cache.py:36`, `docs/loop/fila.md:86`

### F4-C07 · `ad623b3` · Inspeção do banco

**Ressalva original fechada no caminho de inspeção.** `auditar_banco` exige banco existente, abre com `mode=ro` e oculta por padrão os tickers de análises salvas. Os testes distinguem banco ausente, esquema incompleto e visibilidade com e sem opção explícita. O modo completo ainda pode abrir o banco pelo `MarketEngine`, como documentado. `auditoria.py:5`, `auditoria.py:464`, `auditoria.py:530`, `tests/regressao/test_bug_4_21_auditoria_inspecao_sem_migrar.py:24`

### F4-C08 · `55cb6ee` · Aprovação de proventos

**Sem achado.** A DD-100, aceita pelo Marcos, fecha o item por caracterização. O commit é `test:` e fixa a abstenção no caminho de `entradas`, com controle fora da janela. `tests/test_provento_sem_aprovacao.py`, `docs/loop/pendencias.md:259`

### F4-C09 · `14029b7`, `b27c7be` · Proveniência e bancos

**Ressalvas originais fechadas.** A docstring distingue origem ausente de origem demonstrada. O teste do banco afirma `None` para os dois campos de alavancagem e exige os motivos. O complemento só refluí a docstring. `data_quality.py:3`, `tests/test_contas_cvm_consumidores.py:46`

### F4-C10 · `6a71281` · Golden da Qualidade

- **Predicado confirmado.** As 2.291 linhas anteriores permanecem byte a byte iguais e na mesma ordem. As 12 novas correspondem aos IDs aprovados. Os dois testes de valor para empresa e banco passaram em execução direta. `docs/decisoes/predicados-golden-4.md`, `tests/test_qualidade_golden_valores.py:31`
- **Ressalvas para pendências.** O gancho em `tests/test_analysis_service_as_of.py:237` permite consumir os casos novos pelo serviço, mas o arquivo ficou fora da lista aprovada. A variante de entrega posterior tem coleta anterior à entrega, inconsistência já registrada para futura revisão do golden. `docs/decisoes/golden-qualidade-4.md`, `tests/apoio_qualidade.py:77`, `docs/loop/pendencias.md:260`

### F4-C11 · `816f16a`, `c88238f`, `f681c56` · ISIN nos fatores acionários

**Fechado conforme a decisão registrada.** ISIN ilegível fora do conjunto do emissor, dentro da janela, gera abstenção. Executei os dois casos e o controle de descarte do ISIN legível. A exceção para ISIN já pertencente ao conjunto e o código legado inalcançável ficam nas pendências existentes. A fixture autorizada da BUG-3-60 preserva as asserções de emissor alheio. Ela agora usa outro código de emissor, de modo que o nome do caso que menciona a mesma raiz deixou de descrever a fixture. `sentinela/data/fatores_acoes_b3.py:96`, `tests/regressao/test_bug_4_22_isin_ilegivel_nos_fatores.py:21`, `tests/regressao/test_bug_3_60_evento_de_raiz_reciclada.py`, `docs/loop/pendencias.md:263`

## Transversal

- **DD-97 — contesta.** O hash calculado pelo escritor substitui corretamente o `stat` na marcação. A garantia de que a coleta adiantada pertence aos bytes consumidos continua quebrada na CVM. No IF.data, o valor recém-baixado é devolvido da memória, mas a proveniência é consultada separadamente pelo caminho de cache. O teste da troca antes da marcação confirma a proteção específica do F4-C02. `sentinela/data/proveniencia.py:84`, `sentinela/data/providers/ifdata.py:359`, `sentinela/data/providers/ifdata.py:382`
- **DD-98 — confere.** Recalculei o SHA-256 do trecho renderizado no pai e em `c21306d`. Ambos coincidem com os oráculos respectivos, e o diff de `app.py` se restringe aos dois blocos da Carteira. A inclusão do arquivo de teste fora da lista está declarada na decisão. O hash fixa o texto-fonte. A verificação da execução desses ramos da interface continua pendente. `tests/test_app_analysis_service.py:29`, `tests/test_app_analysis_service.py:245`, `docs/loop/pendencias.md:243`
- **DD-99 — confere.** O teste passa a preparar explicitamente um banco vazio e conserva a asserção de zero posições. A BUG-4-21 verifica separadamente que a inspeção com banco ausente não cria arquivo. A edição do caso existente está declarada na decisão. `tests/test_auditoria_contrato.py:121`, `tests/regressao/test_bug_4_21_auditoria_inspecao_sem_migrar.py:24`, `docs/loop/pendencias.md:258`
- **Regressão.** Os oito `fix:` selecionados têm regressão e registro de corrigido, da BUG-4-15 à BUG-4-22, sem marcas `xfail` no estado entregue. Por inspeção, cada grupo tem pelo menos um caso que distingue o comportamento original da correção. O diff não converte `xfail` estrito em não estrito ou `skip`. A BUG-4-15 e a BUG-4-16 voltam pelas variantes descritas acima. Os demais BUG-4 anteriores ao recorte estão registrados como corrigidos. A rodada não revalidou essas entregas anteriores. `tests/regressao/README.md:392`, `tests/regressao/README.md:406`, `pytest.ini:7`
- **Metodologia e abstenção.** Os efeitos numéricos do recorte vêm da versão e disponibilidade dos insumos, da atribuição de eventos e da persistência. Não identifiquei alteração de fórmula, taxa ou limiar. Na Qualidade, o oráculo distingue lucro dos controladores para ROE e lucro consolidado para margem, conforme a ficha. Na DFP, o achado é de identidade documental e corte pelo leiaute CVM. A validação do dígito ISIN usa a ISO 6166. `docs/metodologia/qualidade.md`, `cvm_provider.py:1172`, `sentinela/data/proventos_b3.py:122`
- **Privacidade e registros auxiliares.** Não identifiquei posições reais ou segredos no diff selecionado. A árvore versionada não lista arquivos sob `data/` ou `outputs/` na raiz, nem `.env` real. O conteúdo de `.env.example` ficou fora da leitura. `52cc1b2` retirou os caminhos pessoais do relatório revisado e acrescentou a instrução aos prompts. `57ef435` registra o pedido de segunda rodada. A ratificação de `max_age_days` fecha a ressalva do F4-A18. Ruff `E9,F63,F7,F82` e `git diff --check` passaram. `scripts/auditar.py:48`, `docs/loop/protocolo.md:79`, `docs/loop/pendencias.md:251`

## Recalculado por mim

- **DFP.** Com `DT_RECEB < 16/06`, a V1 de 15/06 é elegível e a V2 de 16/06 fica fora. A sonda em memória executou o seletor, o cálculo e a etapa da cascata com demonstrativos sintéticos. Obteve `(2025, None)` e R$ 900 mil no snapshot e na série, contra R$ 100 mil pelo corte.
- **Download.** Em memória, o hash de A confirmou a marca e antecipou `data_coleta` de `15:00:30` para `15:00:00`. A conferência termina antes das reaberturas do caminho no consumidor. O cenário de troca posterior foi verificado pela ordem das operações.
- **Qualidade.** ROE de 10% a 14%, média de 12% e desvio populacional de 1,414214 p.p. Margens de 12% a 16% e alavancagem de `200 ÷ 400 = 0,5`. Recalculei os SHAs do golden, `1759c55f…` e `6ad83081…`, e comparei as linhas diretamente.
- **ISIN e relatório técnico.** Recalculei por módulo 10 os seis dígitos das preferenciais C a H e o de `BRLRE2ACNPR6`. Confirmei também que `BRTESTACNOR0` é inválido. No relatório técnico, comparei texto e JSON com a função anterior ao refactor.

## Não verificado

- O pytest completo parou antes da coleta porque o sandbox não permite criar temporários no diretório autorizado. O `conftest.py` também exige `mkdtemp`. As sondas e chamadas diretas acima ocorreram em memória, com rede, leitura de `.env` e configuração de log desativadas. O PASS da suíte e o ciclo vermelho → verde de cada commit continuam sem confirmação independente.
- Os totais do diário, os relatórios sob `outputs/`, os mutation scores, a checagem manual no app e a incidência da corrida em produção. A sonda da DFP prova o valor entregue na fronteira CVM. O efeito sobre cada lente final permanece sem medição.
- O caminho indicado para a auditoria arquivada da Fase 3 não existe neste `HEAD`. Usei a auditoria versionada em `docs/loop/auditorias/fase-3-codex.md` e o registro de regressões para o cotejo de antecedentes.

## Perguntas para o Marcos

1. **DD-97.** O aceite deve preservar a leitura dos bytes de A quando B substitui o cache, ou permitir abstenção diante da troca? O dado que separa as opções é a frequência de colisões no uso local e o custo de repetir uma análise abstida. Ambas precisam garantir que os bytes lidos correspondam à proveniência.

## Dez maiores riscos

1. Reapresentação entregue em D pode entrar pelo exercício anterior no snapshot e na série.
2. A CVM pode consumir o ZIP de B com a coleta atribuída a A.
3. A versão isolada pode selecionar outro `DT_REFER` quando a numeração se repete entre períodos.
4. Os acumulados TTM de hoje ainda percorrem versões entregues em D, fora do aceite do C01.
5. A proveniência do IF.data é consultada pelo caminho de cache após a obtenção do valor.
6. O aceite do relatório completo ainda precisa distinguir a inspeção do banco da abertura pelo motor.
7. A exceção registrada nos fatores ainda aceita ISIN próprio ilegível por pertença ao conjunto.
8. Quantidade acima da faixa do inteiro SQLite ainda pode levantar `OverflowError`.
9. O golden de Qualidade inclui uma fixture com coleta anterior à entrega.
10. A suíte completa e o vermelho → verde por commit seguem sem confirmação independente.

**Veredito — não pode seguir.**