# Graham — versão 2.1

**Status:** versão 2.1 aprovada expressamente pelo Marcos em 28/10/2026 para resolver o bloqueio do F2C-1. Substitui as exigências de reconciliação estrutural e cobertura de eventos da 2.0; mantém suas demais decisões, após auditoria Claude D30.
**Itens que dependem:** F2C-1 e consumidores autorizados da 2C-b. D19–D25/D28. Direção aprovada: pacote de 26/10, §3, em `docs/decisoes/decisoes-2c.md` e fila; detalhes ratificados em 28/10/2026.

## 1. Fórmula e referência

Para cinco exercícios completos e contínuos, com LPA comparável na base acionária final:

\[
L_t^{T}=L_t\,A_{t,T}\frac{I_T}{I_t},\quad
\overline L=\frac{1}{5}\sum_{t=T-4}^{T}L_t^{T},\quad
V_G=\sqrt{22,5\,\overline L\,VPA_T}.
\]

`A` ajusta a quantidade por ação por eventos oficiais; não corrige a moeda. `I` é o índice IPCA. Prejuízos anuais entram com sinal, não são descartados da média. O resultado é um referencial heurístico em R$/ação ou R$/unit, não avaliação por fluxo descontado.

Referência primária: Benjamin Graham, *The Intelligent Investor*, 4ª edição revista, capítulos12 e14, pp.319 e348–349 na paginação impressa, [texto consultado](https://sims.sairam.edu.in/wp-content/uploads/sites/7/2024/03/THE-INTELLIGENT-INVESTOR.pdf). O capítulo12 discute média plurianual; o14 relaciona múltiplos de lucro e patrimônio, cujo produto22,5 corresponde a15×1,5. O texto do14 usa três anos; o12 discute períodos mais longos. **Cinco exercícios e correção por IPCA são adaptações aprovadas do projeto**, não uma janela atribuída literalmente a Graham/Dodd. Não usar a fórmula de crescimento8,5+2g como substituta desta lente.

A identidade algébrica vem de `(P/L)×(P/VPA)=P²/(L×VPA)`. Ela explica22,5, não demonstra a precisão econômica da heurística nem permite aplicá-la a qualquer setor.

## 2. Insumos

| Insumo | Definição/fonte | Unidade e referência |
|---|---|---|
|LPA anual|Controladores, classe do ticker, DRE consolidada da CVM; divulgado ou reserva marcada conforme [por ação1.1](por-acao.md), cada exercício com o próprio documento|R$/ação; exercício completo, versão elegível até as_of|
|Ações e classes|Composição do Capital/FCA do documento; unit soma espécies com composição oficial; direitos distintos seguem abstenção da ficha por ação|Quantidade/espécie; não shares_outstanding atual aplicado retroativamente|
|`A(t,T)`|Ajuste acumulado até a base final: razão de ações de documentos consecutivos em (0,9; 1,1) dispensa ajuste; fora, exige fator oficial B3. Fator q de novas por antigas divide o LPA antigo por q|Adimensional; limites estritos e escala própria de cada documento pela ficha por ação 1.1|
|`I_t`,`I_T`|Índices relativos no mês final de cada exercício, pelo produto dos fatores mensais do IPCA oficial IBGE/SIDRA 1737, variável 63, estendendo o produtor existente aos cinco exercícios|Mesma base; fatores positivos e cobertura mensal completa, com corte pelo calendário de publicação do IBGE|
|VPA final|PL dos controladores/ações do documento final, por classe/unit segundo a ficha por ação|R$/ação ou unit, moeda finalT|
|Preço|FechamentoD-1 da cascata, apenas comparação/apresentação; guardas legadas retiradas por decisão28/10|R$/mesma unidade, data/fonte explícitas|

O índice do fim do exercício é uma **convenção aprovada em 28/10/2026** de normalização dos lucros anuais; não promete corrigir cada receita intranual como uma reapresentação contábil. A ficha de taxa real e o catálogo IBGE já usados pelo projeto fornecem o produtor de IPCA; este rascunho não cria outro coletor.

## 3. Regime, janela e data

Média nominal na moeda do encerramento deT: não é média em moedas de poder aquisitivo diferente. Não deflacionar novamente o VPA final nem descontar o resultado por Selic/NTN-B. Cinco exercícios não significam60meses arbitrários: usar os inícios/fins documentados, inclusive exercício não civil. Escolher versões pela disponibilidade demonstrada em as_of, não a maior versão disponível hoje. Menos de cinco exercícios completos/contínuos abstém, sem anualizar TTM para preencher lacuna. Gordon/bancos continuam DFP anual; Bazin mantém12meses por data-ex, sem mudar por esta ficha.

Compatibilidade acionária aprovada na 2.1: comparar, entre cada par de exercícios consecutivos, as ações em circulação da Composição do Capital, líquidas de tesouraria e convertidas pela escala de cada documento segundo a ficha por ação 1.1. A razão quantidade posterior ÷ anterior estritamente em (0,9; 1,1) demonstra ausência de desdobramento/grupamento nesse par. Fora do intervalo, ajustar pelo fator oficial da B3 quando existir; sem fator oficial, abster com motivo. Acumular os fatores entre cada exercício e o último antes da média. Quantidade ou escala indisponível não demonstra compatibilidade. Esta regra substitui a exigência anterior de cobertura oficial de todos os eventos da janela.

Reorganização societária, fusão, cisão e mudança de perímetro não são detectadas nesta fase: incluir sempre o aviso **"reorganização societária no período não é detectada"**, sem provocar abstenção por esse motivo. A detecção tem destino na **Fase 3**, com fonte e contrato próprios antes da implementação. Direitos de classe/unit continuam seguindo a ficha por ação; não inventar composição. Evento acionário e atualização monetária continuam operações separadas, com proveniência separada.

## 4. Hipóteses e abstenções

Escopo: STOCK/UNIT oficiais com modeloBPP empresa. Banco, seguradora, FII e identidade/modelo ausentes seguem seus motivos próprios; esta ficha não os inclui na heurística.

| Caso | Resultado proposto |
|---|---|
|Cinco exercícios válidos, média positiva e VPApositivo|Referencial pela fórmula|
|LPA de um exercício negativo, mas média positiva|Preservar sinal na média; qualidade descreve prejuízo, não o apaga|
|Média≤0 ou VPA≤0|Abster: média de lucro ou patrimônio não positivo|
|Ausente, NaN/infinito, índice≤0 ou lacuna temporal|Abster com campo/mês/documento faltante; não preencher zero|
|Quantidade/escala não demonstrada, ou razão fora de (0,9; 1,1) sem fator oficial B3|Abster: compatibilidade da base acionária não demonstrada, com motivo por par de documentos|
|Reorganização societária/perímetro|Aviso fixo, sem abstenção; detecção na Fase 3|
|Documento ou IPCA divulgado após as_of|Não usar a revisão futura; abster se não restar cobertura elegível|

## 5. Exemplo independente e matriz de aceite

Companhia sintética, mesma classe e base acionária compatível, cinco LPA1,2,3,4,5. Fatores monetários1,20;1,15;1,10;1,05;1,00. Valores normalizados1,20;2,30;3,30;4,20;5,00, soma16, média3,20. VPAfinal20. Resultado `sqrt(22,5×3,20×20)=37,9473319220`. Dados são sintéticos e fatores escolhidos só para mostrar aritmética; não uma série IPCA real.

```python
from decimal import Decimal as D, getcontext
getcontext().prec = 28
lpa = list(map(D, ['1', '2', '3', '4', '5']))
fatores = list(map(D, ['1.20', '1.15', '1.10', '1.05', '1']))
media = sum(x * f for x, f in zip(lpa, fatores)) / D(5)
valor = (D('22.5') * media * D(20)).sqrt()
print(media, valor)  # 3.20, 37.94733192202055198398672253
```

Não importa nenhum motor/método do projeto. Esse exemplo é o esperado independente do F2C-1.

Matriz de aceite: controle acima; quatro exercícios→abstenção; exercício não civil completo→mesma regra; trimestre/TTM no lugar deDFP→não preenche; LPA[-1,2,3,4,5] com fatores iguais→média2,6; médiazero/negativa→abstenção; VPAzero/negativo→abstenção; split2:1→LPAantigo dividido por2 antes da moeda; razão fora do intervalo sem fator oficial→abstenção; IPCAfaltante/futuro→abstenção; duasPN sem direito reconciliado→abstenção; unit→soma ponderada oficial, sem inferir pelo sufixo. Comparar todas as lentes não alteradas com o golden anterior, sem regenerá-lo neste rascunho.

## 6. Sensibilidade

| Mudança isolada | Resultado sintético |
|---|---:|
|Base|37,947332|
|Média ou VPA +10%|39,799497|
|Média ou VPA −10%|36,000000|
|Ambos +10%|41,742065|

Elasticidade deV em cada fator positivo é1/2. Uma distribuição societária que reduza PL ou uma mudança estrutural não pode ser representada simplesmente por essa elasticidade; nesta fase o aviso fixo explicita a ausência de detecção. A média atenua um exercício extraordinário, mas não garante sustentabilidade.

## 7. Decisões aprovadas e implementação

Marcos,28/10/2026, após auditoriaClaude: cinco exercícios completos contínuos, LPA de cada documento ajustado por fator oficial e IPCA do **fim de cada exercício**, VPA do último. Retirar o pisoP/L7 e as guardasP/L25 e P/VP2,5/3. O limite heurístico é a própria fórmula22,5=15×1,5; não reconstruir o lucro por preço/P/L, nem aplicar os tetos legados como elegibilidade. PLde mercado não é insumo desta versão. Média≤0/VPA≤0 e insumo/base acionária não demonstrados continuam abstenções. A decisão 2.1 substitui a abstenção por perímetro pelo aviso fixo de reorganização.

Esta aprovação resolve as pendências do rascunho sobre piso, guardas e convençãoIPCA. Não altera as fichas Gordon/bancos/Bazin. No F2C-1, enumerar antes→depois e predicado de cada mudança no golden, com testes independentes de histórico curto, prejuízo, eventos, IPCA e VPA. Auditoria original: relatório Claude `auditoria-2c-a-final-e-fichas-claude-relatorio.md`, decisões expressas do Marcos em28/10.


## 8. Compatibilidade da base — exemplo e matriz da 2.1

Exemplo sintético: quantidades em unidades 100, 100, 200, 200, 200 e LPA 2, 2, 1, 1, 1. As razões consecutivas são 1; 2; 1; 1. Um desdobramento oficial B3 2:1 entre o segundo e o terceiro exercício divide por 2 os dois LPA anteriores. Todos os LPA na base final ficam 1; a média é 1 com IPCA constante. Com VPA final 20, `sqrt(22,5 × 1 × 20) = 21,2132034356`. Sem o fator oficial para o par de razão 2, há abstenção. Uma quantidade documental 0,1 em escala de mil equivale a 100 unidades; comparar apenas após essa conversão.

| Razão posterior/anterior ou caso | Resultado |
|---|---|
|1; 0,900001; 1,099999|Compatível, fator de ajuste 1 para o par|
|0,9 ou 1,1 exatos|Fora do intervalo; fator oficial B3 obrigatório|
|2 com fator oficial 2:1|Dividir LPA anteriores por 2, acumulando os ajustes até o último exercício|
|0,5 com fator oficial 1:2|Dividir LPA anteriores por 0,5|
|2 sem fator oficial, ou fator inválido|Abster com motivo; não usar a razão como fator presumido|
|Quantidade ausente/não positiva ou escala indeterminada|Abster com motivo, mesmo com LPA divulgado|
|Escalas documentais distintas, ambas demonstradas|Comparar quantidades convertidas em unidades|
|Fusão/cisão/perímetro não detectados|Exibir aviso fixo, sem abstenção por reorganização|
|IPCA mensal faltante ou não publicado até as_of|Abster Graham com motivo; não afetar o Lynch nominal|
