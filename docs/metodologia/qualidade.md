# Qualidade descritiva — versão 1.0

**Status:** rascunho de 28/10/2026, aguarda auditoria FICHA pelo Claude e aprovação do Marcos; não implementado.
**Itens que dependem:** F2C-2; apresentação em F2C-3/5. Pacote26/10 §2, ADR-0003 D20–D25/D28. Cinco exercícios, faixas descritivas, **sem nota única, pesos, sigmoide ou alteração de valores de outras lentes**.

## 1. Fórmulas e referências

Proposta de descritores sobre cinco exercícios completos e comparáveis, `t=T−4,…,T`:

\[
ROE_t=Lucro_{controladores,t}/PL_{controladores,inicial,t};\quad
\bar r=\frac{\sum r_t}{N};\quad
\sigma_{pop}=\sqrt{\frac{\sum(r_t-\bar r)^2}{N}};\quad
N_+=\sum1_{Lucro_{controladores,t}>0}.
\]

ROE com PLinicial≤0 fica sem razão interpretável, com motivo; não converter em ROEpositivo pela divisão de dois negativos. O início do primeiro exercício requer BPP de abertura equivalente (pode exigir o documento anual anterior aos cinco); cinco DRE não garantem cinco denominadores. Este denominador é proposta explícita de coerência com as fichas Gordon/bancos, sujeita à ratificação para a lente de qualidade.

Margem consolidada=`Lucro líquido consolidado / Receita líquida consolidada` do mesmo exercício/perímetro, receita>0. Não rotular essa margem como dos controladores. Alavancagem=`Dívida financeira líquida / EBITDA` somente quando ambos estiverem demonstrados no mesmo documento/período e EBITDA>0. Regularidade de proventos=`N de exercícios com provento bruto positivo`, com cobertura integral por exercício demonstrada.

As médias/desvio e contagens têm definição matemática; não são uma regra de que certo ROE ou dívida garante qualidade econômica. Referências de insumos: [ficha por ação1.1](por-acao.md), [Gordon](gordon.md), [bancos](bancos.md), [Bazin1.2](bazin.md), pares código/descrição D20 e dicionários oficiais CVM citados em `docs/decisoes/contrato-insumos-cvm-2c.md`. [IAS33 — IFRS](https://www.ifrs.org/issued-standards/list-of-standards/ias-33-earnings-per-share/) trata lucro por ação; não é fonte de limiares de qualidade. Dívida financeira não é passivo total. A definição/reconciliação do EBITDA deve ter fonte contábil identificada; não inventar EBITDA a partir de um múltiplo de mercado.

## 2. Insumos e separação de perímetros

|Indicador|Fonte e unidade|Conferência obrigatória|
|---|---|---|
|ROE|DRE lucroatribuído e BPPPLatribuído/CVM, razão|Mesma entidade/modelo, PLinicial e janela documentados|
|Lucro positivo|DRE dos controladores, R$|Sinal da conta; zero é observado mas não positivo|
|Margem|DRE consolidada, razão|Numerador e denominador consolidados, não receita total com lucrocontroladores|
|Dívida financeira líquida|BPP/notas conciliadas, R$|Dívida onerosa e caixa disponível no contrato; motivo se rubrica não reconciliada|
|EBITDA|Medida documentada/reconciliada da mesma janela, R$|Não confundir EBIT com EBITDA; dado ausente não vira zero|
|Regularidade de proventos|Relação oficialB3 bruta por data-ex/espécie, janelas anuais correspondentes aos exercícios|Mesma classe/base de ações, eventos oficiais; ausência de resposta não é anozero|

A sérieDVA por competência pode ser mostrada em quadro separado com essa identificação, **sem misturar** anos deDVA e data-exB3 na mesma contagem. O contexto médio de cinco anos de proventos não entra no critérioBazin12meses. Registros devem trazer documento/versão, referência, disponibilidade/coleta e motivos por indicador; não são garantiaPIT só porque há cinco números.

## 3. Regime, janela e faixas

ROE, margem e dívida/EBITDA são razões da mesma moeda/período; não aplicam Selic, desconto ou atualização monetária isolada a um componente. Contagem de lucros usa sinal, não soma moedas de anos diferentes. Se exibir média **monetária** de proventos por ação como contexto, converter os cinco anos para moeda/base final com fatores oficiais, como no rascunhoGraham, com rótulo e sem modificarBazin.

Proposta de faixas **observadas**, sem categorias normativas “boa/ruim”:

- ROE: mínimo–máximo, média, desvio-padrão populacional em pontospercentuais e N/5 válidos.
- Lucro: Npositivos/Nobservados, cobertura Nobservados/5; se cobertura5/5, pode mostrar Npositivosde5. Prejuízo é desempenho observado, ausência é falta de evidência.
- Margem: mínimo–máximo e valor final, com rótulo “consolidada” e cobertura.
- Dívida/EBITDA: faixa de razões válidas e situação do último exercício; todos os casos EBITDA≤0 aparecem separadamente, mesmo fora da faixa numérica.
- Proventos: Nanospositivos/Nanoscomcoberturaintegral e coberturaN/5; sem promover um ano incompleto a ano de ausência de distribuição.

Não há cortes arbitrários10%/20%/3vezes nem pontuação por somar indicadores. As faixas vêm das observações e das fórmulas declaradas; se o produto quiser rótulos econômicos para elas, precisa de outra decisão/fonte, antes do código.

## 4. Escopo e inaplicabilidade

Cinco exercícios completos/contínuos são o alvo da lente. Com histórico menor, entregar **cobertura parcial explicitamente**, sem certificar o quadro de cinco anos e sem inventar valores; classificador que exija o quadro completo se abstém. Não confundir quantidade de dados com mérito empresarial. Mudança estrutural/perímetro sem reconciliação interrompe comparabilidade, registra motivo e preserva os dados brutos; não computar a média atravessando a ruptura.

STOCK/UNIT oficiais com modeloempresa são o escopo principal. Para bancos, ROE/lucro podem ser apresentados com os próprios documentos; margem/debt/EBITDA empresariais são “não aplicáveis ao modelo”, sem scorezero e sem contaminar completude. Seguradoras e modelo ausente não recebem certificação de qualidade por uma inferência de setor; política de extensão exige ficha/decisão, não está implementada aqui. FII tem fontes/contexto próprios, não recebe automaticamente esse quadro empresarial.

|Caso|Saída descritiva proposta|
|---|---|
|Dívida>0, EBITDA≤0|“EBITDA não positivo com dívida financeira líquida positiva”; sem múltiplo, nunca riscozero|
|Dívida≤0, EBITDA≤0|Informar os dois sinais e motivo da razão indisponível; não concluir segurança|
|EBITDAausente|“EBITDA não demonstrado”; sem coerção para zero|
|PLinicial≤0|ROE indisponível por patrimônio não positivo; lucro ePL continuam visíveis|
|Receita≤0/ausente|Margem indisponível com causa própria|
|NaN/infinito/ausência|Dado inválido/ausente com cobertura, não “empresa fraca”|
|Quatro anos comparáveis|Quadroparcial4/5; não quadrocompleto com anozero|

## 5. Exemplo independente e matriz

Cinco exercícios sintéticos: PLinicial100 cada; lucrocontroladores10,12,−2,15,15. ROE10%,12%,−2%,15%,15%; média10%; desvio populacional6,292853089pp; faixa−2% a15%; lucropositivo4de5. Receita consolidada100 cada e lucroconsolidado12,14,−1,16,17→faixa de margemconsolidada−1% a17%; a diferença em relação ao lucrocontroladores é preservada.

Dívida30 eEBITDA10 no ano1→3vezes; no final dívida30 eEBITDA−5→razão indisponível, dívida positiva com EBITDA não positivo explícita. Isso não autoriza calcular uma média de−6vezes e classificá-la como baixa alavancagem. ProventosB3 com cobertura integral em cinco anos e totais1,0,1,2,2→4de5 anos positivos.

```python
from statistics import mean, pstdev
lucros = [10, 12, -2, 15, 15]
roe = [lucro / 100 for lucro in lucros]
print(round(mean(roe) * 100, 8))           # 10.0 %
print(round(pstdev(roe) * 100, 8))         # 6.29285309 pp
print(sum(lucro > 0 for lucro in lucros))  # 4 de 5
```

Matriz futura: controle acima; lucrozero não positivo; PLzero/negativo; receita ausente/zero; dívida>0comEBITDAzero/negativo; dívida negativa comEBITDAnegativo; conta passivototal não substitui dívida; mudança estrutural; histórico4/5; anoB3semfonte vs anozerocomcobertura; banco sem margem/EBITDA; mesma entrada/data alterando apenas juros deve manter TODOS os indicadores de qualidade. Não usar esperado copiado de saída do motor.

## 6. Sensibilidade

Aumentar apenas o último lucrocontroladores15→25, mantendo PL100: médiaROE10%→12%, lucropositivo continua4/5. Retirar o último dado: cobertura4/5 e positivos3/4; não mostrar3/5 como se faltasse lucro naquele ano. Selic/NTN-B maiores, com demonstrações idênticas: nenhum indicador muda. EBITDA10→5 com dívida30: razão3→6, sem mudar o valor das lentes de valuation por efeito automático deste quadro. Na passagemEBITDApositivo→zero, a razão deixa de existir; não aproximar para um número muito grande/pequeno.

## 7. Parâmetros, governança e aprovação

Cinco exercícios: decisão26/10, não janela ajustada para maximizar score. Desvio populacional usaN porque descreve a própria janela, não estima população futura; confirmar essa convenção e PLinicial na auditoriaFICHA. Faixasmin–max são estatísticas observadas, não níveis de classificação econômica. ProventosB3data-ex são proposta coerente com o contextoBazin, com alternativaDVAcompetência separada para ratificação.

Antes de implementar: confirmar cobertura mínima de cada descritor, fonte/reconciliação de EBITDA e dívida, disponibilidade da base inicial e política de quadroparcial. Não há obrigação de inventar um número com ausência de fonte. D24 mantém qualidade empresarial, valuation e qualidade dos dados em blocos separados. F2C-2 não pode alterar valores/preços-limite das lentes existentes; testes e predicado do golden somente após a ficha aprovada.
