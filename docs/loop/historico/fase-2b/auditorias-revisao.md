# Auditorias da revisão da 2B (18/10/2026)

Relatórios finais do Codex (`scripts/auditar.py`, sandbox só de leitura), na ordem em que rodaram. Cada rodada foi conferida pelo Claude no código e corrigida com decisões do Marcos do mesmo dia (commits `f5fd081`, `2ca4bc9`, `d16fde5` e o da aprovação).

## Rodada 1 — Ficha por ação 1.1 — modo FICHA

**Modo FICHA.** Escopo: `docs/metodologia/por-acao.md`, versão 1.1, branch `main`, HEAD `f5fd081`; diff contra a versão 1.0. Somente leitura, sem rede, sem importar módulos do projeto e sem alterações no repositório.

Há **três bloqueios**: a proteção matemática alegada em 7.7 é falsa; a recuperação das nove companhias não ocorre pela regra escrita; e o exemplo do BBAS3 depende de uma linha diferente da autorizada em 7.8.

### 1. Fórmula e referência

- **ressalva** — `docs/metodologia/por-acao.md:24`: CPC 41/IAS 33, §§9–20, 66 e A13–A14 sustentam lucro atribuível, média ponderada e tratamento dos direitos de participação; não demonstram que uma linha genérica “PN” corresponde necessariamente a todas as classes. **Fechar:** distinguir a definição normativa da aproximação aprovada em 7.9, declarando sua limitação.

As fórmulas dos exemplos preservam corretamente **controladores × consolidado**, **por ação × total** e **ação componente × unit**. O recalculado está identificado como aproximação, sem equivalência indevida ao LPA básico normativo.

### 2. Insumos

- **ressalva** — `docs/metodologia/por-acao.md:34`: a definição de PL lista apenas 2.03/2.03.09, embora a tabela versionada contemple bancos com 2.07/2.07.02 e 2.08/2.08.09. **Fechar:** descrever o PL pelo par código/descrição de cada modelo, como já acontece com o lucro.
- **ressalva** — `docs/metodologia/por-acao.md:32`: a tabela identifica DFP/ITR, mas nomeia somente o arquivo DFP e usa `DT_REFER` como referência do LPA. Para fluxos, isso não distingue trimestre de acumulado. **Fechar:** incluir o arquivo ITR, `DT_INI_EXERC`, `DT_FIM_EXERC` e `ORDEM_EXERC` na identificação do período.

Não encontrei conversão percentual/razão nesses insumos. LPA é R$/ação; lucro e PL recebem a escala monetária; quantidades de ações têm escala própria.

### 3. Regime, janela e data

- **ressalva** — `docs/metodologia/por-acao.md:44`: “não há regime real ou nominal” confunde ausência de desconto com regime monetário. Os valores utilizados são reais correntes, sem deflação. **Fechar:** declarar valores monetários nominais, sem atualização inflacionária.
- **ressalva** — `docs/metodologia/por-acao.md:46`: preço D-1 e quantidade da demonstração podem estar separados por desdobramento, grupamento ou bonificação; falta a regra operacional de compatibilização ou abstenção. O ADR-0002, D5, exige tratar esses eventos; CPC 41/IAS 33, §§26 e 64, trata ajustes retrospectivos do denominador/LPA. **Fechar:** explicitar a limitação e o comportamento até existir tratamento de eventos.

### 4. Hipóteses e inaplicabilidade

- **bloqueia** — `docs/metodologia/por-acao.md:52`, `:61`, `:68`: a lista não define integralmente o tratamento de LPA zero ou não finito, quantidades individuais negativas/não finitas, tesouraria superior ao capital e composição de unit com quantidade inválida. A proibição de valor inválido está escrita para **reservas dos controladores**, sem alcance inequívoco sobre todos os insumos. **Fechar:** completar as regras por insumo e por saída, incluindo distinção entre zero econômico e preenchimento sem informação; nenhum inválido pode autorizar reserva.
- **ressalva** — `docs/metodologia/por-acao.md:58`: PL ≤ 0 determina abstenção do ROE, mas não esclarece se VPA negativo é preservado como dado ou abstido. **Fechar:** separar validade do dado contábil da aplicabilidade dos métodos; prejuízo e PL negativo não podem virar ausência seguida de substituição favorável.
- **ressalva** — `docs/metodologia/por-acao.md:59`: “até o F2A-9” ficou desatualizado: esse item já foi entregue, inclusive com VPA bancário registrado em `docs/loop/historico/fase-2a/diario.md:545`. **Fechar:** atualizar a regra vigente para bancos.

**Casos reais do universo:**

| Família | Cobertura e lacuna |
|---|---|
| Bancos | Contas distintas reconhecidas, mas definição de PL desatualizada e BBAS3 bloqueado em 7.8. |
| Seguradoras | Há códigos específicos e QUAL3 como conflito de linhas; falta exemplo independente de seguradora operacional. QUAL3 é corretora. |
| Holdings | CSAN3 evidencia minoritários e prejuízo; a explicação causal das divergências continua assumidamente não verificada. |
| Units | TAEE11 e KLBN11 têm contas reproduzíveis; falta exemplo com LPAs diferentes entre componentes e com classe PNA. |
| Preferenciais | Banrisul cobre classes explicitamente divulgadas; USIM5 cobre o novo uso da PN genérica, com limitação de identificação. |
| Empresas com prejuízo | CSAN3, GOLL4 e USIM5 aparecem; falta política completa para zero e preservação de valores negativos. |
| FIIs de papel e tijolo | KNCR11/MXRF11 e HGLG11/XPML11 não são cobertos: faltam fonte, denominador e regras por cota. Isso pode ser escopo de outra ficha, mas a exclusão precisa ser explícita. |

### 5. Exemplo independente

- **ressalva** — `docs/metodologia/por-acao.md:81`: o ZIP citado pelo hash `336a92…` não coincide com os dois artefatos locais examinados. Os dados principais de Petrobras e Taesa coincidem, mas isso não autentica o snapshot original. **Fechar:** preservar ou localizar o artefato citado, ou documentar a reprodução em snapshot identificado.
- **ressalva** — `docs/metodologia/por-acao.md:126`: os exemplos dão valores esperados independentes para Petrobras e Taesa, mas não especificam os resultados dos quatro caminhos novos da versão 1.1. **Fechar:** acrescentar entradas identificadas, resultado esperado, origem/proveniência e abstenções para 7.7–7.10; definir precisão ou tolerância.

**D21:** os seis componentes existem formalmente. Faltam, para sua completude material nesta revisão: regras de domínio dos insumos; regime nominal explícito; exemplos verificáveis dos novos caminhos, sobretudo 7.8; e sensibilidade correta da nova inferência. A aprovação da versão 1.1 permanece pendente, corretamente declarada.

### 6. Sensibilidade

- **ressalva** — `docs/metodologia/por-acao.md:130`: a tabela não incorpora o risco introduzido por 7.7 nem o efeito de atribuir PN genérica a classes distintas. **Fechar:** acrescentar os contraexemplos de escala abaixo e distinguir número divulgado de atribuição inferida à classe.

### 7.1 a 7.6 — decisões anteriores

Sem novo achado sobre as escolhas registradas; a faixa e as reservas permanecem políticas aprovadas, com limitações declaradas.

### 7.7 — Escala pelo lucro consolidado

- **bloqueia** — `docs/metodologia/por-acao.md:201`: é falsa a alegação de que a faixa recusaria a distorção depois da escolha errada. Se a razão na escala verdadeira for **1.000**, a hipótese errada produz **1**, vence pela distância logarítmica e passa em `[0,1; 10]`. **Fechar:** corrigir a demonstração, declarar que a faixa não garante a escala e registrar a aceitação desse risco ou exigir evidência adicional.
- **bloqueia** — `docs/metodologia/por-acao.md:206`: “VPA e capitalização de volta nas 9 companhias” não decorre da regra. Confirmei nove casos de controladores zerados com minoritários no balanço, mas **Cataguases não traz LPA básico por espécie e Aliperti traz ON/PN zerados**. **Fechar:** separar população candidata de população recuperável e registrar os resultados e motivos por companhia.
- **ressalva** — `docs/metodologia/por-acao.md:198`, `:203`: a razão não depende apenas de `f = consolidado/controladores`; incorpora ações finais contra média ponderada e direitos de classe. Quando os controladores se abstêm, `f` nem é observável no documento. **Fechar:** qualificar a demonstração como hipótese simplificada, sem garantia econômica.

### 7.8 — LPA agregado de espécie única

- **bloqueia** — `docs/metodologia/por-acao.md:212`, `:217`: no BBAS3, DFP 2025 versão 1, **3.99.01 = 0**, enquanto **3.99 = 2,40**. A regra autoriza somente 3.99.01; portanto não entrega o LPA/escala/VPA prometidos. Isso já consta em `docs/decisoes/fontes-fase2a.md:33`. **Fechar:** corrigir o efeito anunciado ou decidir explicitamente se e quando 3.99 pode representar LPA básico, com evidência independente da natureza desse valor.

O CPC 41, §66, fundamenta a apresentação por classe; não determina que qualquer valor na linha superior 3.99 seja básico.

### 7.9 — PN única para várias classes

- **ressalva** — `docs/metodologia/por-acao.md:224`, `:226`: a aplicação a todas as classes é decisão registrada do Marcos, mas a expressão “é o LPA divulgado de cada classe” excede a evidência: o CSV divulga “PN”, sem discriminar PNA/PNB. **Fechar:** apresentar como atribuição aceita à classe, com marca e limitação, mantendo a referência aos direitos distintos do CPC 41, §66 e A13–A14.
- **ressalva** — `docs/metodologia/por-acao.md:226`: falta esclarecer se uma linha específica presente e incoerente impede recorrer à PN genérica. **Fechar:** explicitar a precedência de 7.5, evitando substituir divulgado rejeitado por outro valor.

### 7.10 — Correção da espécie

- **ressalva** — `docs/metodologia/por-acao.md:236`: as duas evidências confirmam a contradição da MGLU3, mas falta delimitar a vigência temporal da correção entre DFP e FCA. **Fechar:** registrar documentos, versões e intervalo de aplicação; não estender uma correção atual automaticamente ao histórico.

A exigência de correção manual, com duas evidências e proveniência, está escrita e foi decidida pelo Marcos.

### Recalculado por mim

Usei somente biblioteca padrão (`zipfile`, `csv`, `Decimal`), leitura direta dos CSVs e fórmulas da ficha, sem chamar seus calculadores. DFP: referência 2025-12-31, versão identificada, exercício ÚLTIMO; conferi códigos e descrições.

| Caso | Conta independente | Resultado |
|---|---|---:|
| Petrobras | `110.129.000.000 / 12.888.732.761` | LPA recalculado **8,5445948832** |
| Petrobras | `415.786.000.000 / 12.888.732.761` | VPA **32,2596493938** |
| Taesa | `1.579.863.000 / 1.033.497.000` | LPA recalculado **1,5286575578** |
| TAEE11 | `1,52866 × (1 + 2)` | LPA divulgado composto **4,58598** |
| TAEE11 | `7.608.982.000 / 1.033.497.000 × 3` | VPA **22,0870945924** |
| Klabin | `6.241.478.850 − 106.051.185` | **6.135.427.665 ações** |
| Klabin | `1.678.211.000 / ações / 0,2286` | razão **1,1965352489** |
| KLBN11 | `(14.401.101 − 6.515.155) × 1.000 / ações × 5` | VPA **6,4265658652** |
| KLBN11 | `0,2286 × (1 + 4)` | LPA **1,1430** |
| MGLU3 | `204.603.000 / (775.945.010 − 1.343.449)` | recalculado **0,2641396691**, contra divulgado ON **0,264** |
| USIM5 | linha PN básica, aplicada conforme 7.9 | **−2,50**, preservando o prejuízo |

No FCA local confirmei: BBAS3 somente ON; Pine com ON e PN; USIM5 PNA e USIM6 PNB; MGLU3 cadastrada como PNA apesar de capital somente ON e DRE somente ON.

**Nove candidatos de 7.7:** sete têm razão calculável dentro da faixa — Sul 116 **0,532028**, Lifemed **0,162422**, Cantu **0,972325**, VLI **2,067460**, Cambuci **0,999998**, Mundial **1,000000**, Klabin **1,196535**. Cataguases e Aliperti continuam sem LPA por espécie utilizável. Isso reproduz a aplicação proposta, não comprova externamente a escala verdadeira.

**Contraexemplo de 7.7:** para ações verdadeiramente em unidades, razões verdadeiras entre **100 e 10.000** tornam a hipótese errada em milhares aceita, com razão entre **0,1 e 10**. A faixa separa candidatos próximos; não elimina erros grandes nos insumos.

### Não verificado

- Texto integral das normas e autenticidade externa dos arquivos: sem rede, conforme solicitado. As referências normativas acima identificam o fundamento; não houve nova consulta aos documentos oficiais.
- Snapshot original com hash `336a92…`. O ZIP atual tem SHA-256 `9fa640…`, coleta registrada em 13/10/2026; o cache do levantamento tem `d7aec5…`.
- Escala verdadeira das sete candidatas de 7.7 por evidência externa à inferência.
- Implementação futura, suíte, mutation score e conversão dos novos exemplos em testes. Não executei testes nesta auditoria documental.
- Causas econômicas das divergências históricas e cobertura contábil completa de seguradoras e FIIs.

### Perguntas para o Marcos

1. **7.7:** manter a inferência como aproximação com risco explícito, ou exigir confirmação adicional antes de liberar VPA/capitalização? O dado separador é uma quantidade de ações com escala comprovada independentemente do quociente lucro/LPA.
2. **7.8:** manter somente 3.99.01 e corrigir a promessa sobre BBAS3, ou admitir 3.99 sob condição documentada? O dado separador é a divulgação da companhia que identifique R$ 2,40 como LPA **básico**, período e classe.
3. **7.9:** manter a extensão como aproximação declarada, ou exigir evidência dos direitos/resultados por classe? O dado separador é a nota de resultado por ação e a distribuição do resultado entre PNA/PNB.
4. **Domínio e escopo:** preservar zero/prejuízo/PL negativo como dados e deixar cada lente decidir sua aplicabilidade? Excluir explicitamente FIIs desta ficha ou acrescentar regras por cota? Essas escolhas ainda não estão completas no texto.

As quatro decisões de 18/10 estão registradas; não as atribuo ao autor da ficha. Permanecem abertas as condições acima e a aceitação do risco que a justificativa matemática ocultava.

**Veredito: não pode seguir para aprovação da versão 1.1 enquanto os bloqueios não forem resolvidos ou expressamente dispensados pelo Marcos.**

## Rodada 1 — Proposta da 2B — modo DOCUMENTO

**Modo DOCUMENTO.** Auditoria de `docs/loop/fila-fase2b-proposta.md`, na `main` em `f5fd081`. Somente leitura, sem rede e sem alterações.

As nove regressões abertas da 2A têm destino explícito. A proposta também retirou os itens já resolvidos no fechamento e corrigiu os principais problemas estruturais da versão anterior. Persistem três bloqueios de execução.

Nas referências abaixo, **proposta** significa `docs/loop/fila-fase2b-proposta.md`.

**Cabeçalho, ativação e regras gerais**

- **ressalva** — `proposta:10`: o comando apresentado como limpeza do cache não funciona como escrito. `scripts/invalidar_cache_cvm.py:38` exige tickers; sem `--aplicar`, apenas simula (`:40–44`). **Fecha com:** comando operacional completo, distinguindo conferência e aplicação.
- **ressalva** — `proposta:80`: restringe `tests/regressao/` ao F2B-36, F2B-43 e retirada de marcas, enquanto `proposta:46` exige registrar bugs novos no item em que aparecem. F2B-18, F2B-20 e F2B-45 nomeiam testes fora desse diretório. **Fecha com:** autorização explícita para criar e registrar a regressão em cada `fix:`, identificando o teste cuja marca será retirada.
- Golden: sem achado adicional. Conferi os 2.079 registros atuais: nenhum contém `setor`, `liquidez` ou classe com espaços. Isso sustenta a premissa de inclusões dos dois gates, nas condições atuais.

**F2B-35**

Sem achado adicional: a sincronização documental cobre as divergências citadas no fechamento.

**F2B-36**

Sem achado adicional: registra os dois problemas do IF.data e dá destino nominal aos BUG-2A-10 a 18.

**F2B-7**

Sem achado adicional na decisão de mover os números; a propriedade preservada e sua injeção de taxa precisarão aparecer concretamente no diff.

**F2B-8**

Sem achado adicional: corrige o BUG-2A-01, com regressão identificada e decisão explícita sobre valores não positivos.

**F2B-10**

Sem achado adicional, condicionado à aprovação da ficha 1.1.

**F2B-11**

Sem achado adicional, condicionado à aprovação da ficha 1.1.

**F2B-12**

Sem achado adicional, condicionado à aprovação da ficha 1.1; contempla também a perda de PNA na composição da unit.

**F2B-13**

Sem achado adicional: exige evidência e proveniência da correção de espécie.

**F2B-14**

Sem achado adicional: identifica a regressão do divulgado anterior ao filtro de coerência.

**F2B-16**

Sem achado adicional: contempla a identidade tautológica e o confronto entre fontes, com limiar decidido.

**F2B-17**

Sem achado adicional: distingue cobertura de companhias, referência oficial e Informe Mensal.

**F2B-18**

Ressalva de regressão já registrada nas regras gerais; nenhum achado adicional.

**F2B-20**

Ressalva de regressão já registrada nas regras gerais; o predicado do golden corresponde à mudança descrita.

**F2B-37**

Sem achado adicional: a política anual dos controladores passa a valer em cada documento do TTM.

**F2B-38**

Sem achado adicional: correção e regressão do desempate por versão estão identificadas.

**F2B-39**

Sem achado adicional: preserva a conversão única e impede sobrescrever DY válido com valor fora da faixa.

**F2B-40**

Sem achado adicional: cobre ZIP vazio e sua consequência no cache.

**F2B-41**

Sem achado adicional: a exceção à ficha está expressamente registrada como decisão do Marcos.

**F2B-42**

Sem achado adicional: mesma exceção explícita, com regressão identificada.

**F2B-21**

- **ressalva** — `docs/loop/historico/fase-2a/auditoria-externa.md:36` exige conferir `GRUPO_DFP` **e** `VERSAO`; `proposta:424` retoma apenas versão. `cvm_provider.py:418–424` lê `DRE_con`, mas não confere `GRUPO_DFP`. Isso pode ser suficiente pelo contrato do arquivo, porém a alegação anterior continua sem confirmação ou refutação explícita. **Fecha com:** incluir a conferência do grupo e registrar a evidência que encerra essa ressalva.
- **ressalva** — `proposta:406` especifica a matriz com g convertido por Fisher, mas as fichas devem comparar três definições de g (`:462`), e a última seção promete que a matriz mostrará seus efeitos (`:873`). **Fecha com:** exigir no levantamento a comparação das definições candidatas, além da comparação dos regimes.

**F2B-43**

Sem achado adicional: exige reprodução antes de registrar xfail e preserva a decisão de destino para o Marcos.

**F2B-22**

Sem achado adicional: parâmetros permanecem sujeitos à decisão e à ficha.

**F2B-23**

Sem achado adicional: a definição de crescimento deixou de ser uma escolha implícita do texto.

**F2B-24**

Sem achado adicional: as quatro alternativas do Bazin permanecem abertas.

**F2B-25**

Sem achado adicional na estrutura; a justificativa econômica do DY contra taxa real permanece trabalho obrigatório da ficha.

**F2B-26**

Sem achado adicional na exigência de derivação; equivalência algébrica por Fisher não demonstra, sozinha, a adequação econômica de deflacionar ROE contábil.

**F2B-28**

Sem achado adicional: a base não determinada bloqueia o item, e o dado permanece sem consumidor.

**Marcador “Fichas da 2B, taxa e fontes”**

Sem achado adicional na ordem: precede o provedor cujos nomes dependem da decisão e todos os consumidores das fichas novas.

**F2B-27**

Sem achado adicional: inclui contrato, cache e proveniência, sem escolher vértice.

**F2B-29**

Sem achado adicional: contrato aditivo, sem consumidor e sem alteração de testes existentes.

**F2B-30**

Sem achado adicional na proposta: seleção, defasagem, inflação e proveniência dependem da ficha aprovada.

**F2B-1**

Sem achado adicional, condicionado à ficha; a implementação deverá acompanhar a definição de g escolhida, inclusive nos testes hoje nomeados pela conversão do crescimento nominal.

**F2B-31**

Sem achado adicional: sai da fila se a decisão dispensar a troca de taxa.

**F2B-2**

- **bloqueia** — `proposta:895` permite retirar os pontos de P/VP do score, mas `proposta:65` e `:616` autorizam mudar somente o benchmark do teste da seção B. Esse teste exige `score_final` maior para o menor P/VP (`tests/test_financeiro_pre_refactor.py:141`). Retirar os pontos torna essa asserção incompatível com a decisão. **Fecha com:** prever no marcador a alteração dessa asserção caso os pontos sejam retirados, com justificativa e preservação do teste de igualdade do preço justo.

**F2A-39**

Sem achado adicional: a ligação depende de evidência oficial aceita, sem repetir a ligação indireta anteriormente recusada.

**F2B-4**

- **bloqueia** — `proposta:646` cria versões novas dos seis métodos e novas abstenções por escopo. A D21 exige ficha antes de qualquer versão nova (`docs/adr/0003-validade-dados-metodo-auditoria.md:71`). A fila prepara fichas para Gordon, Bazin e rendimento de FII, mas nenhuma para Graham, Lynch e `FiiNav`. A exceção de `proposta:101` cobre exclusivamente F2B-41 e F2B-42. **Fecha com:** fichas aprovadas para os métodos restantes ou dispensa explícita do Marcos, delimitada à aplicação do escopo.

**F2B-44**

Sem achado adicional: tem destino, regressões e contrato; precede o consumidor bancário.

**F2B-3**

Sem achado adicional: acrescenta a lente sem conectá-la ao motor.

**F2B-32**

Sem achado adicional: depende da lente e das fontes aprovadas; o predicado deverá incorporar os setores efetivamente escolhidos.

**F2A-10**

- **bloqueia** — `proposta:708` distingue listagem recente de ausência de negócios, mas `:709` manda a função receber somente o bloco de liquidez e a regra. O bloco atual contém métricas, data final, fonte e meses ausentes (`sentinela/data/liquidez.py:76–80`); não contém data de listagem. Sem cotações do ticker, devolve apenas abstenção (`:60–61`). Logo, o insumo especificado não permite distinguir uma estreia recente de uma suspensão ou ausência de negociação. **Fecha com:** fonte e transporte da data de início de negociação, tratamento de data desconhecida e teste que diferencie estreia de primeiro negócio observado após suspensão.

**F2B-33**

Sem achado adicional: sincronização posterior ao comportamento implementado.

**F2B-34**

Sem achado adicional: a proposta seguinte deverá incorporar também os destinos decididos para a pergunta 8 do levantamento.

**F2B-45**

Ressalva de regressão já registrada nas regras gerais; a mudança de comportamento foi corretamente separada da limpeza.

**F2B-5**

Sem achado adicional: retirou a regeneração do golden e explicitou as exceções dos scripts históricos.

**F2B-6 e decisão final**

Sem achado adicional no arquivamento. A limpeza efetiva do cache, os relatórios reais e o fechamento permanecem ações futuras verificáveis.

**Riscos e decisões**

- **ressalva** — `proposta:910` apresenta `[CACHE]` com alternativa, mas o marcador intermediário (`:519–526`) não pede essa decisão; F2B-5 já determina remover o script. **Fecha com:** declarar que a aprovação decide a limpeza integral, ou incluir `[CACHE]` no marcador e condicionar a remoção ao resultado.
- As escolhas de ativação já registradas foram tratadas como decisões existentes, sem reabri-las nesta auditoria.

**Recalculado por mim**

Para o exemplo de `proposta:868–870`, usando diretamente as fórmulas:

| Grandeza | Resultado |
|---|---:|
| g nominal = 12% × 40% | 4,8% |
| g real pela opção (i) | −0,663507% |
| k nominal por Fisher | 18,16% |
| Gordon pela opção (i) | R$ 47,065868 |
| ROE real por Fisher | 6,161137% |
| g real pela opção (ii) | 2,464455% |
| Gordon pela opção (ii) | R$ 64,473161 |
| Diferença entre valores | +36,984960% |

Os arredondamentos apresentados conferem. A diferença vem de hipóteses de crescimento distintas.

Também conferi a identidade da lente de bancos: converter ROE, g e k pelo mesmo fator de Fisher preserva `(ROE − g)/(k − g)`. Isso verifica a álgebra, sem validar a hipótese econômica.

**Não verificado**

- A suíte não iniciou: `FileNotFoundError: No usable temporary directory found`. O sandbox é integralmente somente leitura.
- Ruff: o comando original tentou gravar cache; repetido com `--no-cache`, **passou** para `E9,F63,F7,F82`.
- Não executei rede, mutmut, geração do golden, limpeza de cache ou comandos de auditoria que gravam relatórios.
- Não certifiquei nesta auditoria a ficha 1.1 nem os arquivos oficiais e contagens dos levantamentos. Sua aprovação permanece condição de ativação.
- Os testes futuros nomeados nos itens ainda serão criados; sua existência na proposta não demonstra que o aceite já passa.
- Não identifiquei repetição dos F2A-41 a 44 nos itens remanescentes.

**Perguntas para o Marcos**

1. **Escopo e D21:** criar fichas para Graham, Lynch e `FiiNav`, ou dispensar ficha exclusivamente para o gate de escopo? O dado que separa as opções é o diff pretendido: apenas restrição de público ou alteração adicional de insumo/regra.
2. **P/VP no score de FII:** manter os pontos ou retirá-los? A ficha deve mostrar o efeito de cada opção sobre score e classificação; retirar exige liberar a asserção identificada no F2B-2.
3. **Listagem recente:** usar data oficial de início de negociação ou primeira negociação observada como aproximação declarada? Compare estreias, suspensões e mudanças de código; o COTAHIST da janela, sozinho, não distingue esses casos.
4. **Cache:** aprovar limpeza integral e remoção do script, ou preservar invalidação seletiva? A diferença é apagar todos os fundamentos armazenados ou somente os registros afetados.
5. **Decisões já previstas para o meio da fase:** permanecem pendentes g real, vértice, lado da taxa, inflação, defasagem, taxa do Bazin, definição/janela do spread, fonte do DY, benchmark do score, financeiras e BTG. As opções estão registradas; a matriz do F2B-21 precisa efetivamente produzir os dados que permitam compará-las.

**Veredito: não pode seguir — corrigir os três bloqueios antes da ativação.**

## Rodada 2 — Ficha por ação 1.1 — modo FICHA

**Modo FICHA — segunda rodada da versão 1.1**, `docs/metodologia/por-acao.md`, na `main`, commit `2ca4bc9`. Auditoria somente de leitura, sem rede e sem importar o código do projeto nas contas.

Os três bloqueios anteriores receberam correções pertinentes: a faixa deixou de ser apresentada como garantia; as sete companhias passaram a ser candidatas sujeitas à confirmação; e o BBAS3 passou a usar explicitamente a 3.99, com conferência. As contas conferem. Ainda há lacunas que impedem considerar a especificação fechada.

### 1. Fórmula e referência

Sem novo achado: a ficha distingue o LPA normativo da aproximação pelo capital no fim do período e declara as aproximações adicionais das decisões 7.8 e 7.9.

### 2. Insumos

- **Ressalva** — `docs/metodologia/por-acao.md:40`: o novo insumo `sharesOutstanding` tem data da consulta, mas falta exigir o registro do valor e da resposta utilizada, com fonte e hash, para reproduzir a confirmação. **Fecha com:** requisito explícito de proveniência conforme D16, inclusive quando a consulta falhar.

### 3. Regime, janela e data

- **Ressalva** — `docs/metodologia/por-acao.md:49`: distinguir trimestre e acumulado pelo `DT_INI_EXERC` corrige a identificação, mas não determina qual período entra na razão de escala quando ambos existem. **Fecha com:** regra de seleção e exigência de que lucro e LPA comparados tenham exatamente o mesmo intervalo.
- Valores nominais, escala monetária e limitação por eventos societários estão agora declarados. A ficha não mistura taxa real com nominal; não contém desconto.

### 4. Hipóteses e inaplicabilidade

- **Bloqueia** — `docs/metodologia/por-acao.md:76`: a reserva para **lucro dos controladores ausente** ainda exige apenas ausência ou zero dos não controladores na DRE. Assim, permite usar o consolidado mesmo com minoritários no balanço — exatamente o **BUG-2A-03**, registrado como corrigido em `tests/regressao/README.md`. **Fecha com:** exigir também a conferência dos minoritários no balanço nesse ramo, alinhando ficha, D20 e regressão existente.
- **Ressalva** — `docs/metodologia/por-acao.md:67`: a regra geral manda abster diante de insumo inválido, mas o primeiro subitem permite descartar uma linha de LPA não finita e usar outra válida da mesma espécie. **Fecha com:** explicitar se essa é uma exceção deliberada e definir sua precedência sobre a regra de linhas conflitantes.
- **Ressalva** — `docs/metodologia/por-acao.md:69`: faltam regras explícitas para coluna de ações ausente, quantidade fracionária e divergência entre tesouraria total e a soma das tesourarias por espécie. Para preço e quantidade do yfinance, tampouco há regra expressa para zero e negativo. **Fecha com:** completar esses domínios e seus motivos de abstenção.

Os itens 11–13 fecham os pontos anteriores sobre zero, prejuízo, PL/VPA negativos e exclusão dos FIIs. Porém, “zero é não informado” continua sendo uma política de leitura; não demonstra que todo zero econômico seja impossível.

### 5. Exemplo independente

- **Ressalva** — `docs/metodologia/por-acao.md:147`: o caso KLBN11 permite testar a aritmética, mas não a nova condição de liberação da 7.7: falta o valor registrado do yfinance e o resultado esperado da confirmação. **Fecha com:** acrescentar esse insumo com proveniência e um caso de recusa.
- **Ressalva** — `docs/metodologia/por-acao.md:150`: o BBAS3 ainda apresenta “razão 1,000 (F2A-3)” sem os operandos. **Fecha com:** registrar lucro dos controladores, capital, tesouraria e razão sem arredondamento prematuro; cálculo abaixo.

A seção 5.3 fornece valores esperados independentes para a aritmética e para as atribuições de USIM5/MGLU3. Ainda não fornece um teste completo da confirmação pelo yfinance.

### 6. Sensibilidade

- **Ressalva** — `docs/metodologia/por-acao.md:163`: “com a confirmação pelo yfinance, o caso se abstém” é categórico demais sem hipótese sobre a correção e a comparabilidade desse segundo dado. **Fecha com:** declarar essas condições e mostrar a sensibilidade nos dois sentidos do erro de escala.

### 7. Parâmetros e justificativa

**7.1–7.6:** sem novo achado, além da reserva inconsistente apontada na seção 4.

**7.7:**

- **Bloqueia** — `docs/metodologia/por-acao.md:230`: “a menos de 10 vezes” não define uma comparação reproduzível nos dois sentidos. A referência à divergência existente não resolve: ela usa `yfinance/CVM − 1`, enquanto uma confirmação por fator normalmente exige limites inferior e superior. **Fecha com:** escrever a desigualdade, os limites inclusivos/exclusivos, a quantidade comparada por espécie/unit e o tratamento de valores inválidos. Uma comparação unilateral pode aceitar justamente um dos erros de fator 1.000.
- **Ressalva** — `docs/metodologia/por-acao.md:230`: “diferenças de espécie ou de unit ficam abaixo de 10” não está demonstrado como propriedade geral. **Fecha com:** limitar a afirmação aos casos efetivamente medidos ou apresentá-la como hipótese aceita, com abstenção quando a comparabilidade não puder ser estabelecida.

A correção das **sete candidatas** está confirmada: reproduzi as razões publicadas; Cataguases e Aliperti continuam sem denominador de LPA utilizável.

**7.8:** o bloqueio anterior do BBAS3 está fechado no conteúdo: 3.99.01 é zero, 3.99 é 2,40 e a conferência independente passa. A aproximação está declarada; a conferência de 10% não prova que o título seja necessariamente LPA básico.

**7.9:** sem novo achado: a atribuição da PN à PNA/PNB está declarada como aproximação, com precedência da linha específica e sem resgatar linha específica incoerente.

**7.10:** sem novo achado: confirmei o FCA classificando MGLU3 como PNA, enquanto a Composição do Capital e a DRE da DFP apresentam ON. A correção permanece individual, documentada e limitada aos documentos citados.

**Coerência com o ADR:**

- **Ressalva** — `docs/adr/0003-validade-dados-metodo-auditoria.md:37` e `:51`, contra `por-acao.md:230` e `:255`: a D19 ainda diz que yfinance nunca motiva abstenção e que, nas classes distintas, vale somente o divulgado da classe. As novas exceções não constam nas “Revisões”. **Fecha com:** registrar a revisão expressa da D19 ao aprovar a 1.1.

**D21:** as seis partes exigidas existem. Falta completar a definição operacional do novo insumo e de sua confirmação, os domínios indicados e o exemplo completo da 7.7. A aprovação da versão 1.1 segue pendente, corretamente indicada no status.

**Casos reais:** bancos são tratados por modelo, com BBAS3 e abstenção do Pine; holdings e prejuízo aparecem em CSAN3; units em TAEE11/KLBN11; classes em USIM5 e Banrisul. Seguradoras têm mapeamento de insumos, mas não exemplo numérico — e não há seguradora explicitamente selecionada no universo inicial. FIIs de papel, como KNCR11, e de tijolo, como HGLG11, estão expressamente fora desta ficha, remetidos à ficha de FII.

### Recalculado por mim

Método: leitura dos CSVs locais com `zipfile` e `csv`, filtrando demonstração consolidada, exercício ÚLTIMO e versão; contas com `Decimal`, sem funções do projeto.

| Caso | Conta independente | Resultado |
|---|---|---:|
| KLBN11 — ações | 6.241.478.850 − 106.051.185 | **6.135.427.665** |
| KLBN11 — razão | 1.678.211.000 ÷ 6.135.427.665 ÷ 0,2286 | **1,196535248870** |
| KLBN11 — VPA da unit | (14.401.101 − 6.515.155) × 1.000 ÷ 6.135.427.665 × 5 | **6,426565865152** |
| BBAS3 — recalculado | 13.698.124.000 ÷ (5.730.834.040 − 22.370.399) | **2,399616580128** |
| BBAS3 — razão contra 3.99 | 2,399616580128 ÷ 2,40 | **0,999840241720** |
| MGLU3 — recalculado | 204.603.000 ÷ (775.945.010 − 1.343.449) | **0,264139669091** |

BBAS3 diverge **−0,0159758%** de 2,40: passa no limite de 10%. USIM5: confirmei a linha básica PN de **−2,50** e a classe PNA no FCA.

Razões das sete candidatas: Sul 116 **0,53202833**; Lifemed **0,16242208**; Cantu **0,97232514**; VLI **2,06745999**; Cambuci **0,99999811**; Mundial **0,99999987**; Klabin **1,19653525**.

### Não verificado

- Confirmações efetivas pelo yfinance: sem consulta de rede e sem valores registrados na seção 5.3.
- Texto integral das normas CPC/IFRS: usei as referências indicadas pela ficha — CPC 41 §§9–10, 19–20, 66 e A13–A14 — sem validação externa nesta rodada.
- Relatório integral da primeira auditoria da **1.1**: o histórico versionado consultado contém as rodadas da 1.0; comparei os pontos solicitados com o diff da revisão.
- Não executei testes ou lint: esta rodada avalia a especificação documental, sem alteração de código.

### Perguntas para o Marcos

1. **Confirmação por fator:** adotar `0,1 < ações_CVM/ações_yfinance < 10`, ou outra desigualdade? O dado que separa as opções são casos de escala errada nos dois sentidos e casos exatamente nos limites.
2. **LPA inválido com outra linha válida:** a linha válida pode sobreviver ou a espécie inteira se abstém? O caso discriminante é uma mesma espécie com uma linha NaN e outra positiva.
3. **ITR:** qual intervalo fornece o par lucro/LPA para a escala: trimestre, acumulado ou ambos com precedência definida? O dado discriminante é um documento com razões diferentes entre esses intervalos.

**Veredito: não pode seguir.**

## Rodada 2 — Proposta da 2B — modo DOCUMENTO

**Modo DOCUMENTO — segunda rodada.** Escopo: `docs/loop/fila-fase2b-proposta.md`, na `main`, HEAD `2ca4bc9`. Auditoria somente leitura, sem rede e sem alterações.

Os três bloqueios anteriores receberam fechamento documental. Encontrei **um bloqueio de processo** e ressalvas de coerência e aceite.

Nas referências abaixo, **P** significa `docs/loop/fila-fase2b-proposta.md`.

### Regras gerais e ativação

- **Bloqueia — P:80:** o texto permite que testes de comportamento permaneçam apenas fora de `tests/regressao/`. Itens como F2B-18, F2B-20 e F2B-45 descrevem problemas confirmados, mas seus aceites não identificam o teste de regressão registrado cuja marca será retirada. Isso conflita com `docs/loop/protocolo.md:62` e `tests/regressao/README.md:9`. **Fecha:** identificar, em cada `fix:`, o teste em `tests/regressao/`, seu ID e a atualização do registro; registrar antes da correção os bugs ainda sem teste.
- As condições de aprovação da ficha 1.1 antes da ativação estão explícitas em P:11. A ficha continua **em revisão**, conforme `docs/metodologia/por-acao.md:3`; isso é uma condição pendente, não uma implementação indevidamente autorizada.
- A separação entre `fix:`, infraestrutura aditiva e limpeza está preservada. Regeneração do golden está restrita aos itens marcados.

### F2B-35

Sem achado adicional: corrige as instruções e explicita a decisão sobre a seção A.

### F2B-36

Sem achado adicional: cobre os novos bugs do IF.data e atribui destino aos BUG-2A-10 a 18.

### F2B-7

- **Ressalva — P:185–192:** “cada número sai de um teste e entra noutro” não basta para garantir que as propriedades preservadas continuarão sendo exercitadas após as mudanças de taxa. **Fecha:** exigir explicitamente que os testes restantes comprovem mediana de três resultados distintos, média de dois e presença do Bazin no limite, independentemente da taxa escolhida; registrar quais testes numéricos recebem F-4, F-5 ou ambos.

### F2B-8

Sem achado adicional: BUG-2A-01 tem teste, retirada da marca e atualização do registro previstos.

### F2B-10

A regra e os números agora correspondem à ficha revista: confirmação pelo yfinance, sete candidatas entre nove companhias e abstenção sem confirmação.

- **Ressalva — P:217–224:** exige a regra também em `series_cvm`, mas não define a data da quantidade do yfinance usada para confirmar cada exercício. Uma quantidade atual pode divergir da histórica por eventos societários. **Fecha:** explicitar o tratamento da série — confirmação contemporânea, abstenção ou reconstrução exploratória declarada — e acrescentar caso com mudança de quantidade entre exercícios.
- **Ressalva — P:219; `docs/adr/0003-validade-dados-metodo-auditoria.md:37`:** a confirmação passa a condicionar a recuperação de VPA e capitalização, enquanto a D19 ainda diz que divergência com yfinance é “alerta, nunca motivo de abstenção”. **Fecha:** registrar no ADR a exceção limitada da decisão 7.7, distinguindo escala ainda não confirmada de quantidade oficial já determinada.

### F2B-11

Sem achado adicional: corresponde à 7.8 revista; a 3.99 só entra com conferência de até 10%, e Pine continua abstido.

### F2B-12

Sem achado adicional: ação avulsa e unit passam a seguir a mesma precedência de classe; preserva a proibição do recalculado comum.

### F2B-13

Sem achado adicional: exige as duas evidências oficiais para corrigir a espécie e mantém a correção visível.

### F2B-14

Sem achado adicional: corrige o BUG-2A-11 com o divulgado já filtrado por coerência.

### F2B-16

Sem achado adicional: comparação entre fontes distintas e limiar de 10% estão explícitos.

### F2B-17

Sem achado adicional: separa cobertura de companhias, cobertura do Informe e indisponibilidade do índice.

### F2B-18

Aplica-se o bloqueio geral de regressão; piso e âmbito da decisão estão explícitos.

### F2B-20

Aplica-se o bloqueio geral de regressão; o predicado do golden corresponde aos dois casos de preço negativo.

### F2B-37

Sem achado adicional: BUG-2A-10 tem destino e teste; a reserva passa a ser aplicada por documento antes da composição do TTM.

### F2B-38

Sem achado adicional: BUG-2A-14 tem correção e retirada da marca previstas.

### F2B-39

Sem achado adicional: BUG-2A-15 tem destino; não introduz outra conversão de percentual.

### F2B-40

Sem achado adicional: BUG-2A-16 tem destino e verificação de cache incompleto.

### F2B-41

Sem achado adicional: dispensa limitada de ficha, versão menor e alteração dos testes conflitantes estão registradas.

### F2B-42

Sem achado adicional: correção limitada à validade do insumo, com teste de regressão identificado.

### F2B-21

A pergunta 8 agora inclui as regras de domínio da ficha 1.1. F2B-10 e F2B-11 antecedem o levantamento, portanto seus dados corrigidos podem alimentar a matriz.

- **Ressalva — P:421:** ainda manda marcar “Banco sem VPA (BBAS3)”, embora F2B-11 já deva ter recuperado o VPA quando a conferência permitir. **Fecha:** medir o estado posterior às correções, marcando somente os bancos que efetivamente permanecerem sem VPA.

### F2B-43

Sem achado adicional: confirmado vira regressão; refutado fica documentado; destino depende do Marcos.

### F2B-22

Sem achado adicional: parâmetros permanecem em decisão, com fonte, sensibilidade e abstenção.

### F2B-23

Sem achado adicional: a definição de crescimento real deixou de ser tomada pelo texto; exige comparação das alternativas.

### F2B-24

Sem achado adicional: apresenta as quatro opções do Bazin e suas consequências.

### F2B-25

Sem achado adicional nesta etapa: a justificativa econômica do DY contra taxa real continua obrigatória na futura auditoria FICHA.

### F2B-26

Sem achado adicional: exige converter também o ROE e verificar a equivalência real/nominal por contas independentes.

### F2B-28

Sem achado adicional: dado aditivo, sem consumidor; representação e base não determinadas bloqueiam a execução.

### Marcador “Fichas da 2B, taxa e fontes”

Sem achado adicional: decisões, auditorias e aprovação antecedem os consumidores.

### F2B-27

Sem achado adicional: foi colocado depois da decisão sobre os nomes dos campos; contrato com recorte real é obrigatório.

### F2B-29

Sem achado adicional: contrato aditivo, conversão por Fisher e golden inalterado.

### F2B-30

Sem achado adicional: taxa indisponível não ganha contingência; proveniência e isolamento do prompt estão previstos.

### F2B-1

Sem achado adicional: fórmula depende da ficha aprovada; testes copiados da V1 são substituídos por referência independente.

### F2B-31

Sem achado adicional: só executa nas opções que retiram a Selic; as outras retiram o item.

### F2B-2 — bloqueio anterior

**Fechado documentalmente:** P:620 permite alterar a asserção do score quando a decisão retirar os pontos de P/VP; P:528 exige confirmação no marcador. A igualdade dos preços justos permanece separada da escolha do score.

### F2A-39

Sem achado adicional: depende de evidência oficial aceita; não repete uma entrega concluída.

### F2B-4 — bloqueio anterior

**Fechado documentalmente:** P:101 e P:650 registram dispensa expressa e limitada de ficha para aplicação do escopo.

- **Ressalva — P:651 contra P:910:** o item determina modelo pelo setor e “sem setor → empresa”, mas a opção (c) de [FINANCEIRAS] determina modelo pela demonstração. **Fecha:** tornar essas instruções condicionais à opção escolhida e exigir a adequação do item no marcador antes de retomá-lo.

### F2B-44

Sem achado adicional: cobre proveniência, instante de referência e resposta vazia do IF.data.

### F2B-3

Sem achado adicional: método novo sem ligação no motor; fórmula, exemplo e abstenções dependem da ficha.

### F2B-32

Sem achado adicional: ligação no motor está separada da criação do método; qualidade bancária fica fora do valor.

### F2A-10 — bloqueio anterior

**Fechado documentalmente:** P:713 elimina a exceção que dependia de uma data de estreia não disponível.

- **Ressalva — P:712–722; `market_engine.py:653`:** uma exceção de coleta hoje retorna sem preencher `liquidez`. O motor não consegue distinguir isso de uma chamada que nunca mede liquidez, para a qual “nada muda”. **Fecha:** exigir teste integrado de falha do coletor pela cascata, comprovando que o aviso chega à saída; um bloco artificial de falha entregue diretamente ao motor não prova esse caminho.

### F2B-33

Sem achado adicional: sincronização documental tem escopo explícito.

### F2B-34

Sem achado adicional: proposta da 2C, sem implementação.

### F2B-45

Aplica-se o bloqueio geral de regressão. A mudança de comportamento foi corretamente retirada do `chore:` de limpeza.

### F2B-5

Sem achado adicional: golden inalterado, remoções condicionais e exceções do `git grep` estão explícitos.

### F2B-6 e decisão final

Sem achado adicional: resumo, arquivamento, auditoria e fechamento seguem o ciclo previsto.

### Recalculado por mim

Com Python padrão, sem importar código do projeto:

| Conta | Resultado |
|---|---:|
| Ações da Klabin | 6.135.427.665 |
| Razão da escala da Klabin | 1,1965352489 |
| VPA da KLBN11 | 6,4265658652 |
| Recalculado da MGLU3 | 0,2641396691 |
| Gordon, alternativa (i) | R$ 47,065868 |
| Gordon, alternativa (ii) | R$ 64,473161 |

Os valores apresentados com duas casas decimais conferem. Para bancos, convertendo ROE, g e k conjuntamente, obtive P/VP idêntico nos dois regimes: **0,5389221557** na alternativa (i) e **0,3876739563** na alternativa (ii).

### Não verificado

- **Suíte:** `python -m pytest -q -p no:cacheprovider` falhou antes da coleta por inexistência de diretório temporário gravável. Não há conclusão sobre testes verdes.
- **Lint:** passou com `RUFF_NO_CACHE=true ruff check --select E9,F63,F7,F82 .`. A execução sem desativar o cache foi impedida pelo filesystem somente leitura.
- Não executei mutmut, geração de golden, downloads ou comandos que alteram banco e índice.
- Não reconferi nesta rodada os números contra os arquivos brutos da CVM nem a confirmação efetiva das sete candidatas pelo yfinance.
- Não localizei relatório versionado específico da primeira auditoria DOCUMENTO desta proposta; conferi os fechamentos indicados pelo pedido contra o texto e o commit `2ca4bc9`.
- Os testes novos ainda não existem; seus aceites foram avaliados como especificações futuras. O parser atual de `golden_diff.py` aceita as variáveis e operações usadas nos predicados.
- Os itens retirados F2B-9, F2B-15 e F2B-19 têm correspondentes concluídos no histórico e no git; não identifiquei repetição deles na fila restante.

### Perguntas para o Marcos

Além das decisões já corretamente reservadas ao marcador:

1. **Confirmação da escala nas séries:** usar quantidade histórica contemporânea, manter abstenção sem ela ou permitir comparação atual como reconstrução exploratória? O dado separador é a disponibilidade de quantidade datada e a ocorrência de eventos societários entre o exercício e a coleta.
2. **[FINANCEIRAS]:** setor, exclusão ampla dos setores financeiros ou modelo da demonstração? A pergunta 5 do levantamento deve mostrar os casos em que essas opções divergem, incluindo empresas sem setor.
3. **[TAXA], [BAZIN], [FII] e [BANCOS]:** permanecem decisões futuras, corretamente identificadas. A escolha deve usar a matriz, a derivação e a disponibilidade das fontes, sem escolher parâmetros pelo aspecto dos resultados.

**Veredito: não pode seguir — fechar a identificação obrigatória das regressões nos itens `fix:` antes da ativação.**

## Rodada 3 — Ficha por ação 1.1 — modo FICHA

**Modo FICHA — terceira rodada da versão 1.1**, arquivo `docs/metodologia/por-acao.md`, na `main`, commit `d16fde5`. Escopo restrito ao fechamento dos achados da segunda rodada. Auditoria somente de leitura, sem rede ou importação do código do projeto nas contas.

Os dois bloqueios anteriores estão fechados. Restam ressalvas nos domínios dos insumos e na harmonização da D20.

### 1. Fórmula e referência

Sem achado pendente. A ficha distingue o LPA divulgado conforme CPC 41/IAS 33 (§§9–10, 19–20, 66 e A13–A14) do recalculado aproximado; também declara as aproximações das decisões 7.8 e 7.9.

### 2. Insumos

Sem ressalva remanescente sobre o yfinance: `docs/metodologia/por-acao.md:40` agora exige valor, fonte, data e resultado da consulta, inclusive falha, com remissão à D16, que exige hash do conteúdo usado.

### 3. Regime, janela e data

Fechada a ressalva do período do ITR: `docs/metodologia/por-acao.md:34` determina o acumulado do ano e exige intervalos idênticos para lucro e LPA. Valores nominais, escala monetária e limitações por eventos societários permanecem declarados.

### 4. Hipóteses e inaplicabilidade

- **Bloqueio fechado** — `docs/metodologia/por-acao.md:78`: lucro dos controladores ausente só admite reserva sem evidência de minoritários **na DRE e no balanço**. Confere com o ramo implementado em `sentinela/data/controladores.py:107` e com o BUG-2A-03.
- **Ressalva fechada** — `docs/metodologia/por-acao.md:68`: uma linha de LPA não finita agora abstém a espécie mesmo havendo outra linha válida.
- **Ressalva** — `docs/metodologia/por-acao.md:43` e `:67`: permanece sem regra expressa o **preço ausente, zero ou negativo**. A regra geral cobre valores não numéricos e não finitos, mas não esses demais casos. **Fecha com:** domínio do preço e motivo de abstenção dos números que dependem dele, preservando os indicadores contábeis independentes do preço.
- **Ressalva** — `docs/metodologia/por-acao.md:69–70`: “coluna ausente, em qualquer coluna” invalida a composição, mas a linha seguinte permite usar a soma das tesourarias quando o total falta. Falta distinguir coluna inexistente de célula sem valor e explicitar a precedência da exceção. **Fecha com:** enumerar os campos obrigatórios e a condição exata que autoriza a soma.

Quantidades negativas, fracionárias e não finitas, tesouraria superior ao capital da espécie e quantidade inválida da unit agora têm tratamento escrito. O yfinance ausente, não positivo ou não finito não libera a escala.

Casos do universo: bancos têm modelo próprio e os casos BBAS3/PINE4; holdings e prejuízo aparecem em CSAN3; units em KLBN11/TAEE11; preferenciais em USIM5/Banrisul. Seguradoras têm mapeamento, mas continuam sem exemplo numérico e sem representante explicitamente selecionado no universo inicial. FIIs de papel, como KNCR11, e de tijolo, como HGLG11, estão expressamente fora desta ficha (`:75`).

### 5. Exemplo independente

Fechadas as ressalvas funcionais da seção 5.3:

- BBAS3 agora apresenta os operandos e a razão antes do arredondamento de apresentação (`docs/metodologia/por-acao.md:152`).
- Os casos sintéticos fornecem entrada e resultado esperado para aceitar, recusar e testar os limites da confirmação (`:153–154`).

Os exemplos permitem testes independentes do código. Os sintéticos validam a regra; **não demonstram confirmação efetiva da KLBN11 pelo yfinance**.

### 6. Sensibilidade

Fechada a ressalva: `docs/metodologia/por-acao.md:167` condiciona a proteção à correção e comparabilidade do yfinance, cobre os dois sentidos do erro e declara que erros semelhantes nas duas fontes podem passar.

### 7. Parâmetros e justificativa

**7.1–7.6:** sem novo achado no escopo desta rodada.

**7.7:** bloqueio fechado em `docs/metodologia/por-acao.md:234–239`: desigualdade estrita `0,1 < Q_CVM/Q_yf < 10`, quantidades definidas para ação/unit, insumos inválidos tratados e uso limitado ao documento mais recente. A comparabilidade passou a ser hipótese aceita.

**7.8:** fechamento preservado; BBAS3 usa explicitamente a 3.99, com conferência de 10% e aproximação declarada.

**7.9:** fechamento preservado; linha específica tem precedência e uma linha específica incoerente não é substituída pela PN genérica.

**7.10:** fechamento preservado; correção individual, duas evidências oficiais e validade limitada aos documentos citados.

**Coerência com o ADR:**

- A ressalva da **D19 está fechada**: `docs/adr/0003-validade-dados-metodo-auditoria.md:143–147` registra expressamente as exceções de escala, linha agregada, classes e correção de espécie.
- **Ressalva** — `docs/adr/0003-validade-dados-metodo-auditoria.md:66`: a reserva da **D20** ainda exige apenas a conferência da DRE para lucro dos controladores ausente; as revisões não acrescentam a exigência do balanço agora escrita na ficha. **Fecha com:** registrar a revisão da D20, alinhando-a à ficha e ao F2A-41.

**D21:** os seis componentes exigidos existem. Restam completar os domínios indicados na seção 4; a aprovação da versão 1.1 continua corretamente pendente.

### Recalculado por mim

Método: leitura dos CSVs locais com `zipfile` e `csv`, filtrando DFP consolidada 2025, versão 1 e exercício ÚLTIMO; aritmética com `Decimal`, sem funções do projeto.

| Caso | Conta independente | Resultado |
|---|---|---:|
| KLBN — ações | 6.241.478.850 − 106.051.185 | 6.135.427.665 |
| KLBN — razão | 1.678.211.000 ÷ ações ÷ 0,2286 | 1,196535248870 |
| KLBN — VPA da unit | (14.401.101 − 6.515.155) × 1.000 ÷ ações × 5 | 6,426565865152 |
| Confirmação sintética | ações ÷ 6.000.000.000 | 1,0225712775: aceita |
| Confirmação sintética | ações ÷ 6.135.428 | 999,999945399082: recusa |
| BBAS — recalculado | 13.698.124.000 ÷ (5.730.834.040 − 22.370.399) | 2,399616580128 |
| BBAS — razão | recalculado ÷ 2,40 | 0,999840241720 |
| MGLU — recalculado | 204.603.000 ÷ (775.945.010 − 1.343.449) | 0,264139669091 |
| PETR — VPA | 415.786.000.000 ÷ 12.888.732.761 | 32,259649393781 |
| TAEE — LPA da unit | 3 × 1,52866 | 4,58598 |

Os limites **0,1 e 10 recusam**, assim como 0,0999. Confirmei também no FCA local: KLBN11 = 1 KLBN3 + 4 KLBN4; USIM5 = PNA; MGLU3 consta como PNA no documento citado, enquanto a DFP apresenta capital e LPA ON.

### Não verificado

- Confirmações reais pelo yfinance: não houve consulta de rede.
- Texto integral das normas CPC/IFRS: referências avaliadas conforme citadas na ficha.
- Artefato antigo de hash `336a92…`: o ZIP local tem SHA-256 `9fa64012518d104b7ceb294648331bf852bf4014b1ac141a67976823ce2b278d`; os operandos conferidos coincidem com a ficha.
- Não executei testes ou lint; esta revisão é documental.

### Perguntas para o Marcos

1. **Preço ausente ou não positivo:** abster os resultados que dependem do preço ou admitir alguma exceção expressa? O dado discriminante é uma entrada com contabilidade válida e preço ausente, zero ou negativo.
2. **Tesouraria total ausente:** autorizar a soma quando faltar a coluna, quando faltar apenas o valor, ou em ambos? O dado discriminante são esses dois formatos com tesourarias por espécie válidas.

**Veredito: pode seguir com ressalvas.**

## Rodada 3 — Proposta da 2B — modo DOCUMENTO

Modo **DOCUMENTO** — terceira rodada de `docs/loop/fila-fase2b-proposta.md`, em `HEAD d16fde5`. Somente leitura; nenhum arquivo alterado.

O bloqueio anterior está fechado **no planejamento da fila**: BUG-2A-21 a 23 têm registro previsto antes das correções, e F2B-18, F2B-20 e F2B-45 exigem retirar a marca da regressão, obter PASS e atualizar o registro. Isso ainda não significa que os testes foram implementados.

### Cabeçalho, regras e ativação

Sem novo achado. A aprovação da ficha 1.1 continua sendo condição de ativação; as exceções à D19 e à D21 estão registradas nas revisões do ADR-0003.

### F2B-35

Sem achado. Corrige explicitamente as divergências documentais herdadas e o gate da seção A.

### F2B-36

**Ressalva** — `docs/loop/fila-fase2b-proposta.md:182`: o aceite pede “duas linhas novas”, mas o corpo agora exige cinco registros, BUG-2A-19 a 23 (`:170–176`). Fecha substituindo a contagem e exigindo os cinco registros, ressalvados os casos comprovadamente não reproduzidos.

### F2B-7

Sem novo achado. A revisão explicita a preservação das propriedades da mediana, da média de dois resultados e do limite do Bazin, além do destino das asserções numéricas.

### F2B-8

Sem achado. Nomeia a regressão BUG-2A-01 e sua passagem para PASS.

### F2B-10

Sem novo achado. A confirmação usa desigualdades estritas, cobre os limites e exclui a confirmação atual do yfinance das séries históricas.

### F2B-11

Sem novo achado. A linha 3.99 depende da conferência prevista na ficha; o levantamento posterior deixa de presumir que BBAS3 continuará sem VPA.

### F2B-12

Sem novo achado. Preserva PNA/PNB na composição e exige coerência entre ação avulsa e unit.

### F2B-13

Sem achado. Exige duas evidências do mesmo documento para corrigir a espécie.

### F2B-14

Sem achado. Identifica BUG-2A-11, teste e atualização do registro.

### F2B-16

Sem achado. Identifica BUG-2A-12 e testa o limite decidido de 10%.

### F2B-17

Sem achado. Identifica BUG-2A-13 e distingue cobertura de companhias, referência oficial e Informe Mensal.

### F2B-18

Sem novo achado. BUG-2A-21 agora tem regressão explicitamente exigida no aceite.

### F2B-20

Sem novo achado. BUG-2A-22 agora tem regressão exigida nos dois motores e predicado restrito no golden.

### F2B-37

Sem achado. Destino explícito do BUG-2A-10, anterior ao consumidor previsto na 2C.

### F2B-38

Sem achado. Destino explícito do BUG-2A-14.

### F2B-39

Sem achado. Destino explícito do BUG-2A-15; preserva a normalização na fronteira.

### F2B-40

Sem achado. Destino explícito do BUG-2A-16, incluindo completude do cache.

### F2B-41

Sem achado. Destino explícito do BUG-2A-17; alteração de testes e dispensa de ficha estão delimitadas.

### F2B-42

Sem achado. Destino explícito do BUG-2A-18; guarda de domínio separada de mudança de fórmula.

### F2B-21

Sem novo achado. A revisão mede bancos depois do F2B-11 e mantém resultados desconhecidos como “não determinado”, sem decidir metodologia.

### F2B-43

Sem achado. Registra os bugs confirmados antes de qualquer correção e deixa o destino para o marcador.

### F2B-22

Sem achado. Parâmetros permanecem pendentes de decisão e aprovação.

### F2B-23

Sem achado. As definições concorrentes de crescimento real continuam apresentadas como escolhas do Marcos.

### F2B-24

Sem achado. As alternativas do Bazin e suas consequências estão explícitas.

### F2B-25

Sem achado. Exige justificar regime, base do DY e spread na ficha.

### F2B-26

Sem novo achado. Exige converter também o ROE na demonstração da equivalência entre regimes.

### F2B-28

Sem achado. Dado aditivo, sem consumidor; base desconhecida bloqueia a implementação.

### Marcador “Fichas da 2B, taxa e fontes”

Sem achado. Decisões, auditorias e aprovação antecedem os consumidores; itens dispensados são retirados antes da retomada.

### F2B-27

Sem achado. Está depois da decisão sobre os campos do Tesouro.

### F2B-29

Sem achado. Contrato aditivo e conversão condicionada à ficha aprovada.

### F2B-30

Sem achado. Separa provedor, seleção pura, proveniência e ponto de entrada da V1.

### F2B-1

Sem achado. Alteração de comportamento isolada, ficha prévia e golden com predicado.

### F2B-31

Sem achado. Execução condicionada às opções que efetivamente substituem a Selic.

### F2B-2

Sem achado. Mudanças autorizadas na seção B e no score estão explicitadas.

### F2A-39

Sem achado. A evidência oficial da ligação continua sendo pré-condição; não repete uma correção já entregue.

### F2B-4

Sem novo achado. A opção de modelo contábil da [FINANCEIRAS] agora exige ajustar a especificação no marcador antes da execução.

### F2B-44

Sem achado. Corrige os dois bugs registrados no F2B-36 antes da ligação da lente bancária.

### F2B-3

Sem achado. Método novo sem ligação ao motor, com ficha e exemplo independente exigidos.

### F2B-32

Sem achado. Ligação ao motor separada da criação do método.

### F2A-10

Sem novo achado. O novo aceite integrado cobre a exceção do coletor que hoje retorna sem a chave de liquidez.

### F2B-33

Sem achado. Atualização documental delimitada, incluindo a exclusão provisória do BTG.

### F2B-34

Sem achado. Propõe a próxima fila sem implementar nem resolver escolhas metodológicas.

### F2B-45

**Ressalva** — `docs/loop/fila-fase2b-proposta.md:770`: “segue ‘alavancagem não avaliada’ […] como hoje o texto inválido” não descreve o código atual. Em `valuation_engine.py:278–292`, texto inválido vira `0.0`, sem esse aviso. Fecha distinguindo o comportamento atual — ausência de penalidade — do aviso novo exigido pelo item, e cobrindo ambos no teste.

A exigência de regressão para BUG-2A-23 foi acrescentada e fecha a omissão anterior.

### F2B-5

Sem novo achado. A mudança de comportamento saiu da limpeza; remoções e exceções da busca por referências estão enumeradas.

### F2B-6

Sem achado. Resumo e arquivamento seguem o protocolo.

### Decisão final e riscos

Sem novo achado. Os bugs abertos BUG-2A-01 e BUG-2A-10 a 18 têm destino explícito nesta fase. Os itens já resolvidos no fechamento da 2A foram retirados da proposta.

### Recalculado por mim

Usando apenas os números e fórmulas de `:885–887`, sem importar o projeto:

- opção (i): \(g=-0,6635071\%\), valor **R$ 47,065868**;
- opção (ii): \(g=2,4644550\%\), valor **R$ 64,473161**;
- diferença: **36,98496%**;
- cálculo nominal equivalente da opção (i): **R$ 47,065868**.

Os arredondamentos publicados conferem.

### Não verificado

- O relatório integral da segunda auditoria DOCUMENTO não está identificado entre os arquivos versionados consultados. Conferi os fechamentos indicados no pedido e no diff de `d16fde5`; não afirmo ter reconciliado achados anteriores não disponíveis.
- A suíte não iniciou: o sandbox não oferece diretório temporário gravável (`No usable temporary directory`). Isso limita a verificação dinâmica, sem demonstrar falha do projeto.
- O Ruff passou com `--no-cache --select E9,F63,F7,F82`.
- Testes novos e comandos de coleta futuros foram avaliados pela especificação e pelo código existente; não foram executados. Não usei rede, mutmut nem regeneração do golden.

### Perguntas para o Marcos

Nenhuma decisão metodológica nova precisa ser tomada para fechar esta rodada. Permanecem corretamente pendentes no marcador:

- **[TAXA]:** definição de crescimento, vértice, inflação e defasagem; distinguem-se pela matriz do F2B-21 e disponibilidade das fontes.
- **[BAZIN]:** Selic, taxa fixa, custo real ou adiamento; distinguem-se pela sensibilidade ao ciclo e pelo regime declarado.
- **[FII]:** spread, janela, fonte do DY e score; distinguem-se pelas séries e verificações da pergunta 4.
- **[BANCOS]/[FINANCEIRAS]/[BTG]:** insumos, escopo e evidência da ligação; distinguem-se pelos resultados das perguntas 5 e 6.

**Veredito: pode seguir com ressalvas.**
