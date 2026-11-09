# Janelas fundamentais — F2C-1

Implementação das fichas 2.1 aprovadas expressamente pelo Marcos em 28/10/2026. O contrato abaixo descreve produtores e consumidores integrados; evidências de cálculo, regressão, mutação e impacto no universo estão no diário do F2C-1.

Fonte normativa: fichas Graham 2.1 e Lynch 2.1, aprovadas expressamente pelo Marcos em 28/10/2026, e decisões-2c §12. Compatibilidade exige quantidades e escalas de cada documento ou fator oficial quando necessário; CNPJ/modelo iguais e falha de API não são provas substitutas.

## Contrato de entrada normalizado

`sentinela.data.janelas_fundamentais.entradas(dados, instante)` é puro: sem rede, banco ou relógio. Recebe a série anual por documento, início/fim reais, LPA da classe e VPA do próprio documento, proveniência temporal e ações em circulação na escala demonstrada do próprio documento. A compatibilidade entre exercícios consecutivos segue a razão posterior/anterior estritamente em (0,9; 1,1), que dispensa ajuste no par; fora, exige fator oficial B3 ou abstenção com motivo. Acumular os fatores oficiais até a base final: um split de q ações novas por antiga divide o LPA antigo por q. Não usar a razão como fator presumido. `ipca_serie` carrega índices relativos dos meses finais obtidos pelo produto de fatores mensais SIDRA 1737 variável 63, publicações do calendário IBGE e fonte/coleta. Graham usa a média dos cinco LPA na moeda final; Lynch usa os extremos nominais em quatro intervalos. Falha de IPCA só abstém Graham. Insumo não demonstrado nunca é reconstruído por P/L ou P/VP na produção.

Esses campos são o contrato interno de fontes normalizadas, não uma descrição do layout bruto de uma API CVM/B3/IBGE. O produtor CVM acrescenta as janelas lidas da DRE do próprio documento; a série preserva as fontes e o motor recebe um pacote validado ou motivo. Reorganização societária/perímetro não causa abstenção nesta revisão: exibir sempre "reorganização societária no período não é detectada". A detecção tem destino na Fase 3, com fonte e contrato próprios antes de implementar. A relação de eventos de 12 meses do Bazin não é rotulada como cobertura de cinco anos; a regra de razões documentais da 2.1 substitui essa exigência para pares compatíveis. Fora da faixa, sem fator oficial disponível, abster. A atualização monetária estende o produtor macro existente, sem coletor duplicado.

## Exemplos e regressões

Graham: média 3,20 e VPA 20 → 37,9473319220; preço 100/P/L 10 não deve substituir 3,20. Lynch: extremos 1 e 2,0736 em quatro intervalos → 20%, m=1 → 41,472; sem multiplicador 1,5 ou retenção. BUG-2C-30 e 31 foram reproduzidos com xfail estrito antes da mudança; após dois XPASS, as marcas foram retiradas e o registro corrigido. Novos testes de fonte, corte, janela, split, prejuízo e domínio preservam abstenções. Testes V1 não são oráculo da metodologia aprovada.

As fixtures de `tests/apoio_janelas.py` são cenários sintéticos explicitamente completos para testar consumidores. O helper montar documentos não concede à produção um fallback semelhante. Nenhum código de cálculo ganha rede ou relógio. P/L de mercado deixou de ser guarda no Graham, e lucro médio positivo pode coexistir com esse múltiplo descartado.

## Medição e golden

Predicado e IDs prévios em `predicados-golden-2c.md`: grade de 2.291 linhas, 1.410 saídas alteradas em Graham/Lynch e suas consequências na síntese legada (retirada somente nos itens 3/5). FII, banco e casos fora do predicado permanecem iguais; Gordon/Bazin não mudam de fórmula ou janela. A proteção abortou uma gravação antes de escrever por erro de enumeração da classe com espaços, corrigido segundo a normalização já vigente e registrado no diário.

Medição histórica anterior às decisões 2.1, superada pela medição abaixo: snapshot público de 51 ações/units do F2B-31, coleta em 20/10/2026, SHA256 `a36b026a526eaeea23f55a11793dcd90e0254e5191edb8bd8902894e477ff3fe`: Graham 15 → 0, Lynch 2 → 0. O snapshot anterior não traz as evidências históricas exigidas agora. Não é cobertura atual da B3 nem prova ponto no tempo; não mede cinco anos com carteira. Scripts e JSON antes/depois preservados em `outputs/validacao-fase2c/f2c1-universo.*`. A abstenção informa o que falta, sem preço substituto.

## Medição 2.1 atualizada

A medição histórica15→0/2→0 está superada. No mesmo universo inicial de51ativos, com documentos oficiais relidos e preços/perfil do snapshot inicial: Graham15→18; Lynch2→2. Motivos, casos e datas estão no diário e em outputs/validacao-fase2c/f2c1-universo21.json. Não é replayPIT nem cotação atual. A medição intermediária15→14 ocorreu antes de consumir fatoresB3 da relação já coletada; não é o resultado final.

`fatores_acoes_b3.py` normaliza somente as conversões de eventos demonstradas por ManualCâmaraB3 e avisos oficiais citados no módulo. Sem dicionário público identificado para todos os rótulos do JSON, não aplica uma regra universal ao campo factor: desdobramento/bonificação mesmaespécie têm percentual adicional, grupamento já é multiplicativo. Pares compatíveis não exigem eventos; pares incompatíveis exigem evento/fator comprovado e razão residual compatível. Unknown, espécie distinta e bordaCOM ambígua mantêm motivo. A evidência por par e fonte/coleta são preservadas; métodos continuam sem rede.
