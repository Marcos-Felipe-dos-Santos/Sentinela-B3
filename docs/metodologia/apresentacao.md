# Apresentação por lente — versão 1.0

**Status:** aprovada pelo Marcos em 28/10/2026, após auditoria Claude D30. Implementação autorizada na 2C-b conforme as decisões abaixo.
**Itens que dependem:** F2C-3/5/4; histerese entregue como contrato paraF4-2. Pacote26/10 §§1–2/8; ADR-0003 D23–D26/D28/D29. Três dimensões separadas, sem mediana única, nota agregada ou sigmoide.

## 1. Distância ao preço, sem rótulos na 2C

Decisão doMarcos28/10, após a auditoriaClaude bloquear a banda: **não há rótulo por lente na2C**. Cada lente mostra valor ou motivo, hipótese, regime, janela e distância ao preço empercentual:

`distancia_ao_preco_pct = 100 × (valor / preco − 1)`.

É comparação aritmética, não retornoesperado/sinal/recomendação. Lenteabstida→motivo, distânciaausente; não neutro/zero. Não há score de preço, sigmoide, medianaúnica ou classificaçãoagregada. ParaBazin mostrar “atinge / não atinge6%”, DYbruto e preço-limiteinformativo, sem chamar critério de valorjusto.

**Banda e sinais adiados para a Fase3**, com calibração por backtest. A mediana da discordância entre métodos **não** mede incerteza de uma lente contra preço. A candidata33,50% do rascunho foi rejeitada como base de classificação, não aprovada nem implantada.

## 2. Contrato de apresentação e insumos

|Bloco|Conteúdo obrigatório|Não fundir com|
|---|---|---|
|Qualidade empresarial|Descritores/faixas/cobertura de qualidade1.0, dívida/EBITDA≤0 explícito|Upside, score de preço ou taxa de juros|
|Valuation por lente|Nome/versão, hipótese, regime, unidade, janela, documento, V ou motivo, P/data, distância ao preço em%|Mediana/valorúnico/classificação global|
|Qualidade dos dados|Completude por modelo, atualidade, origem, disponibilidade/coleta, reconciliação e motivos|Qualidade econômica ou outra penalização automática|

Não descontar a mesma ausência de dado duas vezes em confiança. Ausência não é perda/prejuízo; valornegativo legítimo daCVM não é incompletude. Não preencher a abstenção por preço, zero, outro método ou outra fonte recusada. Nenhum método inclui banco/seguradora/FII fora do próprio escopo por conveniência visual. Seguradora semlente ou FIIsemrendimento ficam com motivos, sem número/upside.

Uma linha de lente leva: identificador/versão, as_of comfuso, regime/moedabase, valor/unidade ou abstenção, insumos/fontes/documentos utilizados, preço/data, distância ao preço em%, sem banda/rótulo. Mostrar separadamente fonte registrada mas recusada, sem alegar que foi utilizada. Qualidade e dados não são um escore-síntese. Avisos, inclusive cobertura dos pares, continuam visíveis como avisos; não entram numa média de preços.

## 3. Regime, data e escopo

Comparar somente números com unidade equivalente: R$/ação, R$/unit ou R$/cota; mesma base acionária e moeda declarada. Se uma lente anual tem moeda-base anterior ao preço, mostrar a data e seguir a convenção aprovada na ficha correspondente; esta ficha de interface não cria uma atualização/deflação silenciosa. Quando a equivalência não for demonstrada, a distância fica indisponível com motivo, preservando o número de origem quando lícito mostrá-lo como contexto.

Gordon/bancos continuam DFPanual; Bazin12mesesdata-ex; Graham/Lynch dependem dos seus rascunhos aprovados. A comparação entre hipóteses/regimes distintos não autoriza agregação. Com mesma entrada completa e as_of, o resultado calculado é determinístico, sem estado de alertas ou relógio novo no método.

## 4. Evidência histórica da proposta rejeitada

O rascunho sondou10/51casos com versões antigas e perfil simplificado, mediana da semi-amplitude33,49869727%. A auditoriaClaude considerou que discordância entre lentes não é incerteza por lente. OMarcos decidiu não usar essa banda nem sinais na2C. Os artefatos ignorados e o histórico do git preservam a experiência; não há parâmetro de banda em produção. Calibração de classificações somenteFase3, por backtest, com cobertura/viés e validação fora da amostra explícitos.

## 5. Exemplo independente e matriz de aceite

Caso sintéticoV100: P70→distância42,857142857%; P80→25%; P160→−37,5%. Nenhum caso recebe sinalpositivo/neutro/negativo. Vausente→distânciaNone e motivo; Pnão positivo/não finito→motivo, sem número. ParaBazinD6/P100→DY6%, “atinge6%”; D5/P100→5%, “não atinge6%”, sem interpolar sinal; os guardas da fichaBazin continuam válidos.

```python
for preco in [70, 80, 160]:
    print(100 * (100 / preco - 1))
# 42.85714285714286; 25.0; -37.5
```

Matriz:0/1/2/3+lentes; valores/motivos por lente, semsíntese; distânciaNone paraabstenção; unidade/base/moedacompatível; prejuízo≠incompletude; fonteutilizada≠recusada; mesmainput/as_of→mesma saída; sem score/sigmoide/rótulo; legado lido por adaptador com identificaçãohistórica. Fonte é decisão28/10 e aritmética independente, não resultadoV1.

## 6. Sensibilidade

V100/P80 dá25%; V110/P80 dá37,5%; V100/P100 dá0%. O número é distância ao referencial da lente, não estimativa de retorno. Mudar a taxa altera somente lentes que usam essa taxa; não muda indicadores de qualidade por efeito da interface. Regimes diferentes não autorizam agregar valores. Não aplicar banda oculta por cores/ícones/ordenamento de rótulos.

## 7. Histerese — somente contrato F4-2

Separar `resultado_calculado` (lente/versão,as_of,insumos,valoroumotivo,d,sinal,banda/versão) de `estado_alerta` (chave deativo/lente/versão,últimoestado,eventoid,últimoenvio). O método não recebe o estado anterior.

Contrato proposto paraF4-2, parâmetros a aprovar naquela fase: `b_entrada≥b_saida≥0`, política de repetição/cadência e chave de idempotência. Em estado neutro/suspenso, entrarpositivo só comd>b_entrada e negativo só comd<−b_entrada; ao recuperar fonte, reavaliar entrada, não retomar por rótulo antigo. Positivo existente sai para neutro quandod≤b_saida, negativo sai quandod≥−b_saida. Se numa observação cruzar diretamente a banda oposta deentrada, produzir uma única transição para o oposto, sem dois envios duplicados. Dentro da zona de retenção do mesmoestado, não emitir novaentrada; repetição só pela políticaF4aprovada, com eventoididempotente. Lenteabstida→suspender alerta e preservar motivo, não emitir sinalnegativo. Histórico guarda resultado e transição separadamente.

Nenhum valor de b_saida, prazo ou número de repetições é implantado/escolhido aqui. Datas futuras/fonteatrasada e revisão de documento exigem regras de disponibilidade e idempotênciaF4/D16; não usar relógio no cálculo de valuation. Sem estado/persistência de alerta no motor ou SQLite nesta metade.

## 8. Compatibilidade e decisões aprovadas

No fluxo2C, vocabulário “distância ao preço”, sem rótulo por lente. O adaptador de leitura conserva rótulo/scorelegados como resultadohistórico identificado, sem fingir recálculo, sem reinterpretá-los como distância e sem migrarSQLite. Não emitir sinaisnovos a partir de rótulos antigos. Schema/backup/restauraçãoD29 ficamFase3.

F2C-3retira sigmoide/classificaçãoagregada e preserva valor/motivo/distânciaporlente; F2C-4troca vocabulário legado nos consumidores e mantém adaptador de leitura; F2C-5integra lentesseparadas eBazincomo critério. Histerese somentecontratoF4-2na seção7, sem estado/relógio no motor. AuditoriaClaude+decisõesexpressasdoMarcos28/10fecham as pendências deste documento. Implementação deve enumerar predicados de golden e manter fontes/regimes/janelas visíveis.
