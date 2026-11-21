# Auditoria FICHA — backtest — Codex — 13/11/2026

**Executor:** codex. Autor da ficha: claude-code (outra família, D30).
**Base auditada:** `v2/fase-3 @ 07c8034`, `docs/metodologia/backtest.md`.
**Veredito: CONTESTA MÉTODO. Não liberar F3-8a.**

A auditoria foi somente leitura quanto à ficha, código e testes. Este relatório e os registros do loop são os únicos produtos. A decisão 41 aprova condicionalmente: a condição não se cumpriu. Nenhuma fórmula foi corrigida pelo auditor.

## FB-01 — bloqueante — provento e preço em bases acionárias diferentes

O §5 manda dividir o provento bruto pelo fechamento da data ex na série ajustada por eventos em ações. O F3-4c (`sentinela/data/pit/serie_ajustada.py`, função `ajustar`) divide cada preço pelo produto dos fatores posteriores àquela data até o fim da série. A ficha não manda converter o provento pelo mesmo fator. A divisão mistura dinheiro por ação antiga com preço por ação na base final e altera o retorno total.

Contraexemplo aritmético independente, sem importar o projeto: uma ação custa 10 na entrada. Paga 1 por ação e fecha a 10 na data ex. Depois há desdobramento 1:2; o fechamento final é 5. Reinvestir 1 a 10 compra 0,1 ação; depois do desdobramento são 2,2 ações, valendo 11. Retorno total: **10%**. Na base final, preços de entrada e da data ex são 5 e 5. A regra escrita usa o provento bruto 1 sobre 5, produz fator de reinvestimento 1,2 e retorno **20%**. O preço ajustado de entrada já representa duas ações finais; usar o provento antigo novamente duplica seu efeito.

É necessário fixar uma fórmula que mantenha preço, provento por ação e quantidade na mesma base. Exemplos equivalentes a submeter ao autor/Marcos: acompanhar quantidades com preços brutos e eventos, ou ajustar também cada provento para a base da série de preços. A decisão de reinvestir bruto na data ex permanece; a expressão que a implementa na ficha precisa ser revista. O §10 testa JCP e desdobramento separadamente e não detecta essa combinação. Acrescentar o caso combinado ao contrato após a revisão da ficha.

## FB-02 — esclarecer antes da aprovação — início do retorno e benchmarks

O §3.4 define preço da lente como o fechamento anterior ao dia D; §§2 e 6 fixam rebalanceamento e benchmarks no fechamento de D. O §5 não distingue expressamente o preço de referência da lente do preço inicial do retorno. Usar o preço do §3.4 como entrada e o benchmark de D compara períodos diferentes; usar fechamento de D como entrada resolve o alinhamento, mas precisa estar escrito. Fixar o instante inicial comum e a inclusão dos proventos nas fronteiras, preservando o corte informacional da lente. Este ponto é uma ambiguidade de implementação; FB-01 já basta para o veredito bloqueante.

## Conferência dos critérios pedidos

| Critério | Resultado documental |
| --- | --- |
| Universo, liquidez e demonstrações sem informação posterior a D | Confere a direção dos §§2–3: universo em D, 63 pregões anteriores, versão entregue antes do dia de D, estrito principal e exploratório separado. Não se certifica aqui todo o código da 3-b. |
| Preço sem antecipação | Preço da lente anterior a D confere; início do retorno precisa da precisão FB-02. |
| Proventos por disponibilidade, decisão 40 | §2 exige aprovação anterior a D para a lente. Proventos futuros pertencem apenas à medição ex post do retorno; não podem alimentar elegibilidade nem quintis. A fórmula do retorno é contestada em FB-01. |
| Deslistadas incluídas | §3 inclui as posteriormente deslistadas; §5 mantém último preço e depois CDI. Falta de dados não pode virar exclusão silenciosa ou provento zero. A cobertura incompleta da fonte já está nas pendências da 3-b. |
| Quintis por lente sem score | Confere §§1, 3–4 e 7. Fórmula dos cortes, empates e mínimo de 25 estão explícitos. |
| Retorno total contra Ibovespa e CDI em 12/24/36 meses | Horizontes e benchmarks conferem §§5–6; fórmula não confere por FB-01; fronteira inicial ambígua por FB-02. |
| Nenhuma otimização sobre o resultado | Confere §§1 e 9; não se alteram parâmetros de lente. |
| Banda neutra só proposta e metade fora da amostra | Confere §9 e pacote §6/decisão 17: primeira metade para estudo, segunda para validação, exclusão por horizonte que ultrapassa a fronteira, sem efeito automático em método. |

## Decisão 41 e limitações de cobertura

O pedido do Marcos de 13/11/2026 fixa ações a partir de **2018**, pela ausência de ligação oficial emissor→ticker no FCA aberto anterior, substituindo o início de 2016 da decisão 4. FII mantém primeiro Informe aberto + 13 meses. Esses pontos estão registrados aqui sem editar a ficha durante a auditoria. Após resolver a contestação, devem constar na ficha como decisão e limitação, não como nova pergunta pendente.

As lacunas de DY, Bazin, IPCA das janelas, taxa real e proventos por espécie continuam listadas em `pendencias.md` e no §11 da ficha; esta auditoria não as declara resolvidas. Um relatório sem observações não prova o aceite do backtest integrado.

## Encaminhamento

Marcar `[!]` na aprovação da ficha e parar, conforme itens 3 e 5 do pedido e política §3.1. Autor e Marcos precisam resolver FB-01 e precisar FB-02; em divergência de método entre famílias, a fila prevê segunda opinião Gemini. Não executar F3-8a a F3-10 nem limpeza enquanto este bloqueio estiver aberto.
