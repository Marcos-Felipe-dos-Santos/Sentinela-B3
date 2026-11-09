# Lynch — versão 2.1

**Status:** versão 2.1 aprovada expressamente pelo Marcos em 28/10/2026 para resolver o bloqueio do F2C-1. Substitui as exigências de reconciliação estrutural e cobertura de eventos da 2.0; mantém suas demais decisões, após auditoria Claude D30.
**Itens que dependem:** F2C-1 e F2C-12, depois F2C-3/5. D19–D25/D28; pacote26/10 §§3–4. Nenhum resultado de outro método é preenchido artificialmente para compensar abstenção.

## 1. Fórmula e referência

Proposta de substituição do crescimento sustentável instantâneo pelo crescimento histórico do LPA dos controladores, em mesma classe/base acionária:

\[
g_{hist}=\left(\frac{LPA_T^{aj}}{LPA_{T-n}^{aj}}\right)^{1/n}-1,
\quad g_{usado}=\min(g_{hist},g_{max}),
\quad PL_{ref}=100g_{usado},
\quad V_L=LPA_T^{aj}\,PL_{ref}.
\]

`n` é o número de **intervalos anuais**, não a contagem de observações. A seção3 registra a contagem aprovada pelo Marcos. Valores monetários ajustados aqui são por evento societário, **não por IPCA**: esta é uma heurística de crescimento nominal. Não descontar por taxa real nem misturar CAGR real com múltiplo nominal.

Referência bibliográfica primária: Peter Lynch e John Rothchild, *One Up on Wall Street*, cap.13, “Some Famous Numbers”, ediçãoSimon&Schuster2000, ISBN9780743200400; [página oficial da editora e trecho disponibilizado](https://www.simonandschuster.com/books/One-Up-On-Wall-Street/Peter-Lynch/9780743200400). A referência é a relação P/L–crescimento, não os antigos parâmetros1,5/25%/35 do projeto. A página pública consultada não fornece o capítulo13 integral: a decisão expressa do Marcos fixa m=1; não se atribui ao relatório uma conferência bibliográfica não registrada, sem alegar página ou citação literal não acessada. A expressão de CAGR é a identidade de capitalização `L_T=L_0(1+g)^n`, resolvida para g; sua aritmética independe da implementação.

**Distinção essencial:** crescimento já observado do LPA não deve ser multiplicado novamente por retenção como se fosse `ROE×(1−payout)`. A proposta abaixo usa payout como indicador contextual da mesma fonte do perfil. Em28/10 oMarcos aprovou payout apenas como contexto e m=1, teto de g25%, sem P/Lmáximo.

## 2. Insumos

| Insumo | Definição e fonte | Unidade/data |
|---|---|---|
|LPA de cada exercício|Lucro dos controladores por classe, DRE consolidada/CVM, conforme [por ação1.1](por-acao.md); cada exercício com seu próprio documento e proveniência|R$/ação ou unit; período completo e versão disponível no corte|
|Base acionária|FCA/Composição do Capital do documento e fator oficialB3; unit por composição oficial, direitos dePN reconciliados|Mesma base final; splitq:1 divide o LPA antigo porq|
|Preço|FechamentoD-1 da cascata, na mesma escala da ação/unit|R$/unidade e data/fonte explícitas|
|DY do perfil e payout|RelaçãoB3 bruta12meses quando válida; se inválida, **ambos** usam o DY válido da cascata com o mesmo aviso/motivoB3|Razão, zero válido é dado; não “ausência”|
|Payout contextual|`DY_fonte_comum × preço_de_referência / LPA_T`; preço da mesma referência do DY, não preço intradiário distinto|Razão, fonte/intervalo explícitos; não é automaticamente payout contábilDVA|
|ROE do perfil|Controladores/CVM segundo contrato vigente; não estimado do preço|Razão e documento; não entra como g na fórmula proposta|

B3 e cascata inválidas→perfil não demonstrado e abstenção deLynch; não inventarDYzero. O índice de ativos e o modeloBPP delimitam escopo; código de ticker não demonstra classe/modelo.

## 3. Regime, janela e data — decisão aprovada

Marcos28/10: **cinco observações e quatro intervalos anuais**, expoente1/4. Para2021–2025, início2021 e fim2025; não chamar os quatro intervalos de cinco anos decorridos. Exercícios completos contínuos e encerramentos correspondentes, inclusive não civis. Menos de cinco observações, lacuna temporal, base acionária não demonstrada ou razão de ações fora de (0,9; 1,1) sem fator oficial B3→abstenção. Não preencher comTTM.

LPA dos controladores por documento/classe, ajustado à base final: comparar ações em circulação da Composição do Capital de cada par de exercícios consecutivos, líquidas de tesouraria e convertidas pela escala própria da ficha por ação 1.1. Razão posterior ÷ anterior estritamente em (0,9; 1,1) demonstra ausência de desdobramento/grupamento; fora do intervalo, usar fator oficial B3 ou abster com motivo. Não converter a razão observada em fator presumido. Acumular os fatores oficiais para trazer cada LPA à base final. O CAGR é nominal: não corrigir um extremo porIPCA nem misturá-lo com taxa real. Documentos e fatores devem estar disponíveis até as_of. Gordon/bancos continuam DFPanual e Bazin12mesesdata-ex.

Exibir sempre o aviso **"reorganização societária no período não é detectada"**, sem abstenção por fusão, cisão ou mudança de perímetro. A detecção tem destino na **Fase 3**, com fonte e contrato próprios antes da implementação. Direitos de classe/unit continuam seguindo a ficha por ação.

## 4. Perfil, hipóteses e inaplicabilidade

Escopo: STOCK/UNIT oficiais, modeloBPPempresa e perfil crescimento demonstrado. A regra vigente do perfil é ROE>20% **e** DY<4% confiável; não é um “ou”. A decisão sobre fonte comum não altera esses dois limites automaticamente. Perfilrenda→Lynch se abstém; ausência simultânea deLynch/Bazin permanece ausência.

| Caso | Tratamento proposto |
|---|---|
|LPAinicial ou final≤0|Abster: CAGR sem extremos positivos|
|Exercício intermediário com prejuízo|Informar na qualidade; manter somente se série/base acionária comparáveis. Não pode desaparecer da cobertura. Tratamento aprovado pelo Marcos28/10|
|g≤0|Abster: crescimento histórico não positivo; não fabricar múltiplo/preçozero|
|Cinco observações sem um exercício, fator ou fonte|Abster com motivo específico; TTM não preenche|
|B3zero válido, cascata5%|Usarzero para perfil **e** payout; não substituir pelo5%|
|B3<4%, ROE>20%, cascata não confiável|MesmaB3 válida para ambos; não recusar só pela fonte que não foi usada|
|B3inválida, cascata válida|AvisoB3 + perfil/payout da cascata|
|Ambas inválidas ou perfil não demonstrado|Abster, sem preencher outro método|

O payout mostrado deve ser bruto e sem truncamento no contexto. Se ultrapassar100%, mostrar o fato; não converter em retenção que modifique retroativamente o CAGR. Não há guarda adicional de elegibilidade por payout nesta versão aprovada.

## 5. Exemplo independente e matriz de aceite

Série sintética2021–2025:1;1,2;1,44;1,728;2,0736. Quatro intervalos; sem evento, classe/perímetro constantes. `g=(2,0736/1)^(1/4)−1=20%`. Com m1, teto de g25% e sem P/Lmáximo, aprovados em28/10: múltiplo20 e referencial `2,0736×20=41,472`. Preço30, DYcomum2%→payout contextual0,6/2,0736≈28,94%; o CAGR continua20%.

```python
from decimal import Decimal as D, getcontext
getcontext().prec = 28
n = D(4)  # cinco observações anuais
lpa0, lpaT = D(1), D('2.0736')
g = (lpaT / lpa0) ** (D(1) / n) - D(1)
pl_ref = min(g, D('.25')) * 100
print(g, lpaT * pl_ref)  # 0.20; 41.472
```

Não importa projeto. Se a janela for cinco intervalos com crescimento20%, usar sexto LPA2,48832, e não o mesmo par com expoente trocado.

Matriz de aceite: extremoszero/negativos/NaN→abstenção; lacuna anual→abstenção; splitoficial2:1→ajuste antes doCAGR; razão fora do intervalo sem fator oficial→abstenção; exemplo nominal e controle que deliberadamente aplicaIPCA a um extremo devem divergir (recusar regime misto); os quatro casos de fonte/perfil da seção4; controlemúltiplos direitos/semBPP/seguradora→abstenção; perda deLynch eBazin→ambos ausentes. Testes da2C-b serão escritos da ficha aprovada, não do resultadoV1.

## 6. Sensibilidade independente

Manter LPAfinal2,0736 e mudar a taxa como ensaio de premissa, sem afirmar que o mesmo histórico gera taxas diferentes:

|g informado|P/L pela proposta|Referencial|
|---:|---:|---:|
|10%|10|20,736|
|20%|20|41,472|
|25%|25|51,84|
|40%|25 (teto de g)|51,84|

Abaixo dos tetos, V varia linearmente com LPAfinal e g. Partir de lucro inicial muito pequeno pode inflar CAGR mesmo quando ambos extremos são positivos; mostrar extremos/cobertura e aviso de base pequena, sem criar limiar numérico arbitrário para esse aviso. Desconto real e rendimento nominal fixo são lentes distintas; não tirar mediana com esta heurística.

## 7. Parâmetros e decisões aprovadas

Marcos28/10: cinco observações/quatrointervalos; **m=1**, como a relação P/L=crescimento da regra do livro; gmax25%; **sem P/Lmáximo**; payout somentecontexto, usando a mesma fonte do perfil; prejuízo intermediário permitido com extremospositivos. Excluir as hipóteses legadasm1,5/PLmáximo35 e não reaplicar retenção aoCAGR. Não excluir um exercício negativo intermediário da cobertura nem introduzir piso de crescimento.

Fonte comumDY: B3válida (inclusivezero) para perfil e payout; caso contrário cascata válida com o mesmo aviso/motivo. Perfilcrescimento continua ROE>20% e DY<4% confiável; oMarcos não alterou os dois limites do perfil. F2C-12 deverá provar os quatro casos de fonte e ausência legítima de lentes, sem preencher números. O esperado independente aprovado passa de62,208 no rascunho para **41,472**, pelo m=1. Registrar o predicado do golden antes de mudar números/abstenções; não usar esperadoV1.


## 8. Compatibilidade da base — exemplo e matriz da 2.1

Exemplo sintético: ações em unidades 100, 100, 200, 200, 200; LPA 2; 2,4; 1,44; 1,728; 2,0736. As razões são 1; 2; 1; 1. Com fator oficial B3 2:1 no segundo par, dividir os dois primeiros LPA por 2: a série final é 1; 1,2; 1,44; 1,728; 2,0736, CAGR nominal de 20% e referencial 41,472. Sem o fator oficial há abstenção; o aumento observado de ações não é usado como substituto do fator. IPCA não participa de nenhum passo do Lynch.

| Razão posterior/anterior ou caso | Resultado |
|---|---|
|1; 0,900001; 1,099999|Compatível, fator 1 para o par|
|0,9 ou 1,1 exatos|Fora do intervalo; exige fator oficial B3|
|2 com fator oficial 2:1|LPA dos exercícios anteriores dividido por 2 antes do CAGR|
|0,5 com fator oficial 1:2|LPA dos exercícios anteriores dividido por 0,5|
|Fator oficial ausente/inválido fora do intervalo|Abster com motivo|
|Quantidade ausente/não positiva ou escala indeterminada|Abster com motivo, sem usar ações atuais retroativamente|
|Escalas documentais distintas, ambas demonstradas|Comparar quantidades convertidas para unidades pela regra por ação 1.1|
|Reorganização/perímetro não detectados|Aviso fixo, sem abstenção por esse motivo; detecção na Fase 3|
|IPCA indisponível|Não altera Lynch: série e CAGR permanecem nominais|
