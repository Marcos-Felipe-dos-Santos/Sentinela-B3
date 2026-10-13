# Auditoria externa da ficha por ação e do universo inicial

Relatório final do auditor externo (Codex, `--sandbox read-only`, modo FICHA), sobre `docs/metodologia/por-acao.md` versão 0.1 e `docs/decisoes/universo-inicial.md`, HEAD `17603b6`. Copiado sem edição de conteúdo; só os links para caminhos locais viraram texto.

## Auditoria 1 — ficha versão 0.1

**Modo FICHA.** Escopo: `docs/metodologia/por-acao.md` contra D19, D20, D21, D23 e D28, com auditoria separada de `docs/decisoes/universo-inicial.md` contra D32. Branch `v2/fase-2a`, HEAD `17603b6`. Trabalho somente de leitura, sem importar módulos do projeto, executar seus scripts ou alterar arquivos.

## 1. Ficha por ação: achados

| Severidade | Evidência | Achado e condição para fechar |
|---|---|---|
| **bloqueia** | `por-acao.md:144`; `scripts/levantamento_fase2a.py:263` | A afirmação de que a distribuição F2A-16 usa somente lucro dos controladores está incorreta. Reproduzi os **255 casos**, mas **49 usam lucro consolidado como reserva**, pois o levantamento usa `controladores or total`, inclusive quando a linha é zero. Corrigir a descrição e explicitar a dependência com 7.2, ou refazer a distribuição conforme a política aprovada. |
| **bloqueia** | `por-acao.md:56` | A ficha transforma divulgado “não coerente” em divulgado “ausente”, aplicando a regra 2. D19 não registra essa equivalência. Marcar a escolha como decisão e definir o tratamento, inclusive quando nenhuma outra espécie permite inferir a escala. |
| **ressalva** | `por-acao.md:56`; DRE consolidada da QUAL3 | QUAL3 tem **duas linhas básicas “ON” conflitantes**, −0,00895 e +0,04662; lucro dos controladores positivo, R$ 10.665.000. Há conflito de identificação além do sinal. Para fechar, distinguir esses problemas e registrar como tratar duplicidade conflitante. |
| **ressalva** | `por-acao.md:139`; `sentinela/data/acoes_cvm.py:98` | “Mais perto de 1” significa, no código, menor `abs(log(razão))`. A referência à raiz de 1.000 depende dessa métrica. Escrever a métrica na ficha para tornar a inferência reproduzível. |
| **ressalva** | `por-acao.md:100` | LPA com lucro consolidado da Petrobras arredonda para **8,5815**, não 8,5816. Corrigir; as porcentagens apresentadas permanecem válidas. |
| **ressalva** | `por-acao.md:78`; `data/cvm/dfp_2025.zip.proveniencia.json` | A ficha cita cópia de 8/10/2026; a proveniência do ZIP usado nesta auditoria registra coleta em **1/10/2026**. Os dados dos exemplos coincidem. Identificar o artefato por hash e esclarecer se 8/10 é data de consulta ou de outra cópia. |
| **ressalva** | `por-acao.md:163` | A presença de participação minoritária no balanço demonstra minoritários, mas não prova, sozinha, quanto do lucro do exercício lhes pertence. A mistura de escopos é um risco confirmado; a parcela efetiva exige outra evidência. Ajustar a afirmação categórica. |

A ficha contém os seis componentes exigidos por D21: fórmula, insumos, regime/janela, abstenções, exemplos e sensibilidade. Os exemplos fornecem referência independente para D28. Isso **não fecha D23** enquanto as escolhas da seção 7 permanecerem pendentes, nem substitui os testes futuros do F2A-36.

A referência contábil sustenta média ponderada e distribuição do resultado conforme os direitos das classes. Ela não torna `lucro ÷ ações finais` equivalente ao LPA normativo, nem garante que toda linha divulgada esteja correta. [CPC 41, §§9–20 e A13–A14](https://conteudo.cvm.gov.br/cvm_institucional/export/sites/cvm/menu/regulados/normascontabeis/cpc/CPC_41_rev_12.pdf).

## 2. Recalculado por mim

Li diretamente os CSVs dentro de `data/cvm/dfp_2025.zip`, usando apenas biblioteca padrão e aritmética `Decimal`. Selecionei CNPJ, referência **2025-12-31**, versão **1**, exercício **ÚLTIMO**, DRE e BPP **consolidados**, conferindo código **e descrição** das contas.

SHA-256 do ZIP: `336a92cc2d0829b5b96adcf2550f9acd469503cbf8b8cb6a05873ddd668bc4d2`.

### Petrobras — PETR3/PETR4

CNPJ `33.000.167/0001-01`; documento `155122`, recebido em **5/3/2026**.

Valores extraídos:

- `3.11.01 — Atribuído a Sócios da Empresa Controladora`: **110.129.000**, escala MIL.
- `2.03 — Patrimônio Líquido Consolidado`: **417.587.000**, MIL.
- `2.03.09 — Participação dos Acionistas Não Controladores`: **1.801.000**, MIL.
- LPA básico, descrições ON e PN: **8,54** cada.
- Capital: ON **7.442.231.382**, PN **5.446.501.379**, tesouraria **0**.

Conta:

```text
Ações = 7.442.231.382 + 5.446.501.379 − 0
      = 12.888.732.761

Lucro dos controladores = 110.129.000 × 1.000
                        = R$ 110.129.000.000

LPA recalculado = 110.129.000.000 ÷ 12.888.732.761
                = R$ 8,5445948832

Razão contra divulgado = 8,5445948832 ÷ 8,54
                       = 1,0005380425
Diferença = +0,053804%
```

Na hipótese de ações em milhares, o LPA seria **0,0085445949**, razão **0,0010005380**. A inferência dos exemplos determina **unidade**.

```text
PL dos controladores = (417.587.000 − 1.801.000) × 1.000
                     = R$ 415.786.000.000

VPA = 415.786.000.000 ÷ 12.888.732.761
    = R$ 32,2596493938 ≈ R$ 32,26
```

Para a comparação da ficha:

```text
LPA consolidado = 110.605.000.000 ÷ 12.888.732.761
                = 8,5815263650 ≈ 8,5815
```

**Conferência:** resultados principais corretos; corrigir o arredondamento da comparação. O LPA divulgado usado conforme D19 é **8,54**, separado do recalculado.

### Taesa — TAEE11

CNPJ `07.859.971/0001-30`; documento `155448`, recebido em **17/3/2026**.

Valores extraídos:

- Lucro dos controladores: **1.579.863**, MIL.
- PL consolidado: **7.608.982**, MIL.
- Lucro e participação dos não controladores: **0**.
- LPA básico ON e PN: **1,52866** cada.
- Capital: ON **590.714**, PN **442.783**, tesouraria **0**.

```text
Quantidade bruta = 590.714 + 442.783 = 1.033.497

Hipótese unidade:
LPA = 1.579.863.000 ÷ 1.033.497
    = 1.528,6575577868
Razão contra divulgado = 999,9984023830

Hipótese milhar:
Ações = 1.033.497 × 1.000 = 1.033.497.000
LPA = 1.579.863.000 ÷ 1.033.497.000
    = 1,5286575578
Razão = 0,9999984024
```

A inferência determina **milhar**.

Conferi diretamente no FCA 2026, em `outputs/ref_teste/fontes/`, a composição oficial **“1 ON / 2 PN”**, documento `158852`, versão 1:

```text
LPA divulgado da unit = 1 × 1,52866 + 2 × 1,52866
                     = R$ 4,58598

VPA por ação = 7.608.982.000 ÷ 1.033.497.000
             = R$ 7,3623648641

VPA da unit = 3 × 7,3623648641
            = R$ 22,0870945924
```

**Conferência:** exemplo correto nos arredondamentos apresentados.

## 3. Decisões da seção 7 — opções e dados

### 7.1 Faixa da escala

Reproduzi os números do levantamento original, **incluindo sua reserva de lucro consolidado**:

| Faixa | Fora da faixa, entre 255 |
|---|---:|
| `[0,1; 10]` | 5 |
| `[0,5; 2]` | 17 |
| `[0,8; 1,25]` | 28 |

P10 **0,837**, mediana **1,000**, P90 **1,051**; **209/255** dentro de ±10%. As contagens conferem, mas a base inclui os **49 casos de reserva** mencionados no achado.

Opções apresentadas: manter a faixa; estreitá-la para uma das alternativas; ou revisar a base antes de fixá-la. Há outra escolha associada: a escala indeterminada derruba também o **LPA divulgado**, como exige a redação atual da regra 1, ou apenas os indicadores que dependem da quantidade de ações? A segunda opção exige revisão explícita de D19.

### 7.2 Linha da controladora zerada

Confirmei **439 companhias** com DRE e BPP consolidados, **zero linhas dos controladores ausentes** e **105 casos** com controladores zerados e não controladores zerados ou ausentes.

Na Klabin:

```text
Lucro consolidado = R$ 1.678.211.000
Lucro controladores = 0
Lucro não controladores = 0
PL não controladores = R$ 6.515.155.000

PL controladores = (14.401.101 − 6.515.155) × 1.000
                 = R$ 7.885.946.000

Lucro consolidado ÷ PL controladores = 0,2128103591
```

Opções:

- Equiparar zero a ausência e permitir a reserva.
- Permitir reserva somente sem evidência de minoritários também no balanço.
- Abster diante dessas linhas zeradas e do conflito.
- Preservar literalmente o zero informado, distinguindo-o de ausência; nesse caso, a escala inferida por LPA fica indeterminada.

As duas primeiras ampliam a política escrita em D20. Nenhuma opção foi escolhida nesta auditoria.

### 7.4 Regras 2 e 5

| Opção | Consequência |
|---|---|
| Inferir pela outra espécie do mesmo documento | Permite aproximação quando há divulgado utilizável de outra espécie; sem nenhum, abstém. |
| Obter escala em outro documento/fonte | Amplia a política atual; exige proveniência e evidência de que a escala se aplica ao documento analisado. |

A regra 3 continua tendo precedência: divulgado de outra espécie não autoriza recalculado comum para preferenciais com direitos distintos. Buscar escala histórica também precisa preservar lucro, PL e quantidades do documento analisado.

## 4. Auditoria separada: universo inicial contra D32

Confirmei **85 tickers distintos: 73 atuais e 12 históricos**. Todos os 73 atuais aparecem no índice e alcançam pelo menos 100 negócios à vista nos ZIPs COTAHIST de **julho, agosto e setembro de 2026**. Confirmei também as reapresentações da MRV de 2021 e 2022, recebidas em **6/7/2023**.

| Severidade | Evidência | Achado e condição para fechar |
|---|---|---|
| **ressalva** | `universo-inicial.md:13` | “Atual” incorpora um limiar de **100 negócios** e uma janela específica, acrescentados pelo loop. D32 não fixa esse limiar. Marcos precisa aprovar o critério; não confundir esse recorte com o denominador oficial da cobertura. |
| **ressalva** | `universo-inicial.md:145` | O denominador de D32 está citado corretamente, mas sem cardinalidade e lista materializada nesta proposta. Os **73 atuais** são o universo inicial selecionado, não o total de listados. Para uma afirmação numérica de cobertura, anexar a população e exclusões do mesmo snapshot. |
| **ressalva** | `universo-inicial.md:133` | BTG é exclusão por lacuna do índice, não por ausência de negociação. Isso está explicitado corretamente, mas deixa um dos casos bancários pedidos pela D32 sem cobertura. Fechar por correção ou dispensa explícita do Marcos. |
| **ressalva** | `universo-inicial.md:125` | Um ticker por companhia reduz a verificação de espécies e classes. Registrar a aprovação desse escopo e quais tickers ficam fora da verificação inicial. |

**Sucessores — dados conferidos:**

| Ticker | CNPJ no FCA/índice | Negócios à vista jul–set/2026 |
|---|---|---:|
| AZUL3 | 09.305.994/0001-29 | 34.747 |
| AXIA3 | 00.001.180/0001-26 | 1.968.451 |
| NATU3 | 71.673.990/0001-77 | 739.313 |

Os três satisfazem o critério operacional de atual. AZUL3 e AXIA3 preservam os CNPJs dos respectivos registros antigos; **NATU3 tem CNPJ diferente de NTCO3**, portanto a continuidade histórica exige tratamento explícito.

Opções de escopo: conservar a lista proposta; acrescentar os três sucessores mantendo os antigos como históricos; ou explicitar substituição na cobertura atual. Acrescentá-los produz **76 atuais + 12 históricos = 88 ativos**.

**BTG Pactual:** confirmei no FCA o CNPJ `30.306.294/0001-45`, unit com código **`000000`** e composição **“1 ON E 2 PNA”**. BPAC11 falta no índice, mas registra **1.695.828 negócios** no período. A ligação corretiva com BPAC11 precisa de evidência oficial e proveniência. Opções: correção pela tabela autorizada, item próprio para o índice, ou exclusão provisória expressamente aprovada — sempre registrada como lacuna.

## 5. Não verificado

- As explicações causais de emissões, recompras e conversões na tabela de sensibilidade; a própria ficha as identifica como hipóteses.
- Os demais resultados antigos de ROE/VPA da seção 6 e a distribuição de 38 razões do F2A-3.
- Todas as frações das carteiras dos FIIs e todos os motivos cadastrais individuais.
- Implementação futura, testes e mutation score do F2A-36/37; esta auditoria não executou a suíte.

## 6. Perguntas para o Marcos

1. Qual faixa aprovar, e qual tratamento dar ao divulgado quando a escala é indeterminada?
2. Como tratar controladora zerada, mantendo a distinção entre zero e linha ausente?
3. A escala pode vir de outro documento? Com quais evidências?
4. Divulgado incoerente pode receber o tratamento de ausente? Como tratar linhas conflitantes?
5. Aprovar o critério de atual, os sucessores, o escopo por companhia e a exclusão provisória do BTG?

**Veredito: não pode seguir para F2A-36/37 até corrigir os achados bloqueantes e registrar as decisões do Marcos.**

## Decisões do Marcos (13/10/2026) e resposta na versão 0.2

- **Bloqueio 1** (base da faixa): a ficha passa a dizer que 49 dos 255 casos do F2A-16 usam o lucro total (`controladores or total`).
- **Bloqueio 2** (divulgado incoerente tratado como ausente): decidido que o LPA da espécie se abstém, com alerta, sem recalculado (ficha 7.5; ADR-0003, "Revisões").
- **7.1:** faixa [0,1; 10] mantida; escala indeterminada não derruba o LPA divulgado (revisão da regra 1 da D19).
- **7.2:** lucro total só sem não controladores no balanço; KLBN11 passa a se abster no lucro dos controladores.
- **7.4:** escala só de outra espécie do mesmo documento.
- **Ressalvas:** QUAL3 descrita como conflito de linhas; métrica `|log(razão)|` escrita; 8,5815; arquivo identificado por SHA-256 e data de coleta de 1/10/2026; afirmação sobre o lucro dos minoritários da KLBN11 ajustada.
- **Universo:** critério de "atual" aprovado como operacional; AZUL3, AXIA3 e NATU3 incluídos (NATU3 como emissor novo); um ticker por companhia, exceto o Banrisul (BRSR3, BRSR5, BRSR6); BTG em exclusão provisória até o F2A-39. Total: 78 atuais + 12 históricos.
