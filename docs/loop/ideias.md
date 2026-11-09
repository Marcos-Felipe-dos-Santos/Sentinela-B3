# Ideias

Regra (pacote de processo F3-0, P4, aprovado pelo Marcos em 09/11/2026): ideia nova não entra em fila ativa. Ela é registrada aqui, com data, e só é avaliada num checkpoint. Uma ideia aprovada no checkpoint vira item da proposta da fila seguinte; enquanto isso, não é trabalho do loop.

## Entradas

**Análise offline com resumo histórico (09/11/2026).** Uso derivado, para um projeto de terceiro: rodar a análise sem rede sobre um snapshot local e gerar um resumo histórico por ativo, sem compra nem venda. O que a Fase 3 já cobre: `as_of`, ponto-no-tempo, eventos societários, deslistadas e banco único. Falta avaliar: critério "sem rede na análise" (hoje o F3-1 trata o import); modo offline que falha fechado; manifesto e verificação do snapshot; cópia local do backup (o F4-5 envia para o Google Drive); instalação sem rede; resumo com carimbo "dados até X" em modo estrito (D17). Destino provável: proposta da Fase 4. Fora do repositório: formato dos dados do terceiro, frequência de atualização, critério de aceite e responsabilidade pelo uso.
