# Decisões da Fase 4 — preparação da fila

Decisões do Marcos de 23/11/2026, tomadas sobre o levantamento de dados do Gemini de 21/11
(`docs/decisoes/levantamento-dados-f4.md`, lacunas L1 a L7) e a auditoria completa do Gemini de 20/11
(`docs/loop/auditorias/projeto-v2-gemini.md`, achados 1 a 18; o achado 4 virou o BUG-3-63, corrigido
na `main` pelo PR #29, e o achado 10 foi corrigido no mesmo PR). A numeração continua a das decisões da
Fase 3 (a última foi a 51, de 20/11/2026). A proposta que as aplica é `docs/loop/fila-fase4-proposta.md`.

## 1. Decisões de dados (bloco 1 da proposta)

**52 · FII no histórico pelo Informe Mensal da CVM (L2).** Numa data passada, quando o complemento da
B3 do fundo (`b3_fundo`, sem data de publicação) não existe na data, a continuidade dos eventos de cota
é demonstrada pelo Informe Mensal da CVM: `Cotas_Emitidas` e `Valor_Patrimonial_Cotas` nos 13 meses
da janela, cada mês pela `Data_Entrega` anterior a D. Mês com salto de VP ou evento de cota que o
próprio Informe não explica abstém a lente, com o motivo. A ficha `docs/metodologia/fii.md` é
atualizada (versão nova, auditoria FICHA) **antes** do código; sem a ficha aprovada, o item de código
não começa. A banda do salto de VP e o que conta como evento "explicado" são da ficha, não do item.

**53 · Identidade dos proventos pelo código CVM (L3).** A identidade do emissor na relação de
proventos da B3 passa a exigir o código CVM da coleta igual ao código CVM do ativo (índice oficial na
data). Cada causa do levantamento (L3, causas C1 a C7) é tratada num item separado, cada um com o
teste vermelho antes (D27) e com a regra da causa escrita no item. A decisão 33 não é afrouxada de uma
vez: o que cada item relaxa vale só para a causa dele, e o resto da decisão 33 continua igual. A C8
(raiz reciclada) não tem caso na sonda; a guarda do C3-03/C3-03b (BUG-3-60) fica como está.

**54 · Ticker que mudou de raiz sem trocar de companhia (L6-A).** Quando o ticker mudou a raiz de
quatro letras e o código CVM e o CNPJ são os mesmos, o ativo é ligado pelo código CVM às coletas e
eventos de proventos já gravados no banco sob a raiz nova. Sem o mesmo código CVM e o mesmo CNPJ no
índice oficial, nada é ligado. Sem coleta nova.

**55 · BPP e DRE individuais sem consolidado (L4).** Quando a companhia não entrega BPP consolidado
no exercício e não tem controladas (provado no BPA individual do mesmo documento), o BPP e a DRE
individuais valem para o modelo do BPP e para as contas da companhia. A proveniência declara
"individual, sem controladas". Sem a prova de ausência de controladas, abstém como hoje. Os pares
das contas individuais entram em `sentinela/data/referencia/contas_cvm.csv`. Os 37 pares da sonda que
têm BPP consolidado e caem no mesmo motivo por documento sem números são do GA2b (F4-H01), não desta
decisão.

## 2. Já aprovadas antes e mantidas

- **Decisão 45 (L1):** conta `f` do FRE para os exercícios de 2010 a 2019 sem Composição do Capital
  na DFP, com a `DT_RECEB` anterior a D e a escala conferida pelo LPA divulgado na DRE; sem conferência,
  abstém. Era o F4-H04 da proposta anterior.
- **L5 (IPCA antes de 12/2016):** aplica a regra existente (DD-39) também ao índice do IPCA usado pelo
  Graham; não é decisão nova.
- **L6-C (companhias deslistadas sem fonte estruturada com data ex) e L7 (IF.data sem calendário de
  publicação):** viram limitação declarada; nenhum item de código.

## 3. Estrutura da fila

- **Bloco 0 — correções do app, antes de tudo.** Os achados críticos e médios da auditoria completa
  que se confirmarem com teste vermelho (1, 3, 5, 6, 7, 9, 2, 8, 14, 15, 17 e a parte confirmada do
  16; o README já descreve a V2), o cache da CVM e do Informe que vence no meio da análise, a gravação
  do instante do clique e do download real na proveniência, e o `AGENTS.md` e o `CLAUDE.md`
  desatualizados. A limpeza (achados 11, 12, 13 e 18) fecha o bloco. Achado que não fica vermelho
  fecha como "não confirmado", com o log, sem código.
- **Bloco 1 — dados, prazo de 2 semanas a partir do início do bloco**, na ordem do levantamento:
  L2 (decisão 52, ficha antes), L3 (decisão 53, uma causa por item), L6-A (decisão 54), L1 (decisão
  45), L5, L4 (decisão 55); no fim, uma sonda para medir o ganho. O que não fechar no prazo vira
  limitação declarada.
- **Bloco 2 — a Fase 4 original** (F4-1 a F4-9 do PLANO) e as heranças F4-H que restarem.

## 4. Regras novas

**R1 · Gate de fase com o app.** O gate de cada fase inclui (a) um teste manual do app pelo Marcos,
com rede real, em uma ação, uma unit e um FII, conferindo os motivos de abstenção, e (b) um teste
[e2e] automatizado do caminho de hoje com o `MarketEngine` real (fontes HTTP simuladas só na borda),
chamando `AnalysisService.analisar(ticker, as_of=agora)`.

**R2 · Auditoria externa por bloco.** A auditoria externa, por uma família diferente da do executor,
roda no fim de cada bloco, não só no fim da fase.

## 5. Regras que se mantêm

- A política de decisão autônoma (`docs/loop/politica-decisao-autonoma.md`).
- A regra 3 da decisão 49: a terceira reprovação de código de um item de auditoria não para o loop; o
  achado vira limitação declarada, com xfail estrito, e a fila segue. Na Fase 4 vale para os itens do
  bloco 0 e para os itens criados por uma auditoria de bloco (R2).
- A regra da decisão 48: achado novo que não seja resultado errado, vazamento de futuro ou perda de
  dado vai para depois (`docs/loop/ideias.md` ou a proposta da fase seguinte), não entra no bloco em
  curso.

## Adendo de 23/11/2026 — decisões do Marcos sobre a proposta

Prevalece sobre o texto acima onde diverge.

- **A1 · Ordem do L2.** A ficha FII 1.4 (decisão 52) é escrita no início do bloco 1 e auditada em
  paralelo; o `[DECISÃO]` da ficha e o código do FII vão para depois do item da decisão 55 (L4).
- **A2 · Faixa do P/VP do FII.** A faixa do `FiiNav` é aposentada: sem alertas de prêmio ou desconto.
  O P/VP continua só como número de contexto descritivo, inclusive quando a lente de rendimento
  abstém.
- **A3 · L6-B.** Autorizada a coleta nova da B3 para os cinco tickers de companhia ativa sem coleta
  (AESB3, CESP6, ENBR3, JBSS3, OIBR3); vira item do bloco 1. A companhia sem relação na B3 vira
  limitação declarada.
- **A4 · Caminhos locais.** O levantamento (`docs/decisoes/levantamento-dados-f4.md`) foi editado só
  para trocar os links locais do autor por caminhos relativos ao repositório; nenhum arquivo
  versionado guarda caminho local da máquina do Marcos.
- **A5 · `BRAPI_TOKEN`.** O `.env.example` tem a linha (conferido pelo Marcos); a frase de que ela
  falta sai do `AGENTS.md` e do `CLAUDE.md` no item de documentação do bloco 0.
