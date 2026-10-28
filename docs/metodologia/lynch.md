# Lynch — versão 2.0

**Status:** rascunho de 28/10/2026, aguarda auditoria FICHA pelo Claude e aprovação do Marcos. Não implementado. O método vigente é1.1.0; número da ficha não muda registro por si só.
**Itens que dependem:** F2C-1 e F2C-12, depois F2C-3/5. D19–D25/D28; pacote26/10 §§3–4. Nenhum resultado de outro método é preenchido artificialmente para compensar abstenção.

## 1. Fórmula e referência

Proposta de substituição do crescimento sustentável instantâneo pelo crescimento histórico do LPA dos controladores, em mesma classe/base acionária:

\[
g_{hist}=\left(\frac{LPA_T^{aj}}{LPA_{T-n}^{aj}}\right)^{1/n}-1,
\quad g_{usado}=\min(g_{hist},g_{max}),
\quad PL_{ref}=\min(m\,100g_{usado},PL_{max}),
\quad V_L=LPA_T^{aj}\,PL_{ref}.
\]

`n` é o número de **intervalos anuais**, não a contagem de observações. A tabela da seção3 resolve a ambiguidade para auditoria antes do código. Valores monetários ajustados aqui são por evento societário, **não por IPCA**: esta é uma heurística de crescimento nominal. Não descontar por taxa real nem misturar CAGR real com múltiplo nominal.

Referência bibliográfica primária: Peter Lynch e John Rothchild, *One Up on Wall Street*, cap.13, “Some Famous Numbers”, ediçãoSimon&Schuster2000, ISBN9780743200400; [página oficial da editora e trecho disponibilizado](https://www.simonandschuster.com/books/One-Up-On-Wall-Street/Peter-Lynch/9780743200400). A referência é a relação P/L–crescimento, não os parâmetros1,5/25%/35 deste projeto. A página pública consultada não fornece o capítulo13 integral: a conferência desse capítulo pelo auditor/livro permanece necessária, sem alegar página ou citação literal não acessada. A expressão de CAGR é a identidade de capitalização `L_T=L_0(1+g)^n`, resolvida para g; sua aritmética independe da implementação.

**Distinção essencial:** crescimento já observado do LPA não deve ser multiplicado novamente por retenção como se fosse `ROE×(1−payout)`. A proposta abaixo usa payout como indicador contextual da mesma fonte do perfil. Ratificar essa função do payout e os multiplicadores antes do F2C-12; a direção aprovada não autoriza silenciosamente uma nova transformação econômica.

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

## 3. Regime, janela e data — questão de contagem explícita

A decisão26/10 diz “CAGR de5anos” e exige pelo menos cinco exercícios completos contínuos. Cinco observações2021–2025 contêm **quatro intervalos anuais**; cinco intervalos2020–2025 exigem seis observações. Dividir por5 usando apenas2021/2025 daria taxa incorreta para aquelas datas.

| Alternativa para aprovação | Dados exigidos | Expoente |
|---|---|---|
|Proposta principal: janela de cinco exercícios,2021–2025|5observações completas/contínuas|1/4|
|Se Marcos confirmar cinco anos decorridos,2020–2025|6observações completas/contínuas|1/5|

**Pendente de ratificação FICHA:** preferir a primeira leitura porque coincide com a cobertura de cinco exercícios explicitamente exigida, mas não chamar quatro intervalos de cinco anos decorridos. O exemplo usa a primeira e declara isso. Nenhuma das alternativas é implementada antes da confirmação. Para exercício não civil, usar encerramentos correspondentes de períodos completos; se os intervalos não forem anuais comparáveis, abster até reconciliação, sem forçar o expoente.

Todos os exercícios/documentos e eventos até a base final precisam estar disponíveis em as_of. Evento sem fator oficial, mudança estrutural/perímetro sem reconciliação ou histórico curto→abstenção. O nível do LPAfinal e o CAGR são nominais, sem corrigir um extremo porIPCA deixando o outro nominal. Gordon/bancos e Bazin mantêm suas janelas aprovadas.

## 4. Perfil, hipóteses e inaplicabilidade

Escopo: STOCK/UNIT oficiais, modeloBPPempresa e perfil crescimento demonstrado. A regra vigente do perfil é ROE>20% **e** DY<4% confiável; não é um “ou”. A decisão sobre fonte comum não altera esses dois limites automaticamente. Perfilrenda→Lynch se abstém; ausência simultânea deLynch/Bazin permanece ausência.

| Caso | Tratamento proposto |
|---|---|
|LPAinicial ou final≤0|Abster: CAGR sem extremos positivos|
|Exercício intermediário com prejuízo|Informar na qualidade; manter somente se série/base/perímetro comparáveis. Não pode desaparecer da cobertura. Ratificar este tratamento na auditoria|
|g≤0|Abster: crescimento histórico não positivo; não fabricar múltiplo/preçozero|
|Cinco observações sem um exercício, fator ou fonte|Abster com motivo específico; TTM não preenche|
|B3zero válido, cascata5%|Usarzero para perfil **e** payout; não substituir pelo5%|
|B3<4%, ROE>20%, cascata não confiável|MesmaB3 válida para ambos; não recusar só pela fonte que não foi usada|
|B3inválida, cascata válida|AvisoB3 + perfil/payout da cascata|
|Ambas inválidas ou perfil não demonstrado|Abster, sem preencher outro método|

O payout mostrado deve ser bruto e sem truncamento no contexto. Se ultrapassar100%, mostrar o fato; não converter em retenção que modifique retroativamente o CAGR. Uma política adicional de elegibilidade por payout é decisão econômica separada, ainda não aprovada neste rascunho.

## 5. Exemplo independente e matriz de aceite

Série sintética2021–2025:1;1,2;1,44;1,728;2,0736. Quatro intervalos; sem evento, classe/perímetro constantes. `g=(2,0736/1)^(1/4)−1=20%`. Com m1,5, teto de g25% e P/L35, propostos por continuidade explícita das hipóteses do projeto: múltiplo30 e referencial `2,0736×30=62,208`. Preço30, DYcomum2%→payout contextual0,6/2,0736≈28,94%; o CAGR continua20%.

```python
from decimal import Decimal as D, getcontext
getcontext().prec = 28
n = D(4)  # cinco observações anuais
lpa0, lpaT = D(1), D('2.0736')
g = (lpaT / lpa0) ** (D(1) / n) - D(1)
pl_ref = min(D('1.5') * min(g, D('.25')) * 100, D(35))
print(g, lpaT * pl_ref)  # 0.20; 62.208
```

Não importa projeto. Se a janela for cinco intervalos com crescimento20%, usar sexto LPA2,48832, e não o mesmo par com expoente trocado.

Matriz futura: extremoszero/negativos/NaN→abstenção; lacuna anual→abstenção; splitoficial2:1→ajuste antes doCAGR; fator ausente→abstenção; exemplo nominal e controle que deliberadamente aplicaIPCA a um extremo devem divergir (recusar regime misto); os quatro casos de fonte/perfil da seção4; controlemúltiplos direitos/semBPP/seguradora→abstenção; perda deLynch eBazin→ambos ausentes. Testes da2C-b serão escritos da ficha aprovada, não do resultadoV1.

## 6. Sensibilidade independente

Manter LPAfinal2,0736 e mudar a taxa como ensaio de premissa, sem afirmar que o mesmo histórico gera taxas diferentes:

|g informado|P/L pela proposta|Referencial|
|---:|---:|---:|
|10%|15|31,104|
|20%|30|62,208|
|25%|35 (teto)|72,576|
|40%|35 (ambos tetos)|72,576|

Abaixo dos tetos, V varia linearmente com LPAfinal e g. Partir de lucro inicial muito pequeno pode inflar CAGR mesmo quando ambos extremos são positivos; mostrar extremos/cobertura e aviso de base pequena, sem criar limiar numérico arbitrário para esse aviso. Desconto real e rendimento nominal fixo são lentes distintas; não tirar mediana com esta heurística.

## 7. Parâmetros e pendências de aprovação

Cinco exercícios e fontecomumDY: decisões26/10; fatoroficial e reconciliação: mesmas regras aprovadas. Quatro intervalos para cinco observações: aritmética, **contagem de janela pendente** conforme seção3. m1,5, gmax25% e PLmax35 são hipóteses herdadas do projeto, não do autor; sua permanência deve ser ratificada/versionada, sem escolher por aparência dos resultados.

Confirmar antes do código: contagem4/5intervalos; papel contextual ou elegibilidade do payout (sem descontar retenção duas vezes); tratamento de prejuízo intermediário; manutenção das demais guardaslegadas. Não implementar alterações além das decisões explícitas. Registrar fontes deLPA/evento/DY/ROE e motivos por lente; F2C-12 enumera antes/depois e predicado do golden apenas após aprovação.
