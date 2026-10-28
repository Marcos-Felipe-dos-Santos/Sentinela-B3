# Graham — versão 2.0

**Status:** rascunho de 28/10/2026, aguarda auditoria FICHA pelo Claude e aprovação do Marcos. Não implementado. A ficha 2.0 não é a versão do método atualmente registrado (1.2.0).
**Itens que dependem:** F2C-1 e consumidores autorizados da 2C-b. D19–D25/D28. Direção aprovada: pacote de 26/10, §3, em `docs/decisoes/decisoes-2c.md` e fila; detalhes propostos abaixo ainda não são decisões aprovadas.

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
|`A(t,T)`|Fator oficial acumulado de desdobramento/grupamento até a baseT; fatorq de novas por antigas implica dividir o LPA antigo porq|Adimensional; sem fator demonstrado, não assumir1|
|`I_t`,`I_T`|IPCA mensal oficial IBGE/SIDRA, agregado1737, número-índice no mês final de cada exercício; equivalência por produto dos fatores mensais quando a cobertura é completa|Mesmo índice/base; valores positivos, publicados até o corte|
|VPA final|PL dos controladores/ações do documento final, por classe/unit segundo a ficha por ação|R$/ação ou unit, moeda finalT|
|Preço|FechamentoD-1 da cascata, apenas comparação/apresentação e guardas legadas em discussão|R$/mesma unidade, data/fonte explícitas|

O índice do fim do exercício é uma **convenção proposta** de normalização dos lucros anuais; não promete corrigir cada receita intranual como uma reapresentação contábil. A ficha de taxa real e o catálogo IBGE já usados pelo projeto fornecem o produtor de IPCA; este rascunho não cria outro coletor.

## 3. Regime, janela e data

Média nominal na moeda do encerramento deT: não é média em moedas de poder aquisitivo diferente. Não deflacionar novamente o VPA final nem descontar o resultado por Selic/NTN-B. Cinco exercícios não significam60meses arbitrários: usar os inícios/fins documentados, inclusive exercício não civil. Escolher versões pela disponibilidade demonstrada em as_of, não a maior versão disponível hoje. Menos de cinco exercícios completos/contínuos abstém, sem anualizar TTM para preencher lacuna. Gordon/bancos continuam DFP anual; Bazin mantém12meses por data-ex, sem mudar por esta ficha.

Mudança de exercício, fusão/cisão, reorganização ou alteração de direitos exige reconciliação documentada. Igualdade de CNPJ/modelo ou existência de cinco linhas não a demonstra. Evento de cota/ação e atualização monetária são operações separadas, com proveniência separada. A ausência de evento somente pode ser assumida com cobertura oficial demonstrada para a janela (levantamento F2C-22), não porque a resposta falhou.

## 4. Hipóteses e abstenções

Escopo: STOCK/UNIT oficiais com modeloBPP empresa. Banco, seguradora, FII e identidade/modelo ausentes seguem seus motivos próprios; esta ficha não os inclui na heurística.

| Caso | Resultado proposto |
|---|---|
|Cinco exercícios válidos, média positiva e VPApositivo|Referencial pela fórmula|
|LPA de um exercício negativo, mas média positiva|Preservar sinal na média; qualidade descreve prejuízo, não o apaga|
|Média≤0 ou VPA≤0|Abster: média de lucro ou patrimônio não positivo|
|Ausente, NaN/infinito, índice≤0 ou lacuna temporal|Abster com campo/mês/documento faltante; não preencher zero|
|Fator oficial, direitos ou reconciliação não demonstrados|Abster: base acionária/perímetro não comparável|
|Documento ou IPCA divulgado após as_of|Não usar a revisão futura; abster se não restar cobertura elegível|

## 5. Exemplo independente e matriz de aceite

Companhia sintética, mesma classe e sem evento, cinco LPA1,2,3,4,5. Fatores monetários1,20;1,15;1,10;1,05;1,00. Valores normalizados1,20;2,30;3,30;4,20;5,00, soma16, média3,20. VPAfinal20. Resultado `sqrt(22,5×3,20×20)=37,9473319220`. Dados são sintéticos e fatores escolhidos só para mostrar aritmética; não uma série IPCA real.

```python
from decimal import Decimal as D, getcontext
getcontext().prec = 28
lpa = list(map(D, ['1', '2', '3', '4', '5']))
fatores = list(map(D, ['1.20', '1.15', '1.10', '1.05', '1']))
media = sum(x * f for x, f in zip(lpa, fatores)) / D(5)
valor = (D('22.5') * media * D(20)).sqrt()
print(media, valor)  # 3.20, 37.94733192202055198398672253
```

Não importa nenhum motor/método do projeto. Esse exemplo poderá virar esperado no F2C-1 somente depois de aprovar os detalhes da ficha.

Matriz futura: controle acima; quatro exercícios→abstenção; exercício não civil completo→mesma regra; trimestre/TTM no lugar deDFP→não preenche; LPA[-1,2,3,4,5] com fatores iguais→média2,6; médiazero/negativa→abstenção; VPAzero/negativo→abstenção; split2:1→LPAantigo dividido por2 antes da moeda; fator ausente→abstenção; IPCAfaltante/futuro→abstenção; duasPN sem direito reconciliado→abstenção; unit→soma ponderada oficial, sem inferir pelo sufixo. Comparar todas as lentes não alteradas com o golden anterior, sem regenerá-lo neste rascunho.

## 6. Sensibilidade

| Mudança isolada | Resultado sintético |
|---|---:|
|Base|37,947332|
|Média ou VPA +10%|39,799497|
|Média ou VPA −10%|36,000000|
|Ambos +10%|41,742065|

Elasticidade deV em cada fator positivo é1/2. Uma distribuição societária que reduzaPL ou uma mudança estrutural não pode ser representada simplesmente por essa elasticidade: exige tratamento documental. A média atenua um exercício extraordinário, mas não garante sustentabilidade.

## 7. Parâmetros, compatibilidade e perguntas de auditoria

- Cinco exercícios: decisão doMarcos26/10, não calibração para elevar valores.22,5: relação histórica15×1,5; IPCA: normalização monetária brasileira proposta no pacote.
- **Ponto para ratificação FICHA:** fórmula proposta usa diretamente a média corrigida, sem reconstruir lucro por preço/P/L nem aplicar o pisoP/L7 que altera o LPA naV1. Não implementar a retirada desse piso sem aprovação expressa da ficha e enumeração do predicado do golden.
- Guardas legadas P/L25 e P/VP2,5/3 por perfil não são justificadas pelo simples uso de cinco exercícios. Antes do código, Marcos/Claude devem decidir se permanecem como elegibilidade separada ou se saem. Nenhum número foi escolhido aqui como novo limite. Sem essa ratificação não há contrato completo para alterar esses predicados.
- Confirmar convenção de índice de fim de exercício versus média anual, reconciliação de eventos e disponibilidade histórica. Essas pendências não são resolvidas pelo exemplo aritmético.
- Impacto2C-b: mudar somente ações/units em que a janela/normalização/regra explicitamente aprovada mudar. Publicar antes→depois e motivos, versões e fontes por lente. Sem implementação enquanto a ficha estiver emrascunho.
