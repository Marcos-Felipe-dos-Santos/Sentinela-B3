## Modo FASE — Sentinela B3

Auditoria cruzada em `v2/fase-4`, de `v2-fase-3` até `HEAD` (`d829a45`), restrita aos 21 commits indicados pela decisão 23. A seleção cobre o trabalho do Claude Code no bloco 0 e o pedido de checkpoint. O bloco 1 ainda está pendente na fila.

**Quatro pontos bloqueiam o checkpoint**. A seleção da DFP comprova a entrega de uma versão e pode consumir outra, a marca de download pode atribuir um arquivo concorrente à execução errada, o Bazin ainda pode descartar um evento com ISIN inválido e o refactor da auditoria técnica introduz uma exceção em uma entrada que antes produzia relatório.

## Itens da fila

### F4-A08 · `6db6a5d`, `430f17e` · Corte de entrega da DFP

- **Confirmada na seleção do ano.** O exercício não civil só avança quando uma linha anual encerrada tem `DT_RECEB < D` no índice da DFP, pela chave `CNPJ_CIA`, `DT_REFER` e `VERSAO` do leiaute CVM. Entrega em D mantém o ano anterior. A ausência do índice gera motivo explícito. `430f17e` completa as três fixtures negativas e preserva as asserções das fronteiras de período. [cvm_provider.py](/home/marcos/projetos/Sentinela_B3/cvm_provider.py:1121) · [test_cvm_fronteiras_2c.py](/home/marcos/projetos/Sentinela_B3/tests/test_cvm_fronteiras_2c.py:43)
- **Bloqueia — a versão provada se perde na análise corrente.** O seletor devolve só o ano. Na cascata de hoje, `MarketEngine` passa `ano_final` e retira `as_of` do snapshot, que pode escolher a maior `VERSAO` disponível. Com V1 entregue em 15/06 e V2 entregue em 16/06 no mesmo ZIP, para corte em 16/06 o seletor comprovou V1 e devolveu 2026. A leitura corrente fica livre para consumir V2. Fechamento em `tests/regressao/test_bug_4_NN_versao_dfp_fora_do_corte.py`: exigir que o snapshot e a série usem a versão elegível, com valores distintos nas duas versões, e que V2 fique fora em D. [market_engine.py](/home/marcos/projetos/Sentinela_B3/market_engine.py:1220) · [market_engine.py](/home/marcos/projetos/Sentinela_B3/market_engine.py:1248) · [cvm_provider.py](/home/marcos/projetos/Sentinela_B3/cvm_provider.py:562)

### F4-A09 · `34e10fb` · Download da própria execução

- **Confirmada em execução sequencial.** A leitura local antecipa `data_coleta` para o instante da execução e o registro lateral preserva o `mtime`. O efeito sobre números finais de Graham e Rendimento do FII é **não verificável pelos testes do item**. Os casos CVM e Informe leem a proveniência diretamente. No caso Bancos, comparar duas lentes abstidas demonstra igualdade naquele cenário, sem demonstrar igualdade com valor. O teste de inadimplência exige um calendário sintético. [test_bug_4_10_download_da_execucao_no_as_of.py](/home/marcos/projetos/Sentinela_B3/tests/regressao/test_bug_4_10_download_da_execucao_no_as_of.py:159) · [Teste da lente Bancos](/home/marcos/projetos/Sentinela_B3/tests/regressao/test_bug_4_10_download_da_execucao_no_as_of.py:299)
- **Bloqueia — a garantia de isolamento da DD-97 é contradita sob concorrência.** A publica seu arquivo e, em operação separada, consulta `stat(dest)`. Se B publicar no intervalo, A registra a identidade do arquivo de B e o aceita com a hora de A. Reproduzi em memória a etapa de marcação e leitura com a identidade já substituída. Os downloads CVM e IF.data também usam um nome `.tmp` fixo por destino, o que permite interferência antes da publicação. Fechamento em `tests/regressao/test_bug_4_NN_download_concorrente_no_as_of.py`: intercalar A e B com bytes distintos, exigir que A aceite somente sua própria versão ou se abstenha e verificar que dois downloads do mesmo destino não compartilhem o temporário. [cvm_download.py](/home/marcos/projetos/Sentinela_B3/cvm_download.py:29) · [ifdata.py](/home/marcos/projetos/Sentinela_B3/sentinela/data/providers/ifdata.py:359) · [proveniencia.py](/home/marcos/projetos/Sentinela_B3/sentinela/data/proveniencia.py:84)

### F4-A10 · `7ec079a` · Dois instantes na proveniência

- **Ressalva — a alegação de hora real do download é contradita para a B3.** O motor preenche `baixado_em` com a hora em que a chamada retorna. A relação de proventos pode vir do cache na repetição da mesma coleta explícita. Nesse caso, a nova hora é registrada sem novo download. Para os arquivos CVM, Informe e IF.data, os dois campos são adicionados à leitura da execução e o esquema lateral permanece igual. A preservação das guardas foi confirmada no diff. A igualdade de todos os valores de lente ficou **não verificada em execução**. Fechamento em `tests/regressao/test_bug_4_NN_hora_download_b3_em_cache.py`: repetir a consulta com a mesma chave em dois instantes, contar uma única coleta e exigir que o registro preserve o instante original. [market_engine.py](/home/marcos/projetos/Sentinela_B3/market_engine.py:399) · [b3_proventos.py](/home/marcos/projetos/Sentinela_B3/sentinela/data/providers/b3_proventos.py:112)

### F4-A11 · `c21306d` · Posições da carteira

- **Confirmada para as entradas da regressão existente.** A fronteira rejeita os tickers e valores inválidos enumerados, trata `sqlite3.Error` e preserva a regra de custo médio. **DD-98:** a atualização do hash é compatível com a mudança autorizada de interface. O hash caracteriza o texto-fonte. A execução dos ramos da aba segue pendente no bloco 2, conforme registrado. [database.py](/home/marcos/projetos/Sentinela_B3/database.py:15) · [app.py](/home/marcos/projetos/Sentinela_B3/app.py:471) · [pendencias.md](/home/marcos/projetos/Sentinela_B3/docs/loop/pendencias.md:243)
- **Ressalva — quantidade aceita vira BLOB.** Em SQLite em memória, `np.int64(10)` passa por `numbers.Integral`, a gravação retorna `True` e `typeof(quantidade)` devolve `blob`. Uma atualização posterior encontra bytes onde espera um inteiro. Fechamento em `tests/regressao/test_bug_4_NN_quantidade_integral_em_blob.py`: uma quantidade integral do NumPy deve ser recusada sem gravar ou persistida como `INTEGER`, com redução posterior funcionando. [database.py](/home/marcos/projetos/Sentinela_B3/database.py:21) · [Encaminhamento ao SQLite](/home/marcos/projetos/Sentinela_B3/database.py:125)
- **Ressalva — entradas finitas podem persistir preço médio infinito.** Duas inclusões de 2 unidades a `1e308` retornaram sucesso e gravaram `inf`. A média ponderada é `1e308`. Fechamento em `tests/regressao/test_bug_4_NN_preco_medio_infinito.py`: exigir média finita correta ou rejeição sem alteração da posição anterior. [database.py](/home/marcos/projetos/Sentinela_B3/database.py:113)

### F4-A11b · `534bd3a` · Validador ISIN compartilhado

Sem achado no refactor. O corpo do validador ISO 6166 foi movido para `proventos_b3`, e o consumidor de fatores passou a chamar a mesma função. [proventos_b3.py](/home/marcos/projetos/Sentinela_B3/sentinela/data/proventos_b3.py:122)

### F4-A11c · `b0ffcf7`, `0e21e9b` · ISIN inválido no Bazin

- **Bloqueia — a alegação de abstenção para ISIN inválido é contradita.** A correção protege o descarte por emissor, mas a linha seguinte ainda extrai a espécie de um ISIN ilegível e pode descartar o evento por espécie. Com o arranjo da BUG-4-04 para ON, `BRALHEACNPA0` falha no dígito verificador e, mesmo assim, libera DY de `0,15`. `BRALHEACNOR0` se abstém. A BUG-4-12 só varia o dígito e a caixa em exemplos cujo trecho de espécie é ON. O `b0ffcf7` registra a parada e a troca autorizada do literal preserva a asserção da BUG-4-04. Fechamento em `tests/regressao/test_bug_4_NN_isin_invalido_outra_especie_bazin.py`: exigir abstenção com o motivo do evento quando um ISIN inválido e dentro da janela aparentar outra espécie. Manter um controle com descarte comprovado. [proventos_b3.py](/home/marcos/projetos/Sentinela_B3/sentinela/data/proventos_b3.py:319) · [test_bug_4_12_isin_sem_digito_verificador_no_bazin.py](/home/marcos/projetos/Sentinela_B3/tests/regressao/test_bug_4_12_isin_sem_digito_verificador_no_bazin.py:23)

### F4-A12 · `8294c99` · Banco e saídas da auditoria

**Ressalva.** Confirmados o banco único, o destino `outputs/auditoria/` e a seção Carteira com só a contagem por padrão. A abertura pode criar ou migrar o banco, e a seção Análises salvas continua expondo os tickers analisados. Os dois efeitos constam das pendências da fase. Para fechar a ressalva, o aceite precisa definir se a inspeção deve abrir o banco sem migração e se o relatório padrão pode incluir esses tickers. [auditoria.py](/home/marcos/projetos/Sentinela_B3/auditoria.py:457) · [unico.py](/home/marcos/projetos/Sentinela_B3/sentinela/data/store/unico.py:263) · [pendencias.md](/home/marcos/projetos/Sentinela_B3/docs/loop/pendencias.md:246)

### F4-A13 · `e00deab` · Classe do ativo na auditoria

Sem achado no roteamento. Confirmado o uso de `AssetClassifier().is_fii`. A regressão testa a escolha de motor pelo `main`, com dublês nos destinos. A alegação sobre os valores ou as abstenções produzidos por esses motores fica **não verificada por esse teste**. [auditoria.py](/home/marcos/projetos/Sentinela_B3/auditoria.py:662) · [test_bug_4_14_auditoria_classe_pelo_indice.py](/home/marcos/projetos/Sentinela_B3/tests/regressao/test_bug_4_14_auditoria_classe_pelo_indice.py:53)

### F4-A14 · `e29ade6` · Motor técnico na auditoria

**Bloqueia — a preservação geral da saída é contradita.** Executei a função antes e depois do commit com 30 fechamentos numéricos, `High` textual e `Low` numérico. Antes, o relatório produziu RSI `50,0`, médias indisponíveis e tendência indefinida. Depois, o cálculo de ATR acionado pela delegação levantou `TypeError`. A caracterização existente fixa o comportamento dos cenários escolhidos, principalmente séries de fechamento. O hash serve para caracterização, sem validar o RSI de Wilder. Fechamento em `tests/regressao/test_bug_4_NN_auditoria_tecnica_ohlc_parcial.py`: exigir o mesmo registro para fechamento utilizável com `High` ou `Low` inválido, ou aplicar a parada `[!]` prevista no aceite e destinar a mudança ao bloco 2. [auditoria.py](/home/marcos/projetos/Sentinela_B3/auditoria.py:366) · [technical_engine.py](/home/marcos/projetos/Sentinela_B3/technical_engine.py:63) · [Fila](/home/marcos/projetos/Sentinela_B3/docs/loop/fila.md:68)

### F4-A15 · `33d7878` · Documentação das camadas e da qualidade

**Ressalva.** A nova docstring afirma que P/L e P/VP derivados só são comparados entre fontes diferentes. Quando a origem não está demonstrada, `_mesma_fonte` devolve `False` e os checks ainda podem rodar. Ajustar a descrição para distinguir proveniência ausente de fontes comprovadamente distintas. O diff deste item altera textos e docstrings. [data_quality.py](/home/marcos/projetos/Sentinela_B3/data_quality.py:3) · [Regra para proveniência ausente](/home/marcos/projetos/Sentinela_B3/data_quality.py:274)

### F4-A15b · `6bcf5dd` · Divisão de trabalho

Sem achado novo. D31 e F5-1 passam ao Codex nos documentos previstos. As referências residuais ao Jules estão registradas em pendências.

### F4-A16 · `932a1b3` · Remoção de `divida_pl`

**Ressalva.** Confirmada a remoção da chave e do único cálculo, sem consumidor de produção identificado. As três asserções removidas verificavam a chave aposentada. Com isso, o teste que promete verificar ausência de alavancagem no banco deixa de testar qualquer campo de alavancagem. A lacuna já consta das pendências. Fechar com asserções sobre `divida_liq_ebitda` e `div_liq_patrimonio`, ou dar ao teste um nome compatível com o que restou. A distinção entre PL e outras contas do BPP usa o leiaute CVM e o mapeamento por código e descrição da D20. [test_contas_cvm_consumidores.py](/home/marcos/projetos/Sentinela_B3/tests/test_contas_cvm_consumidores.py:39) · [cvm_provider.py](/home/marcos/projetos/Sentinela_B3/cvm_provider.py:36)

### F4-A17 · `f732602` · Chamadas duplicadas nos testes de FII

Sem achado. O diff elimina duas chamadas idênticas e preserva as asserções distintas e os casos com argumentos diferentes.

### F4-A18 · `3a63b2a` · Mapas manuais e vulture

**Ressalva de aceite.** Os mapas saem da instrumentação e continuam no `also_copy`. A retirada de `max_age_days` pedida na fila ficou pendente. A exceção tem referência nos dublês indicados no diário. Fechar com a ratificação do aceite revisado ou com evidência do vulture que permita a remoção. [pyproject.toml](/home/marcos/projetos/Sentinela_B3/pyproject.toml:5) · [test_market_engine.py](/home/marcos/projetos/Sentinela_B3/tests/test_market_engine.py:77)

### F4-A19 · `4094be1` · Cobertura da Qualidade

Sem achado no levantamento. Confirmados 2.291 casos no golden, 1.924 ações com cinco exercícios observados e zero valores preenchidos nos cinco indicadores dos 9.620 exercícios. O commit apresenta opções e predicado, sem regeneração. [golden-qualidade-4.md](/home/marcos/projetos/Sentinela_B3/docs/decisoes/golden-qualidade-4.md:8)

### F4-A20 · `d5bf7de` · Caminhos locais

Sem achado. Confirmada a precedência `--saida` → `SENTINELA_AUDITORIA_DESTINO` → `outputs/auditorias/`. A busca pelos padrões pessoais do ticket no `HEAD` retornou zero arquivos. [scripts/auditar.py](/home/marcos/projetos/Sentinela_B3/scripts/auditar.py:336)

### Registros de revisão e checkpoint · `bf73c5a`, `8314d34`, `d829a45`

Sem achado adicional nos diffs documentais. A falta de revisão ligeira em `bf73c5a` foi reconhecida em `8314d34`. A contagem do pedido R2 confere para `769e385..d5bf7de`, com 20 commits Claude Code e dez Codex. `d829a45` é o 21º commit Claude Code da seleção. A confirmação documental da DD-93 precisa incorporar a falha da F4-A11c.

## Transversal

- **Regressão.** Os seis `fix:` selecionados têm regressão identificável, registro atualizado e testes sem `xfail` no estado entregue, da BUG-4-09 à BUG-4-14. Por inspeção, os oráculos têm casos que distinguem o comportamento anterior do novo. Isso inclui a falha de roteamento com o `main` real e a leitura dos dois relatórios em um banco sintético. O **PASS** e o vermelho anterior são não verificados por execução. O diff selecionado não converte `xfail` estrito em `skip` ou `xfail` não estrito. As lacunas e reduções de cobertura observáveis estão nos itens correspondentes. [tests/regressao/README.md](/home/marcos/projetos/Sentinela_B3/tests/regressao/README.md:400) · [pytest.ini](/home/marcos/projetos/Sentinela_B3/pytest.ini:7)
- **Seleção por autoria.** F4-A00a, A00, A01, A02, A03, A00b, A04, A05, A06 e A07 estão fora da seleção. BUG-4-01 a BUG-4-08 aparecem como corrigidos e têm arquivos de regressão, sem parecer sobre a entrega nesta rodada. BUG-3-63 foi fechado antes do bloco 0. BUG-3-60 já estava registrado como corrigido e recebeu casos adicionais no commit Codex de F4-A05. Nenhum desses dois closures foi reexecutado aqui.
- **Números e metodologia.** Nenhum commit selecionado altera a fórmula, taxa, janela ou limiar de uma lente. Os efeitos numéricos encontrados vêm do documento escolhido, da disponibilidade do insumo, da classificação ou da persistência. A retirada de `divida_pl` tira uma chave de fronteira. O refactor técnico altera a capacidade de produzir relatório em uma borda. Mutation score e igualdade com o golden não demonstram validade econômica, conforme D28.
- **Privacidade e integridade.** Não identifiquei dados da carteira real ou segredos nos diffs selecionados. As posições usadas nas regressões são sintéticas. A lista versionada não contém entradas em `data/` ou `outputs/` na raiz, nem `.env` real. O marcador `.env.example` aparece pelo nome e seu conteúdo ficou fora da leitura. Os dois commits que alteram o golden no intervalo são Codex, fora da seleção. `git diff --check` e Ruff `E9,F63,F7,F82` passaram. O diretório de trabalho terminou limpo.
- **Auditoria anterior.** O caminho `docs/loop/historico/fase-3/auditoria-externa.md` não existe neste `HEAD`. Usei os relatórios versionados em `docs/loop/auditorias/`, incluindo `fase-3-codex.md` e `fase-3-gemini.md`, e o registro de regressões para identificar antecedentes.

## Recalculado por mim

- **DFP.** Para corte em 16/06, 15/06 satisfaz `DT_RECEB < D` e 16/06 fica fora. Executei o seletor real com duas versões sintéticas. Retornou 2026 sem a identidade da V1.
- **Bazin.** Conferi o dígito por módulo 10 e reproduzi a janela sintética. `BRALHEACNOR9` passa na estrutura e no dígito. `BRALHEACNOR0` e `BRALHEACNPA0` falham. A série liberada indevidamente divide R$ 1,50 por R$ 10,00 e retorna `0,15`, ou 15%. O yield é uma razão nominal bruta. [Ficha Bazin](/home/marcos/projetos/Sentinela_B3/docs/metodologia/bazin.md)
- **Carteira.** Duas parcelas com mesmo preço têm média igual ao próprio preço. O caso com `1e308` isolou o estouro da multiplicação intermediária. Em outro caso, `typeof(quantidade)` demonstrou o armazenamento como BLOB.
- **Golden.** Contei 2.003 ações e 288 FIIs. Nos 9.620 exercícios observados da Qualidade, contei zero valores presentes em cada um dos cinco indicadores. SHA-256 começa em `1759c55f7e5995f5`.

## Não verificado

- A suíte e o ciclo vermelho → verde por commit. O pytest parou antes da coleta porque o sandbox bloqueou a criação de temporários na pasta autorizada. O `conftest.py` também exige `mkdtemp`, de modo que trocar o modo de captura não tornaria a suíte executável em somente leitura.
- Os totais de testes do diário, os mutation scores, Vulture e Deptry, a checagem manual no app e os arquivos de evidência citados sob `outputs/`.
- A versão efetivamente consumida e o valor final das lentes num E2E com duas versões da DFP. A falha de encaminhamento da versão foi verificada no código e o seletor foi executado em memória.
- A ocorrência da corrida de download em produção. Verifiquei a janela no código e simulei a marcação do arquivo já substituído. A regressão completa precisa controlar a concorrência no download.
- A disponibilidade real de publicações do IF.data e o efeito numérico de ponta a ponta dos ZIPs renovados. A auditoria ficou offline e não abriu dados nem banco locais.

## Perguntas para o Marcos

1. **DFP corrente.** Aplicar o mesmo corte diário ao snapshot e à série ou admitir entrega em D quando houver hora oficial anterior ao clique? O dado que separa as opções é a disponibilidade de hora oficial confiável por versão. O índice usado neste item oferece a data.
2. **Relatório do banco.** Manter criação e migração automáticas, ou exigir banco existente com abertura de inspeção? Manter tickers das análises salvas no relatório padrão, ou exigir opção explícita também para eles? A decisão depende de o relatório servir apenas ao diagnóstico local ou poder circular externamente.
3. **P1 e F4-A18.** Escolher entre enriquecer a grade comum, acrescentar a família de 12 casos ou declarar a lacuna. O dado para decidir é a cobertura de valores obtida por caso e a extensão do diff a revisar. Na mesma decisão de checkpoint, ratificar ou não a permanência de `max_age_days` com alvo nos dublês.

## Dez maiores riscos

1. A prova de entrega da DFP pode autorizar o ano e a leitura corrente usar outra versão.
2. Downloads concorrentes podem atribuir à execução um arquivo publicado por outra.
3. Um ISIN inválido com aparência de outra espécie pode liberar número no Bazin.
4. O relatório técnico pode parar no ATR por um campo que o relatório anterior dispensava.
5. O preço médio persistido pode virar infinito com preços de entrada finitos.
6. Uma quantidade integral do NumPy pode corromper o tipo da posição no SQLite.
7. A proveniência B3 pode registrar como download novo uma leitura de cache.
8. O relatório sem a flag de carteira ainda pode expor tickers das análises salvas.
9. O golden cobre as abstenções da Qualidade e deixa os cinco indicadores sem trava de valor de ponta a ponta.
10. O gate de regressão da seleção segue sem confirmação independente em execução.

**Veredito — não pode seguir.**