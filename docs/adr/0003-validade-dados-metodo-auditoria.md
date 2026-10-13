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

Este ADR fixa critérios de validade antes de a 2A avançar para os itens que calculam (F2A-3 em diante).

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

**D19 — Ações e indicadores por ação com semântica explícita.** O F2A-3 distingue, e nunca mistura:
- LPA contábil divulgado (DRE 3.99): referência de conferência;
- LPA recalculado: lucro atribuível aos controladores ÷ **média ponderada** das ações em circulação no período (IAS 33/CPC 41), quando a média estiver disponível; quando não estiver, a aproximação usada é declarada no resultado;
- VPA na data: PL dos controladores ÷ ações em circulação no fim do período;
- quantidade para valor de mercado: ações em circulação na data, por classe;
- units pela composição oficial e classes preferenciais distinguidas quando o cálculo exigir.

"ON + PN − tesouraria" é insumo de reconciliação, não definição universal. Consolidado contra individual é declarado.

**D20 — Contas da CVM por código e descrição.** Nenhuma conta é lida só pelo código. A leitura confere o par (código, descrição) contra uma tabela versionada por modelo de demonstração (empresas não financeiras, bancos, seguradoras). Par sem correspondência vira abstenção com motivo, nunca valor de outra conta.

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

**D27 — Aceite em PASS.** Uma correção termina com o teste em PASS e a marca de xfail retirada. XPASS é estado intermediário. Os aceites que diziam "xfail → XPASS" passam a ler "xfail estrito → correção → marca retirada → PASS".

**D28 — Métrica não é validade.** Mutation score continua como gate, mas não substitui referência independente. Todo método ou cálculo financeiro tem pelo menos um caso com valor esperado tirado de fonte externa citada ou de cálculo independente documentado na ficha.

**D29 — Backup restaurável antes das migrações.** Antes da primeira migração relevante do SQLite (Fase 3), existe backup consistente (API de backup do SQLite) e **uma restauração verificada**. A Fase 4 acrescenta testes de falha deliberada: download interrompido, execução repetida, fechamentos concorrentes, fonte indisponível ou com formato alterado, horário perdido.

### Processo

**D30 — Auditoria externa por modelo diferente.** O loop do Claude Code continua o único autor de código do branch da fase. Um modelo de outra família (hoje, o ChatGPT/Codex) atua só como auditor, com o prompt versionado em `docs/loop/auditoria-externa.md`:
- no checkpoint de cada fase, antes do push, em modo FASE;
- em cada ficha metodológica, em modo FICHA;
- em PRs do Jules, em modo PR.

O resultado vai para `docs/loop/historico/fase-N/auditoria-externa.md`. Achado **bloqueia** impede o push até ser resolvido ou dispensado pelo Marcos por escrito.

**D31 — Jules reduzido.** O Jules fica restrito a tickets triviais com especificação externa completa e arquivo único. Tickets com valores de referência numéricos passam ao loop, com o valor tirado da ficha.

**D32 — Escopo verificável.** "Todos os listados" e "qualquer data" viram metas com denominador explícito e lista de exclusões. A primeira entrega é um universo representativo que inclui os casos difíceis (bancos, units, holdings com minoritários, empresas com reapresentação, FIIs de papel e de tijolo), ampliado por critério mensurável.

## O que muda na Fase 2A

- **F2A-1:** retoma com as correções do diário e acrescenta ao registro do índice a data de coleta e o hash de cada arquivo-fonte (D16).
- **Item novo F2A-32 (antes do F2A-3):** `feat: record temporal provenance for collected data` — esquema de proveniência (D16) aplicado ao cache da CVM, ao COTAHIST e ao índice; testes de contrato dos provedores existentes (D18).
- **Item novo F2A-33 (antes do F2A-3):** `feat: map CVM accounts by code and description` — tabela versionada (código, descrição, modelo) e leitura que se abstém sem correspondência (D20); conserta de passagem a leitura do PL dos bancos na V1 como `fix:` separado, se mudar saída.
- **Item novo F2A-34 (antes do F2A-3):** `docs: add methodology sheet for per-share figures` — ficha do D21 para LPA, VPA e quantidade de ações (D19), com exemplo independente; o F2A-3 só começa com a ficha aprovada.
- **F2A-3, F2A-5, F2A-7, F2A-8 e F2A-9:** passam a seguir D19 e D20.
- **Todos os aceites "XPASS":** leem como D27.
- **Checkpoint da 2A:** inclui a auditoria externa (D30).

## O que muda nas fases seguintes

- **2B:** fichas (D21) de taxa real, Gordon, FII e bancos antes de cada item; D22 e D23.
- **2C:** D24, D25 e D26.
- **3:** D17 e D29.
- **4:** D29, falhas deliberadas.
- **5:** perguntas específicas no lugar de "notícia tem sinal": divulgação antes ou depois do fechamento, eventos sobrepostos, persistência, tamanho do efeito, robustez à janela.
- **6:** a vitrine do núcleo pode sair antes da Fase 5 terminar.
- **7:** aceite contra os requisitos aprovados da V2, não paridade com tudo da V1.

## Consequências

- A 2A fica mais longa (três itens a mais e fichas). Em troca, o F2A-3 em diante parte de definições escritas, e a auditoria passa a ter critério.
- O prazo da Fase 2 deixa de ter estimativa até o fim da 2A.
- O processo passa a depender de um segundo modelo no checkpoint. Se ele não estiver disponível, o checkpoint usa o `senior-reviewer` com o mesmo prompt, registrando a limitação.
