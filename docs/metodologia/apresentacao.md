# Apresentação por lente — versão 1.0

**Status:** rascunho de 28/10/2026, aguarda auditoria FICHA pelo Claude e aprovação do Marcos. Não implementado; nenhuma classificação ou estado de alerta muda por este texto.
**Itens que dependem:** F2C-3/5/4; histerese entregue como contrato paraF4-2. Pacote26/10 §§1–2/8; ADR-0003 D23–D26/D28/D29. Três dimensões separadas, sem mediana única, nota agregada ou sigmoide.

## 1. Fórmula, referência e significado

Para uma lente válida com referencial positivo `V` e preço de mesma unidade/referência `P>0`, a distância de apresentação é `d=V/P−1`. Dada banda `0≤b<1`, proposta de três estados:

|Predicado|Classificação educacional|
|---|---|
|d>b|sinal positivo|
|−b≤d≤b|neutro|
|d<−b|sinal negativo|
|Lente abstida ou V/P não demonstrados|indisponível com motivo, **não** neutro|

A fórmula é aritmética, não uma expectativa de retorno nem probabilidade. A fonte da separação é a decisão doMarcos26/10 e D24–D26, não uma lei externa que determine o limiar econômico. A banda candidata da seção4 vem de medição declarada, sujeita à aprovação e nova verificação sob as fichas2.0. Não converter a distância em score por exponencial, nem desempatar lentes com média/mediana.

Graham/Lynch são referenciais heurísticos; Gordon/bancos carregam suas hipóteses de regime e documento. A tabela não transforma todos em um “valor justo” único. ParaBazin: mostrar **“atinge/não atinge o critério nominal6%”**, Dbruto12meses, DY e preço-limite `D/0,06` informativo, não “valor justo”. Se receber também sinal pela distância ao preço-limite, rotulá-lo como classificação do **critério**, separada de atingir6%. Por identidade, `d_Bazin=DY/0,06−1`; a faixa neutra não muda a taxa6% nem a regra de elegibilidade da fichaBazin. Esta apresentação adicional do sinal doBazin precisa ser ratificada na auditoria, sem criar preço-limite de sérieabstida.

## 2. Contrato de apresentação e insumos

|Bloco|Conteúdo obrigatório|Não fundir com|
|---|---|---|
|Qualidade empresarial|Descritores/faixas/cobertura de qualidade1.0, dívida/EBITDA≤0 explícito|Upside, score de preço ou taxa de juros|
|Valuation por lente|Nome/versão, hipótese, regime, unidade, janela, documento, V ou motivo, P/data, distância e sinal se aplicável|Mediana/valorúnico/classificação global|
|Qualidade dos dados|Completude por modelo, atualidade, origem, disponibilidade/coleta, reconciliação e motivos|Qualidade econômica ou outra penalização automática|

Não descontar a mesma ausência de dado duas vezes em confiança. Ausência não é perda/prejuízo; valornegativo legítimo daCVM não é incompletude. Não preencher a abstenção por preço, zero, outro método ou outra fonte recusada. Nenhum método inclui banco/seguradora/FII fora do próprio escopo por conveniência visual. Seguradora semlente ou FIIsemrendimento ficam com motivos, sem número/upside.

Uma linha de lente leva: identificador/versão, as_of comfuso, regime/moedabase, valor/unidade ou abstenção, insumos/fontes/documentos utilizados, preço/data, distância e versão da banda. Mostrar separadamente fonte registrada mas recusada, sem alegar que foi utilizada. Qualidade e dados não são um escore-síntese. Avisos, inclusive cobertura dos pares, continuam visíveis como avisos; não entram numa média de preços.

## 3. Regime, data e escopo

Comparar somente números com unidade equivalente: R$/ação, R$/unit ou R$/cota; mesma base acionária e moeda declarada. Se uma lente anual tem moeda-base anterior ao preço, mostrar a data e seguir a convenção aprovada na ficha correspondente; esta ficha de interface não cria uma atualização/deflação silenciosa. Quando a equivalência não for demonstrada, a classificação fica indisponível com motivo, preservando o número de origem quando lícito mostrá-lo como contexto.

Gordon/bancos continuam DFPanual; Bazin12mesesdata-ex; Graham/Lynch dependem dos seus rascunhos aprovados. A comparação entre hipóteses/regimes distintos não autoriza agregação. Com mesma entrada completa e as_of, o resultado calculado é determinístico, sem estado de alertas ou relógio novo no método.

## 4. Dispersão medida e banda candidata — evidência e limitações

Sondagem em28/10/2026, sem rede e sem carteira: snapshot público do levantamentoF2B-31, `outputs/f2b31_b3/universo_dados.pkl`, coleta declarada `2026-10-20T21:05:33.499636+00:00`, SHA256 `a36b026a526eaeea23f55a11793dcd90e0254e5191edb8bd8902894e477ff3fe`. Os51candidatos são a amostra pública de ações/units do universo inicial daquele levantamento, **não todo o índice nem o universo atual completo**. Não afirmar que são51companhias diferentes ou independentes. Dados brutos não entram neste commit; os números reduzidos abaixo permitem reproduzir a estatística.

Procedimento descritivo: chamar contratos puros vigentes Graham1.2.0/Lynch1.1.0/Gordon2.1.0/Bazin2.1.0 sobre insumos da coleta. Usar somente modeloempresa; preço/PL/PVP/DY/ROE/LPA finitos, preço ePVP positivos; perfil nessa sondagem pelo DY da **cascata** e ROE (ROE>20%, DY<4%), não replay integral da seleção de perfilB3. VPAheurístico=preço/PVP, como adaptadorvigente. ParâmetrosGraham25/7/2,5/3; Lynch0,95/0,25/1,5/35. Gordon/Bazin recebem as entradas demonstradas pelos consumidores puros para o instante da coleta; fonte que abstém não gera número. Não incluir bancos, FII ou número de abstenção.

Isso mede **saídas das hipóteses vigentes**, não valida economicamente suas fórmulas nem gera esperado de teste para as fichas futuras. Não aplica ainda médiaIPCA/CAGRnovo ou garante compatibilidade histórica/perímetro completa das fontes. A seleção por insumos comuns também exclui casos que uma lente isolada poderia calcular; viés de cobertura declarado.

51candidatos →10casos com≥2saídas positivas; excluídos11por modelo,1por insumo e29por menos de duas saídas. Para cada caso calcular a semi-amplitude relativa `s_i=(maxV−minV)/(maxV+minV)`, sem fabricar uma lente de consenso. Abaixo, valoresmínimo/máximo são **somente estatística diagnóstica**, não preço-síntese.

|Ticker público|mínimo|máximo|s_i|
|---|---:|---:|---:|
|CMIG4|10,710223198166666|19,489622377038728|0,29071006859982435|
|LREN3|8,36474182455494|18,586297475244365|0,37926387687637486|
|PETR4|33,42995325032594|77,69102599192121|0,39831427911650036|
|RECV3|22,735483333333335|24,059561465262007|0,028295263689295958|
|SLCE3|6,635737022192893|15,971464626352226|0,4129537016254346|
|SUZB3|11,714659981822603|379,46614999999997|0,9401061622508172|
|TAEE11|47,73936443154704|50,107620163|0,024203665971582158|
|TIMS3|20,60707029346282|24,53900993666667|0,08709371053170109|
|VALE3|56,10136366201289|93,54154925000002|0,25019685101960837|
|WEGE3|4,172604719056212|9,50266617708469|0,3897591132569518|

Mediana de s: **0,33498697273809963 (33,49869727%)**, mínimo2,42036660%, máximo94,01061623%. Proposta de trabalho para auditoria: **b_candidata=mediana(s)**, constante versionada, sem escolher10%/15% só porque produz rótulos visualmente convenientes. A regra da mediana reduz a influência de um caso extremo, mas é uma **hipótese de apresentação**, não intervalo de confiança, erro esperado, margem de segurança ou recomendação. Não usar o b de cada ativo dinamicamente nem reduzir a banda quando faltarem lentes.

A medição é pequena, de versões anteriores aGraham2.0/Lynch2.0, com perfil simplificado e fontes de base diferentes. **Não basta para aprovar banda final de produção.** Antes de2C-b, Claude/Marcos devem ratificar ou rejeitar essa proposta e exigir repetição por lente/regime no universo e data aprovados, com contagem de exclusões e comparação das bandas. A aprovação pode escolher bandas distintas por lente; esta ficha não escolhe limiares novos escondidos. Sembaprovada, sinal por lente ficaindisponível; os resultados e motivos continuam apresentados. O rascunho entrega a evidência e uma candidata justificada, não simula que sua adoção já foi decidida.

Artefatos ignorados da medição: `outputs/validacao-fase2c/sondagem-dispersao-fichas.py` (SHA256 `90d27ad48bfe10ffaff89deb27f5b057be9c7f728cb404290f5b09e2aece39a2`) e `.json` (SHA256 `1b78d20179b331a2875d18121c60032efd2a7a5265544e4f781919553e821071`). Contêm medição pública, nenhum dado da carteira. Se perdidos, não inferir disponibilidade do snapshot a partir desta tabela.

## 5. Exemplo independente e matriz

Caso sintético, **sem ticker real**: V100, P70/80/160. Usando apenas para demonstração a candidata b0,33498697273809963, d42,857%/25%/−37,5% produz sinalpositivo/neutro/sinalnegativo. Preços de fronteira P=V/(1+b) eV/(1−b) são aproximadamente74,907098 e150,372994; igualdade pertence ao neutro. Não interpretar os limites arredondados de tela como igualdade computacional exata.

```python
from statistics import median
s = [.29071006859982435, .37926387687637486, .39831427911650036,
     .028295263689295958, .4129537016254346, .9401061622508172,
     .024203665971582158, .08709371053170109, .25019685101960837,
     .3897591132569518]
b = median(s)
for preco in [70, 80, 160]:
    d = 100 / preco - 1
    rotulo = 'sinal positivo' if d > b else 'sinal negativo' if d < -b else 'neutro'
    print(preco, rotulo)
print(b)  # 0.33498697273809963
```

A estatística é recalculada por biblioteca padrão; o exemplo de classificação não importa motores. Matriz futura: fronteiras±b e vizinhos; bsemversão/inválida→indisponível; Pzero/negativo/nãofinito→motivo; Vausente→semupside/sinal; regimes/bases incompatíveis→motivo; lentes discordantes→linhas discordantes semrótulosíntese; BazinD0/comfonteausente→regra da ficha vigente, sem valorinventado; prejuízo válido≠incompletude; ausência sem penalização dupla; motor repetido com mesmaentrada/as_of→mesmoresultado; leitura de rótuloslegados preserva número e mostra origem histórica.

## 6. Sensibilidade e limites da classificação

Para o caso V100/P80, d25%: banda10%→sinalpositivo; banda33,50%→neutro; banda50%→neutro. O número da lente não mudou. ParaV100/P160, d−37,5%: banda33,50%→sinalnegativo; banda50%→neutro. Logo, a banda é uma decisão material de apresentação, não pode ser ajustada retrospectivamente para um rótulo desejado. A dispersão entre hipóteses não mede risco futuro; repetir a sondagem com as novas janelas e documentar a sensibilidade é condição da aprovação, não código neste item.

## 7. Histerese — somente contrato F4-2

Separar `resultado_calculado` (lente/versão,as_of,insumos,valoroumotivo,d,sinal,banda/versão) de `estado_alerta` (chave deativo/lente/versão,últimoestado,eventoid,últimoenvio). O método não recebe o estado anterior.

Contrato proposto paraF4-2, parâmetros a aprovar naquela fase: `b_entrada≥b_saida≥0`, política de repetição/cadência e chave de idempotência. Em estado neutro/suspenso, entrarpositivo só comd>b_entrada e negativo só comd<−b_entrada; ao recuperar fonte, reavaliar entrada, não retomar por rótulo antigo. Positivo existente sai para neutro quandod≤b_saida, negativo sai quandod≥−b_saida. Se numa observação cruzar diretamente a banda oposta deentrada, produzir uma única transição para o oposto, sem dois envios duplicados. Dentro da zona de retenção do mesmoestado, não emitir novaentrada; repetição só pela políticaF4aprovada, com eventoididempotente. Lenteabstida→suspender alerta e preservar motivo, não emitir sinalnegativo. Histórico guarda resultado e transição separadamente.

Nenhum valor de b_saida, prazo ou número de repetições é implantado/escolhido aqui. Datas futuras/fonteatrasada e revisão de documento exigem regras de disponibilidade e idempotênciaF4/D16; não usar relógio no cálculo de valuation. Sem estado/persistência de alerta no motor ou SQLite nesta metade.

## 8. Compatibilidade e pendências de aprovação

Rótulos históricos deCOMPRA/NEUTRO/VENDA serão lidos por adaptador, conforme §8aprovado, exibidos como sinais **com identificação de resultado legado**, sem fingir recálculo pela banda nova. Não reler score como qualidade nem converter abstenção em neutro. Schema e migração/backup/restauraçãoD29 ficamFase3; a2Cnão migraSQLite.

Antes de implementar: aprovar a banda por lente/regime e protocolo amostral; confirmar apresentação do sinal doBazin além do atingimento6%; confirmar equivalência temporal/monetária nas fichas; garantir ausência de sinalglobal e sigmoide; testar compatibilidade e exemplos independentes. O estado de alerta completo continuaF4-2. O `[x]` na fila certifica só a entrega deste rascunho. Parar na decisão “Auditoria da2C-a e das fichas da2C-b”; nenhuma implementação2C-b foi autorizada.
