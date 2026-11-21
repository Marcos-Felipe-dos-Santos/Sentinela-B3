# Escopo de operadoras de saúde e benefícios (F3-P10, F2C-45(i))

Levantamento de 12/11/2026, feito só com leitura do banco único (DFP de 2010 a 2025, BPP consolidado) e do índice público `data/referencia/indice.json`, sem rede. O critério vigente fica como está, e o estudo não escolhe limiar.

## 1. O critério vigente

`CVMProvider.modelo_do_documento` (decisão do Marcos de 25/10/2026, F2B-4) olha primeiro o PL. Quando o PL está no par do modelo empresa, o documento vira "seguradora" se alguma conta do BPP consolidado tiver na descrição (`_CONTAS_DE_SEGURADORA`):
- "provisões técnicas";
- "contrato(s) de seguro/resseguro";
- "atividade seguradora".

A comparação é feita na descrição normalizada, sem acento (`contas_cvm.normalizar_descricao`). O valor da conta não conta para o critério. Seguradora e documento sem modelo demonstrado não recebem número de método de ação. O levantamento da 2C (`escopo-avisos-pendentes-2c.md` §1) fotografou só a DFP de 2025.

## 2. Histórico ponto-no-tempo: quando cada companhia mudou de escopo

O mesmo critério foi reproduzido sobre o BPP consolidado de cada DFP de 2010 a 2025, sempre na maior versão guardada de cada documento. A data entre parênteses é a entrega dessa versão (`entregas.dt_receb`), ou seja, quando a mudança passaria a valer no modo estrito.

| Ticker (índice atual) | Setor no índice | Mudanças de modelo pelo BPP |
|---|---|---|
| BBSE3 | Seguradoras e Corretoras | seguradora desde a DFP de 2012 (entregue em 29/04/2013) |
| HAPV3 | Serviços Médicos | seguradora desde a DFP de 2017, a primeira guardada (24/04/2018) |
| IRBR3 | Seguradoras e Corretoras | seguradora desde a DFP de 2016 (31/07/2017) |
| MGLU3 | Comércio | seguradora de 2010 a 2012 (DFP de 2010 entregue em 05/05/2011); empresa desde a DFP de 2013 |
| PEAB3, PEAB4 | Holding sem setor principal | empresa até 2023; seguradora desde a DFP de 2024 (03/04/2025) |
| PSSA3 | Seguradoras e Corretoras | seguradora desde a DFP de 2010 (01/03/2011) |
| QUAL3 | Seguradoras e Corretoras | empresa até 2013; seguradora desde a DFP de 2014 (26/03/2015) |
| RDOR3 | Serviços Médicos | empresa de 2018 a 2022; seguradora desde a DFP de 2023 (26/03/2024) |
| SAUD3 | Serviços Médicos | empresa até 2019; seguradora desde a DFP de 2020 (04/03/2021) |

Mais 11 companhias fora do índice atual passaram por "seguradora" em algum ano (deslistadas ou sem ação listada hoje). Seis delas já eram seguradora na DFP de 2010.

No backtest, HAPV3, RDOR3, SAUD3, QUAL3, PEAB e MGLU3 trocam de escopo dentro da janela. Antes da troca, recebem os métodos de empresa; depois, abstêm-se. O inverso vale para a MGLU3 a partir de 2013.

## 3. Materialidade: o peso das contas que disparam o critério

A medida é a soma das contas de topo cuja descrição dispara o critério, dividida pelo passivo total (conta 2), na DFP de 2025:

| Ticker | Peso no passivo total | Contas |
|---|---:|---|
| IRBR3 | 59,1% | Passivos da atividade seguradora/resseguradora |
| PSSA3 | 19,7% | Passivos de contratos de seguro |
| RDOR3 | 17,5% | Passivos de contratos de seguro |
| SAUD3 | 11,5% | Passivos de contratos de seguro e resseguro |
| PEAB3 | 5,5% | Passivos de contratos de seguros |
| HAPV3 | 2,7% | Passivo de contratos de seguros |
| BBSE3, QUAL3 | 0% | A descrição dispara, mas a conta tem valor zero ou vazio |

Na MGLU3 de 2012, o peso era de 1,1% (provisões técnicas de seguros).

O critério por descrição põe na mesma classe uma resseguradora (59%) e uma operadora com 2,7% do passivo. Para BBSE3 e QUAL3, a classificação vem só do rótulo, com valor zero.

## 4. Caminhos para a decisão (nenhum escolhido)

1. **Manter o critério atual.** As trocas de escopo da seção 2 entram no backtest como estão, com o motivo de abstenção.
2. **Materialidade por valor.** A conta só dispara com valor diferente de zero, e a classe exige um peso mínimo no passivo ou no resultado, com limiar a decidir pelo Marcos. Com "valor diferente de zero", sem limiar, BBSE3 e QUAL3 deixariam de ser seguradora pelo BPP (o setor delas continua sendo de seguradora).
3. **Segmentos.** Usar a nota de segmentos ou a receita de contratos de seguro da DRE. Essa fonte ainda não foi medida: nos dados abertos da CVM, ela não tem campo estruturado próprio.
4. **Operadora de saúde como escopo próprio,** com lente própria no futuro, no lugar de entrar como seguradora (ANS e IFRS 17). É mudança de escopo de método, caso do §3 da política.

Qualquer um desses caminhos exige ficha, item `fix:` próprio e regressão antes da mudança.
