# Decisões antecipadas da Fase 3 — Tempo como entrada

**Preparadas pelo Claude (chat) em 09/11/2026** sobre `docs/PLANO.md` (F3-1 a F3-10, gate e decisões pendentes) e `docs/loop/fila-fase3-proposta.md` (F3-P01 a P16, oito casos xfail). Valem depois da aprovação do Marcos. Quando uma decisão exige ficha (D21), ela fixa a direção, e a ficha fixa os números.

## 0. Estrutura: três metades e duas paradas planejadas

A Fase 3 é a maior até agora: dados históricos de 15 anos, banco único e backtest. **Sugestão:** três filas, cada uma terminando num checkpoint com auditoria.

- **3-a, fundação e dívidas (sem dado histórico novo).** F3-1 (macro por data, sem rede no import, E-6), F3-2 (SQLite único com migrações, E-14), F3-6 (`analisar(ticker, as_of)` conectado ao app), F3-P13 (data explícita na série) e os bugs migrados (F3-P01 a P06, P08). **Gate:** `as_of` = hoje reproduz o resultado atual (golden inalterado), e o banco migrado sem perda.
- **3-b, histórico ponto-no-tempo.** Levantamento das fontes (L1, abaixo), depois F3-3 (demonstrações PIT), F3-4 (COTAHIST longo e eventos), F3-5 (universo PIT com deslistadas), F3-7 (backfill), F3-P07, P09 a P12, P14 e P15 (os estudos viram contrato antes de código).
- **3-c, backtest.** A ficha do backtest (D21), depois F3-8 e F3-P16, F3-9 (limpeza) e F3-10 (resumo).

**Paradas planejadas:**
1. Depois da proposta revisada: auditoria DOCUMENTO pelo Claude (chat), antes de ativar. A fase é cara demais para ativar sem revisão.
2. Depois do levantamento L1: o Marcos confirma as escolhas da seção 2 com os números medidos.

## 1. Regras de execução (as da 2C, mais duas)

- Decisão provisória pelo lado da abstenção, sem parar.
- `[!]` só nos seis casos do plano final da 2B.
- Revisão reprovada só por texto não para.
- **Novo — teste ponta a ponta obrigatório.** Todo item que liga produtor a consumidor tem no aceite um teste integrado pelo produtor real (arquivo no formato oficial → provedor → cascata ou serviço → motor), sem montar a chave à mão. É a lição da 2C.
- **Novo — testes protegidos.** As quebras previstas pela própria fase ficam autorizadas aqui (seção 5). Uma quebra não prevista para o loop.
- **Executores alternados (Claude Code e Codex):**
  - cada commit registra o executor no corpo ("Executor: claude-code" ou "Executor: codex");
  - a troca de executor sempre passa por `passagem` e `retomar`;
  - no fechamento de cada metade, o Codex audita os itens do Claude Code, e o Claude (chat) audita os do Codex (D30). O Gemini faz a auditoria de fase no fim da 3-c.

## 2. Decisões de dados (as que o PLANO deixa para "antes da Fase 3")

**L1, primeiro item da 3-b (levantamento, sem código de produção):** medir e registrar em `docs/decisoes/`:
- tamanho e disponibilidade de DFP/ITR/FCA/cadastro desde 2010;
- COTAHIST anual desde 2010;
- Informe de FII desde o primeiro ano aberto;
- **se os arquivos abertos da CVM guardam versões antigas** (reapresentações), ou só a última;
- o histórico do Tesouro, do SIDRA e do Focus.

Sugestões, a confirmar com os números do L1:

1. **Profundidade:** dados desde **2011** (primeiro ano do ITR aberto, com a DFP de 2010 como abertura). Como Graham, Lynch e qualidade pedem 5 exercícios, a primeira análise completa de ação é em **2016**. FII começa no primeiro ano do Informe aberto mais 13 meses.
2. **Universo PIT:** em cada data, todas as companhias com ação listada na B3 naquela data (FCA e cadastro históricos, mais a presença no COTAHIST), **incluindo as deslistadas depois**, e os FIIs com Informe naquela data. O universo do backtest é esse universo filtrado pela regra de liquidez **daquela data** (63 pregões até a data, sem olhar o futuro).
3. **Reapresentações:** vale a versão entregue até a data (`DT_RECEB ≤ as_of`). Se o L1 mostrar que a fonte aberta só guarda a última versão, a análise histórica usa a última e **declara na proveniência** "possível reapresentação posterior não observável" (viés de antecipação aceito e registrado). Não se reconstrói versão antiga por outra fonte não oficial.
4. **Macro histórico:** NTN-B pelo CSV histórico do Tesouro (desde 2004), IPCA pelo SIDRA, PIB Focus pela série histórica do BCB, Selic pelo SGS. As mesmas regras de corte e idade da 2B, aplicadas à data.
5. **Volume e armazenamento:** os brutos ficam fora do git, em `data/` com a proveniência e o hash de sempre. O L1 mede o espaço; acima de 20 GB, o loop para e pergunta.

## 3. Banco único (F3-2)

- Migrações SQL numeradas em `sentinela/data/store/migrations/`, aplicadas por um executor simples com tabela de versão. **Sem ORM.**
- **Backup antes (D29):** cópia dos dois bancos atuais com hash, contagem de linhas por tabela antes e depois, e restauração testada. As posições da carteira não podem perder nenhuma linha, e o teste confere isso. O conteúdo da carteira nunca vai para arquivo versionado.
- O adaptador de leitura de análises antigas (F2C-4) continua valendo sobre o banco novo.

## 4. Serviço e app (F3-6)

- `AnalysisService.analisar(ticker, as_of)` vira a única orquestração. O `app.py` chama o serviço, e a orquestração duplicada do app sai no F3-9.
- O relógio só é lido na borda (app, CLI). Tudo abaixo recebe `as_of`, e o F3-P13 entra aqui.
- **Permissão para o `app.py`:** só trocar a chamada da orquestração pelo serviço, com a lista de linhas no diário antes. Nenhuma mudança visual.

## 5. Quebras previstas de testes protegidos e do golden (autorizadas)

- **F3-1:** os testes que dependem da semente de Selic no import (`conftest`) podem passar a injetar o macro por data. Asserções numéricas iguais.
- **F3-6:** o golden **não muda** com `as_of` = hoje. Se mudar, é bug e para o loop.
- **F3-8:** os testes do backtest antigo, sobre os CSVs fabricados, saem junto com os CSVs, com o substituto escrito antes (D27).
- Qualquer outra asserção protegida que precise mudar: `[!]`.

## 6. Backtest (F3-8, ficha antes)

**Direção:** educacional, por lente, sem score.
- Para cada lente e data de rebalanceamento (fim de mês), ordenar o universo PIT elegível pela distância ao preço, em quintis.
- Medir o retorno total futuro (preço ajustado e proventos) em 12, 24 e 36 meses de cada quintil, contra o Ibovespa e o CDI.
- Mostrar dispersão, número de ativos e o efeito das deslistadas.
- **Sem otimização de parâmetro sobre o resultado:** as lentes entram como aprovadas. O backtest descreve, não calibra.
- A calibração da banda neutra (adiada na 2C) só pode usar a metade inicial do período, com a outra metade como validação fora da amostra, e só como **proposta** para o Marcos.

## 7. Bugs e itens migrados (F3-P01 a P16)

- **Na 3-a, com os aceites da proposta:**
  - **P01:** emissor B3 pelo código CVM;
  - **P02:** preço médio na redução parcial, sem tela;
  - **P03:** conferência ponderada da unit;
  - **P04:** falha do Informe nos riscos;
  - **P05:** literal OData;
  - **P06:** origem da classe no contexto da IA;
  - **P08:** versão ilegível do Informe;
  - **P13:** data explícita na série.
- **Na 3-b, como estudo e contrato antes do código:**
  - P07 e P09 a P12;
  - **P14:** calendário de proventos, com fonte oficial de 5 anos;
  - **P15:** detecção de reorganização, com regra explícita; até lá, o aviso fixo continua.
- **Na 3-c:** **P16**, junto com o F3-8.
- Os oito casos xfail continuam estritos até cada correção.

## 8. Limpeza (F3-9)

Pelo inventário, com `git rm`:
- os dois bancos antigos, só depois do backup e da migração verificados;
- o cache de 7 dias da cascata antiga;
- a orquestração duplicada do `app.py`;
- o `limpar_banco.py`;
- o `auditar_recomendacoes.py`;
- os CSVs fabricados do backtest.
