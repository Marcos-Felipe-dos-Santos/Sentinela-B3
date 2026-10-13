# ADR-0003 — Validade de dados, de método e auditoria externa

**Status:** proposto (13/10/2026). Decide o Marcos; até lá, nenhuma fila muda por causa deste texto.
**Origem:** revisão independente do plano feita com o ChatGPT em 13/10/2026, mais as lições das Fases 0, 1 e do começo da 2A.
**Relaciona-se com:** ADR-0001 (refactor V2.1), ADR-0002 (loop, tempo e dados; D1 a D15).

## Contexto

O projeto ganhou estrutura de rigor: tipos de unidade, contrato de método, golden, mutação, revisão por agente. A revisão externa apontou o risco que sobra: **aparência de rigor sem demonstrar que dados e premissas representam o que se pretende calcular**. Exemplos concretos já ocorridos:

- PRs com CI verde e nenhum arquivo alterado (#12, #21);
- valores de referência inventados num teste de especificação (#19);
- diário que não batia com o código (F2A-1);
- a V1 lendo o PL dos bancos numa conta que não é o PL (F2A-16, pergunta 4);
- o mesmo código de conta da CVM com significados diferentes entre empresas.

Este ADR chega com a 2A em andamento: F2A-3 e F2A-5 já foram entregues. Ele fixa critérios de validade para o que falta e define, na seção "Transição", como o que já foi entregue é revisto. Versão 4: incorpora duas auditorias externas de 13/10/2026 (Codex, modo DOCUMENTO). A primeira reprovou a versão 2 por quatro bloqueios; a segunda reprovou a versão 3 por um bloqueio (F2A-33 como `feat:` mudando saídas) e cinco ressalvas. Os relatórios estão em `docs/loop/historico/fase-2a/auditoria-adr0003.md`.

## Decisões

Numeração continua a do ADR-0002.

### Tempo e proveniência

**D16 — Proveniência temporal desde a 2A.** Todo dado coletado registra: período de referência; data de entrega ou divulgação, quando a fonte informa; data da coleta; documento; versão; fonte (URL ou arquivo); hash do conteúdo usado. Entra como requisito dos itens de dados da 2A, não como trabalho da Fase 3. O que não for guardado agora pode não ser recuperável depois.

**D17 — Dois modos de histórico.**
- *Histórico estrito:* usa só informação comprovadamente disponível até a data analisada. Sem ela, abstém-se.
- *Reconstrução exploratória:* pode usar aproximações (por exemplo, a versão atual de uma demonstração reapresentada), documentadas, e seus resultados ficam **separados** do estrito, com rótulo próprio.
- Um resultado produzido no passado e um resultado recalculado hoje para uma data passada são registros diferentes.
- Substitui a regra da seção 5 do PLANO que permitia usar a versão atual com registro da limitação.

**D18 — Contratos de provedor junto com o provedor.** Cada provedor novo ou alterado na 2A ganha teste de contrato (formato, colunas, unidades, escala) no mesmo item, com fixture tirada do arquivo real e registrada. Não espera a Fase 4.

### Definições contábeis

**D19 — Ações e indicadores por ação com semântica explícita.** Revisa o item 1 da seção 4 de `docs/decisoes/checkpoint-fase0.md` ("LPA = lucro ÷ (ON + PN − tesouraria)"). O que continua valendo daquela decisão: a Composição do Capital como fonte das ações, o lucro e o PL do mesmo documento, e a divergência com o yfinance como **alerta, nunca motivo de abstenção**. A regra antiga "abstenção só quando a CVM falha" vale apenas nesse sentido: o yfinance não derruba um número da CVM. As abstenções por classe, composição ou escala das regras abaixo são novas e prevalecem. O que muda é o denominador do LPA e o tratamento de classes.

Cada número tem uma definição e um papel:

| Número | Definição | Papel |
|---|---|---|
| **LPA usado pelos métodos** | o LPA básico divulgado pela companhia na DRE (3.99.01.x), da espécie do ticker, que já segue a IAS 33/CPC 41 (lucro dos controladores ÷ média ponderada) | entrada dos métodos |
| **LPA recalculado** | lucro dos controladores ÷ ações em circulação no fim do período (ON + PN − tesouraria) | conferência contra o divulgado (F2A-5) e reserva |
| **VPA** | PL dos controladores ÷ ações em circulação no fim do período | entrada dos métodos (aqui o fim do período é a definição correta, não aproximação) |
| **Ações para valor de mercado** | ações em circulação na data, por espécie | capitalização |

Regras de uso:
1. **LPA divulgado disponível e coerente** (escala determinada e mesmo sinal do lucro): é o LPA dos métodos.
2. **Divulgado ausente:** o recalculado entra como **aproximação declarada**, com marca na proveniência ("ações do fim do período, não média ponderada"). Os métodos podem usá-lo.
3. **Mais de uma classe preferencial com direitos distintos** (PNA, PNB etc., identificadas pela `Sigla_Classe_Acao_Preferencial` do FCA): o LPA recalculado comum **se abstém** para as preferenciais; vale só o divulgado da classe, se houver. Sem divulgado da classe, o LPA da classe se abstém.
4. **Units:** o LPA da unit é a soma dos LPAs das espécies que a compõem, ponderada pela composição oficial do FCA. Se faltar o LPA divulgado de alguma espécie componente, aplica-se a regra 2 com a marca, **exceto** quando a regra 3 proíbe o recalculado para essa espécie: aí a unit inteira se abstém. A regra 3 tem precedência sobre a 2. Composição não reconhecida: abstém-se (já é o comportamento do F2A-1).
5. **Escala das ações:** a inferência pelo LPA divulgado (o F2A-3 escolhe unidade ou mil pela razão mais perto de 1, com faixa [0,1; 10]) fica **provisória** até a ficha do F2A-34, que justifica a faixa com a distribuição medida no F2A-16 e lista os casos na faixa mas longe de 1. Esses casos já geram alerta (F2A-5). Quando não há LPA divulgado para inferir a escala, ela é indeterminada e o recalculado se abstém.

Consolidado contra individual é sempre declarado.

**D20 — Contas da CVM por código e descrição.** Nenhuma conta é lida só pelo código. A leitura confere o par (código, descrição) contra uma tabela versionada por modelo de demonstração (empresas não financeiras, bancos, seguradoras). Par sem correspondência vira abstenção com motivo, nunca valor de outra conta.

Reservas permitidas, e só estas. São **política proposta** por este ADR, não demonstração de que não há minoritários: a ausência da linha é tratada como falta de evidência, e a ficha do F2A-34 registra a justificativa e os casos do universo em que a reserva foi usada. Aprovar o ADR aprova esta política.

Distinção obrigatória: **linha ausente** (a conta não existe no documento) pode autorizar a reserva; **valor inválido** (linha presente com valor não numérico, NaN ou infinito) nunca autoriza: o campo se abstém.

- **Lucro dos controladores ausente:** vale o lucro total **somente** se a linha dos não controladores também estiver ausente ou zerada, isto é, não há evidência de minoritários. Com a linha dos não controladores presente e diferente de zero, o lucro dos controladores se abstém.
- **PL dos controladores:** vale o PL total **somente** se a conta de não controladores do balanço estiver ausente ou zerada **e** o lucro dos não controladores também. Com qualquer evidência de minoritários sem a separação no balanço, o PL dos controladores se abstém.
- Toda reserva usada fica registrada na proveniência do campo.

O campo genérico `patrimonio_liquido` de `calcular_indicadores`, ainda lido só pelo código (`cvm_provider.py`, `_conta`), passa pela tabela no F2A-38 (correção, não o F2A-33). O caminho dos controladores já está protegido desde o F2A-3: VPA e ROE se abstêm quando a 2.03 não descreve patrimônio líquido.

### Método

**D21 — Ficha metodológica antes de cada lente.** Nenhuma lente nova ou versão nova de método é implementada sem ficha em `docs/metodologia/<lente>.md`, aprovada pelo Marcos, com:
1. fórmula e referência;
2. definição exata de cada insumo;
3. regime monetário (real ou nominal), janela e data de referência;
4. hipóteses e casos de inaplicabilidade (abstenção);
5. um exemplo calculado de forma independente do código;
6. sensibilidade às premissas principais.

A ficha é escrita ou revisada pelo auditor externo (D30), e o exemplo vira teste.

**D22 — Coerência de regime vai além de k e g.** Fluxos, crescimento e desconto ficam no mesmo regime. Trocar Selic por NTN-B não é, sozinho, correção metodológica. A lente de bancos (ROE contábil contra custo de capital) tem derivação explícita na ficha.

**D23 — Parâmetros justificados e versionados.** Prêmio, spread e janela têm justificativa própria, registrada na ficha. Nenhum parâmetro é escolhido para que os resultados pareçam razoáveis.

### Apresentação

**D24 — Três dimensões separadas.** O resultado mostra, sem fundir numa nota única:
- qualidade empresarial (rentabilidade, endividamento, consistência);
- valuation por lente (o que as premissas de cada método implicam);
- qualidade dos dados (completude, atualidade, reconciliação).

**D25 — Janela justificada por método.** As janelas do checkpoint da Fase 0 valem como ponto de partida; cada uma é justificada na ficha, com tratamento explícito para empresas com histórico menor e mudanças estruturais.

**D26 — Histerese fora do cálculo.** O motor produz resultado determinístico para (ticker, data). A histerese (F-28) vive só na camada de alertas, que guarda o próprio estado. O histórico registra separadamente o resultado calculado e o estado do alerta.

### Testes e operação

**D27 — Aceite em PASS.** Uma correção termina com o teste em PASS e a marca de xfail retirada. XPASS é estado intermediário. Os aceites que diziam "xfail → XPASS" passam a ler "xfail estrito → correção → marca retirada → PASS". O rito `fix` do `docs/loop/protocolo.md` muda no mesmo commit que aceita este ADR.

**D28 — Métrica não é validade.** Mutation score continua como gate, mas não substitui referência independente. Todo método ou cálculo financeiro tem pelo menos um caso com valor esperado tirado de fonte externa citada ou de cálculo independente documentado na ficha.

**D29 — Backup restaurável antes das migrações.** Antes da primeira migração relevante do SQLite (Fase 3), existe backup consistente (API de backup do SQLite) e **uma restauração verificada**. A Fase 4 acrescenta testes de falha deliberada: download interrompido, execução repetida, fechamentos concorrentes, fonte indisponível ou com formato alterado, horário perdido.

### Processo

**D30 — Auditoria externa por modelo diferente.** O loop do Claude Code continua o único autor de código do branch da fase. Um modelo de outra família (hoje, o ChatGPT/Codex) atua só como auditor, com o prompt versionado em `docs/loop/auditoria-externa.md`:
- no checkpoint de cada fase, antes do push, em modo FASE;
- em cada ficha metodológica, em modo FICHA;
- em PRs do Jules, em modo PR.

O resultado vai para `docs/loop/historico/fase-N/auditoria-externa.md`. Achado **bloqueia** impede o push até ser resolvido ou dispensado pelo Marcos por escrito.

**Auditor indisponível:** o checkpoint espera. O `senior-reviewer` não substitui o auditor externo, porque é da mesma família de modelo que escreveu o código. Publicar sem auditoria externa só com dispensa escrita do Marcos, no mesmo arquivo do histórico da fase, dizendo o motivo.

**D31 — Jules reduzido.** O Jules fica restrito a tickets triviais com especificação externa completa e arquivo único. Tickets com valores de referência numéricos passam ao loop, com o valor tirado da ficha.

**D32 — Escopo verificável.** "Todos os listados" vira meta com denominador explícito e lista de exclusões. "Qualquer data" ganha intervalo temporal definido na Fase 3, junto com o D17 (primeira data com proveniência completa e tratamento das datas anteriores); até lá, nenhum texto promete histórico para qualquer data.

- **Universo inicial:** as 45 ações do mapa regenerado no F1-15 e os 30 FIIs de `cvm_fii_map.py` (os cinco que `docs/decisoes/fontes-fase2a.md` registra fora da listagem no período entram como **casos históricos**: servem para testar abstenção e histórico estrito, mas não contam no denominador da cobertura atual), mais estes casos difíceis, se não estiverem lá: os 12 bancos ativos do F2A-16; as units do índice (KLBN11, SANB11, TAEE11, ENGI11, BRBI11, IGTI11); uma holding com minoritários relevantes (CSAN3); uma empresa com reapresentação de DFP (escolhida no F2A-32); FIIs de papel e de tijolo. A lista fechada vai para `docs/decisoes/universo-inicial.md` no F2A-35.
- **Denominador da cobertura do índice:** pares (CNPJ, código) ativos no FCA mais recente e FIIs listados em bolsa no Informe Mensal, como o F2A-1 já mede; toda exclusão tem motivo listado.
- **Critério de ampliação:** um grupo novo entra no universo quando todos os seus casos difíceis passam pela verificação do item (números conferidos contra a fonte e abstenções com motivo), sem divergência sem explicação. O gate de cobertura do PLANO passa a citar este denominador.

## Transição: o que já foi entregue

Estado em 13/10/2026: F2A-15, 17, 18, 16, 1, 2, 19, 20, 3, 6 e 5 commitados (`b83dde1`).

**F2A-3 e F2A-5 não são reabertos.** O que eles fizeram continua no branch. O que diverge deste ADR vira itens `fix:` novos, cada um com teste antes, e o golden muda só por eles.

O que o F2A-3 já cumpre, conferido no código pela auditoria externa:
- lucro e PL dos controladores; o LPA divulgado escolhido pela descrição da linha; VPA e ROE que se abstêm quando a 2.03 não descreve patrimônio líquido;
- documento único por CNPJ, `DT_REFER` e `VERSAO`;
- a aproximação do fim do período declarada no `detalhe()`.

O que diverge, e o item que corrige:
- **LPA dos métodos:** hoje é o recalculado com ações do fim do período; pelo D19, passa a ser o divulgado da espécie (F2A-36).
- **Classes preferenciais:** hoje PNA e PNB são agrupadas como "PN", e o provedor fica com a primeira linha "PN…"; pelo D19, regra 3 (F2A-36).
- **Units:** hoje o LPA da unit é o recalculado vezes as ações por unit; pelo D19, regra 4 (F2A-36).
- **Reservas de controladores:** hoje o lucro total entra quando a linha dos controladores falta, mesmo com minoritários; pelo D20, só sem evidência de minoritários (F2A-37).
- **`patrimonio_liquido` genérico** lido só pelo código, que alimenta a alavancagem (`cvm_provider.py`) e chega ao motor (`market_engine.py`): F2A-38.

## O que muda na Fase 2A

Itens novos, antes do F2A-7, nesta ordem:
- **F2A-32** · `feat: record temporal provenance for collected data` — proveniência do D16 (período, entrega, coleta, documento, versão, fonte, hash) no cache da CVM, no COTAHIST e no índice; testes de contrato dos provedores existentes (D18); escolhe a empresa com reapresentação do universo inicial.
- **F2A-33** · `feat: map CVM accounts by code and description` — só infraestrutura: tabela versionada (código, descrição, modelo de demonstração) e função de leitura que se abstém sem correspondência (D20), com testes próprios. **Nenhum consumidor existente muda neste item**; o golden não pode mudar. O cálculo da lente de bancos continua no F2A-9.
- **F2A-38** · `fix: read existing CVM accounts through the code and description table` **[golden]** — rito `fix`: teste xfail estrito com um banco cuja 2.03 não é PL, mostrando que hoje `patrimonio_liquido` e a alavancagem saem de conta errada; depois as leituras existentes passam pela tabela do F2A-33, com abstenção. Escopo do golden declarado no item: só os campos derivados de `patrimonio_liquido` e das contas trocadas; qualquer outra mudança no golden reprova o item.
- **F2A-34** · `docs: add methodology sheet for per-share figures` — ficha do D21 para LPA, VPA, classes, units e escala, com exemplo independente e a justificativa da faixa [0,1; 10]. **Aprovação do Marcos e auditoria externa (modo FICHA) antes do F2A-36.**
- **F2A-35** · `docs: define the initial universe` — `docs/decisoes/universo-inicial.md` (D32).
- **F2A-36** · `fix: use reported EPS by share class in valuation inputs` **[golden]** — regras 1 a 4 do D19.
- **F2A-37** · `fix: restrict controlling-interest fallbacks to evidence of no minorities` **[golden]** — reservas do D20.

Outros ajustes:
- Ordem: F2A-32, 33, 38, 34, 35, 36, 37 (o número segue a ordem de criação, como já acontece na 2A).
- F2A-7, F2A-8 e F2A-9 leem contas pelo F2A-33 e seguem D19 e D20.
- Todos os aceites "XPASS" leem como D27.
- O checkpoint da 2A inclui a auditoria externa (D30).

Pontos do diário do F2A-3 para o checkpoint: a divergência de +402% das ações da SBSP3 contra o yfinance; o BTCI11 e o TRPL11, que o índice tira do motor de FII; e a CSAN3, com ROE dos controladores de −1,83 (holding).

## O que muda nas fases seguintes

- **2B:** fichas (D21) de taxa real, Gordon, FII e bancos antes de cada item; D22 e D23.
- **2C:** D24, D25 e D26.
- **3:** D17 e D29.
- **4:** D29, falhas deliberadas.
- **5:** perguntas específicas no lugar de "notícia tem sinal": divulgação antes ou depois do fechamento, eventos sobrepostos, persistência, tamanho do efeito, robustez à janela.
- **6:** a vitrine do núcleo pode sair antes da Fase 5 terminar.
- **7:** aceite contra os requisitos aprovados da V2, não paridade com tudo da V1.

## Consequências

- A 2A fica mais longa (sete itens a mais, uma ficha e uma auditoria de ficha). Em troca, os números por ação passam a ter definição escrita e conferida.
- O prazo da Fase 2 deixa de ter estimativa até o fim da 2A.
- O processo passa a depender de um segundo modelo no checkpoint. Sem ele, o checkpoint espera ou o Marcos dispensa por escrito (D30).
