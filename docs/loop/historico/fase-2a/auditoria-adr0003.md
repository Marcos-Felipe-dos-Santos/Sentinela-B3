# Auditorias externas do ADR-0003

Relatórios finais do auditor externo (Codex, `--sandbox read-only`, modo DOCUMENTO), copiados sem edição de conteúdo; só os links para caminhos locais viraram texto. O log completo da execução não é versionado.

## Auditoria 1 — versão 2 do ADR (HEAD `b83dde1`)

**Modo DOCUMENTO.** Auditei o ADR-0003 no branch `v2/fase-2a`, HEAD `b83dde1`, contra PLANO, ADRs 0001/0002, fila, diário e decisões registradas. Conferi também `acoes_cvm.py` e `cvm_provider.py`. Nenhum arquivo foi alterado.

O ADR preserva os princípios dos anteriores: abstenção, isolamento dos métodos, dados oficiais e decisão metodológica pelo Marcos. D17 declara expressamente que substitui a permissão de reconstrução do PLANO; mudanças como D24, D26 e D32 são propostas, não contradições por si mesmas. Os problemas estão na transição e em critérios ainda incompletos.

### F2A-3 e transição da fase

- **bloqueia** — O ADR trata F2A-3 como futuro e exige ficha antes de começá-lo ([ADR:17], linhas 99–102), mas ele já está `[x]` na [fila:357], consta como sucesso no [diário:163] e existe no commit `882ef0c`; F2A-5 também já foi entregue. **Para fechar:** definir quais entregas serão reavaliadas e como os novos pré-requisitos se aplicam ao código existente.

- **bloqueia** — D19 modifica uma decisão aceita sem identificar expressamente sua substituição: o [checkpoint:34] fixa lucro dividido por ON + PN − tesouraria; o [ADR:39] passa a exigir média ponderada quando disponível. O código usa exclusivamente ações finais ([acoes_cvm.py:134]), embora declare essa aproximação em `detalhe()`. **Para fechar:** registrar a revisão da decisão anterior e o aceite da transição; o comportamento atual não cumpre integralmente D19.

### D19 — classes, units e escala

- **bloqueia** — “Classes preferenciais distinguidas quando o cálculo exigir” não define quando distinguir ou abster-se ([ADR:42]). O código calcula um LPA comum usando ações totais e multiplica units pela soma dos componentes ([acoes_cvm.py:135]); o provedor agrupa descrições `PN…` numa única chave, escolhendo a primeira ([cvm_provider.py:144]). **Para fechar:** a ficha deve definir tratamento de direitos diferentes, PNA/PNB e composição de units, incluindo inaplicabilidade.

- **ressalva** — D19 não enquadra a inferência de escala já implementada: escolha por proximidade ao LPA divulgado e faixa `[0,1; 10]` ([acoes_cvm.py:85]). O [diário:188] deixa essa faixa para o Marcos. **Para fechar:** exigir na ficha justificativa, aprovação e limites dessa inferência; concordância com o LPA usado para escolher a escala não prova, sozinha, sua validade.

### D20 — contas e abstenção

- **ressalva** — A alegação sobre PL bancário permanece verdadeira para `patrimonio_liquido`: `_conta` seleciona somente pelo código e o campo recebe essa leitura ([cvm_provider.py:381], linha 423). Porém F2A-3 já protege `pl_controladores`, devolvendo `None` quando `2.03` não descreve patrimônio líquido ([cvm_provider.py:94]); VPA e ROE desse caminho se abstêm. **Para fechar:** distinguir no contexto do ADR o campo genérico ainda vulnerável do caminho já protegido.

- **bloqueia** — D20 exige abstenção para par sem correspondência ([ADR:46]), mas não resolve as reservas existentes: ausência da linha dos controladores retorna lucro total; minoritários ausentes ou não reconhecidos permitem retornar PL total ([cvm_provider.py:76], linhas 100–105). **Para fechar:** explicitar quais evidências autorizam essas reservas e quando a ausência significa abstenção.

### D27, D30 e execução

- **ressalva** — D27 corrige os aceites, mas o protocolo ainda encerra o rito `fix` em XPASS ([protocolo:28]). D30 exige modelo de outra família, enquanto as consequências permitem `senior-reviewer` sem estabelecer essa independência ([ADR:120]). **Para fechar:** incluir a sincronização do protocolo e definir se a indisponibilidade do auditor permite publicação, com qual aprovação.

- **ressalva** — D32 troca cobertura universal por universo representativo, mas ainda não oferece denominador, exclusões ou critério mensurável de ampliação ([ADR:94]). **Para fechar:** exigir esses elementos antes de ativar a fila revisada e atualizar o gate de cobertura do PLANO.

### Recalculado por mim

Por aritmética independente, sem executar os módulos:

- Fronteira entre escalas por distância logarítmica: `√1000 = 31,6228`; distância multiplicativa até 10: `3,1623`. Confere com a justificativa aritmética do diário, sem validar a faixa.
- `157 ÷ 170 × 100 = 92,3529%`: confere com os **92,4%** publicados; não confirma a execução do mutmut.
- `38 + 7 = 45`: a contagem de derivadas e abstenções fecha.
- Exemplo ilustrativo: lucro 1.000, média de 100 ações e saldo final de 200 produzem LPA 10 e 5, respectivamente. Declarar a aproximação não elimina seu efeito.

### Não verificado

Não executei pytest, mutmut, downloads ou restauração. Não confirmei os números reais por companhia do diário, os incidentes dos PRs #12/#19/#21, nem a conformidade normativa com IAS 33/CPC 41. A conferência do código foi estática; não auditei os consumidores completos em `market_engine.py` e `data_quality.py`.

### Perguntas para o Marcos

1. D19 substitui a decisão do checkpoint da Fase 0? F2A-3 e F2A-5 serão reabertos?
2. Quais aproximações de denominador, classe e escala podem produzir indicadores, e quais exigem abstenção?
3. O checkpoint pode publicar com auditor da mesma família? Qual universo mínimo passa a definir o aceite?

**Veredito: não pode seguir para ativação como está; precisa fechar a transição do F2A-3 e os critérios de D19/D20.**

## Auditoria 2 — versão 3 do ADR (commit `c7a73e0`)

**Modo DOCUMENTO.** Escopo: ADR-0003 v3, commit `c7a73e0`, no branch `v2/fase-2a`. Auditoria somente de leitura.

Os pontos anteriores receberam encaminhamento explícito, mas **não considero todos fechados**: a Transição ainda permite mudança de comportamento num item `feat:`, e há ambiguidades na D19 e no universo da D32.

### D19 — revisão do checkpoint

A revisão está explícita: identifica o item substituído, separa LPA divulgado, recalculado, VPA e capitalização, e condiciona F2A-36 à ficha aprovada e auditada. O problema de revisão silenciosa da decisão anterior foi fechado.

- **Ressalva** — `docs/adr/0003-validade-dados-metodo-auditoria.md:37` preserva “abstenção só quando a CVM falha”, mas as regras seguintes exigem abstenção por classe, composição ou escala indeterminada; para fechar, delimitar aquela preservação à divergência com o yfinance.
- **Ressalva** — `docs/adr/0003-validade-dados-metodo-auditoria.md:52` manda aplicar a reserva da regra 2 quando faltar um componente da unit, sem explicitar a precedência da proibição da regra 3; para fechar, declarar que a unit se abstém quando um componente não admite reserva.

### Transição — entregas existentes

O texto reconhece corretamente F2A-3 e F2A-5 como entregues e encaminha LPA, classes, units e reservas para correções novas. Conferi no código a seleção do divulgado por descrição, a reserva irrestrita de lucro e a proteção da descrição do PL.

- **Bloqueia** — `docs/adr/0003-validade-dados-metodo-auditoria.md:142` classifica F2A-33 como `feat:`, mas manda substituir **todas** as leituras de conta e introduzir abstenção. Isso altera dados já consumidos: `cvm_provider.py:445` deriva alavancagem do PL genérico, e `market_engine.py:53` a transmite ao motor. Contradiz a separação de comportamento exigida pelo protocolo e a própria Transição (`:124`). Para fechar, separar a infraestrutura da aplicação que corrige saídas, atribuindo a esta rito `fix:`, teste de regressão e escopo explícito do golden.

### D20 — planos B

As reservas agora têm condições e registro de proveniência. Também há encaminhamento explícito do PL genérico para F2A-33 e das reservas para F2A-37. **Fechado no desenho documental**, sujeito à aprovação do Marcos.

- **Ressalva** — `docs/adr/0003-validade-dados-metodo-auditoria.md:60` trata ausência da linha como condição suficiente para a reserva. Isso é uma política proposta, não demonstração de inexistência de minoritários; para fechar, registrar na ficha sua justificativa e distinguir linha ausente de valor inválido.

### D30 — auditor indisponível

**Fechado.** `docs/adr/0003-validade-dados-metodo-auditoria.md:110` exige espera ou dispensa escrita, com motivo, pelo Marcos. O `senior-reviewer` deixou de ser substituto automático.

### D32 — universo e denominador

O denominador do índice está explícito e corresponde à definição de `sentinela/data/referencia/cobertura.py:19`. O universo inicial tem composição proposta e item responsável por fechar a lista.

- **Ressalva** — `docs/adr/0003-validade-dados-metodo-auditoria.md:116` inclui todos os 30 FIIs do mapa, embora `docs/decisoes/fontes-fase2a.md:140` registre cinco fora dos listados em bolsa no período. Para fechar, distinguir casos históricos de casos atuais e registrar o tratamento no F2A-35.
- **Ressalva** — `docs/adr/0003-validade-dados-metodo-auditoria.md:114` promete tornar “qualquer data” verificável, mas não define intervalo temporal; para fechar, atribuir explicitamente essa definição à decisão da Fase 3.

### Recalculado por mim

Contagem dos itens propostos: F2A-32 a F2A-37 = **seis**, coerente com as consequências. A base nominal é **45 + 30 = 75 entradas**, antes das inclusões e deduplicação; não é o tamanho final do universo.

### Não verificado

Não encontrei o relatório anterior versionado; portanto, não posso confirmar equivalência integral com seus quatro bloqueios e todas as ressalvas. Também não refiz as coletas que sustentam +402% e ROE −1,83, nem executei testes neste modo documental.

### Perguntas para o Marcos

A reserva por linha ausente da D20 está aprovada como política? Os FIIs fora da listagem devem integrar o universo inicial como casos históricos?

**Veredito: não pode seguir.**

## Resposta na versão 4

- Bloqueio do F2A-33: dividido em F2A-33 (`feat:`, só infraestrutura, golden intocado) e F2A-38 (`fix:` com xfail, escopo do golden declarado).
- D19 linha "abstenção só quando a CVM falha": restrita ao sentido de que o yfinance não derruba número da CVM.
- D19 regra 4: a regra 3 tem precedência; a unit se abstém quando um componente não admite reserva.
- D20: reservas declaradas como política proposta; linha ausente diferente de valor inválido; justificativa na ficha do F2A-34.
- D32: os cinco FIIs fora da listagem entram como casos históricos, fora do denominador atual; "qualquer data" fica para a Fase 3.
- Relatórios agora versionados neste arquivo.
