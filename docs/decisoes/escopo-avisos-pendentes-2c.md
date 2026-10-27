# Escopo e avisos pendentes — F2C-45

**Status: levantamento; quatro decisões pendentes para o Marcos.** Executor: Codex, 27/10/2026. Não aprova nova regra, não implementa exceção e não ativa item da 2C-b. Cada decisão futura exige especificação, item `fix:` próprio e regressão antes da correção.

## Base, denominador e limites

Fotografia de conteúdo do índice público `data/referencia/indice.json` (gerado em 26/10/2026) e do [ZIP oficial de DFP 2025 da CVM](https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/DFP/DADOS/dfp_cia_aberta_2025.zip), já coletado localmente. Evidência e casos completos em [escopo-avisos-amostra-2c.json](escopo-avisos-amostra-2c.json). SHA256 do índice: `b29e5b882f7a585517594afa1e8113f9211195cd07eb386f0527b7ecdc952a2b`; do ZIP: `d7aec54e7c67998e4cd3ef94c463ab247f09a6baaa2254878d1e431f28130e2a`.

Seleção: todos os **455 tickers STOCK/UNIT**, correspondentes a **342 códigos CVM** distintos. No BPP consolidado, linhas `ÚLTIMO`, maior `DT_REFER` e maior versão por código. Aplicação da função vigente `CVMProvider.modelo_do_documento`, que verifica os pares código/descrição do PL; banco tem precedência; com PL de empresa, a descrição de seguro pode produzir seguradora. Não é seleção pela natureza econômica presumida do emissor.

| Modelo pelo setor | Modelo pelo BPP | Tickers |
| --- | --- | ---: |
| banco | banco | 19 |
| banco | não demonstrado | 16 |
| empresa | empresa | 326 |
| empresa | seguradora | 5 |
| empresa | não demonstrado | 83 |
| seguradora | empresa | 2 |
| seguradora | seguradora | 4 |

Totais BPP: **328 empresa, 19 banco, 9 seguradora, 99 não demonstrados**. Os 99 correspondem a 63 códigos CVM, todos sem BPP consolidado no recorte selecionado; todos possuem código no índice. Isso não prova falha de download, ausência de demonstração individual, ausência de consolidado em outro ano ou situação atual de negociação. O arquivo não certifica disponibilidade histórica, entrega até um `as_of`, documento mais recente global nem elegibilidade final de uma lente. Reproduz os 19 bancos e 99 sem modelo do levantamento F2C-36; não altera o denominador D32.

No universo inicial, há **89 códigos na primeira coluna das tabelas e BPAC11 adicional na seção “BTG após o F2A-39”**, totalizando 90; 55 são STOCK/UNIT no índice. Essa é a delimitação precisa do recorte usado nos levantamentos anteriores: dizer apenas “90 da primeira coluna” é impreciso. Não se incluem os outros códigos citados no texto somente como controles. Oito desses 90 não estão no índice desta fotografia: AZUL4, BCFF11, ELET3, GOLL4, IRDM11, JBSS3, PETZ3 e RBRF11. São exemplos públicos de histórico/identidade, não uma lista de posições. A ausência no índice, sozinha, não demonstra qual é o sucessor nem autoriza conversão de ticker.

## 1. Saúde e benefícios: efeito do critério ampliado

O código vigente identifica `provisoes tecnicas`, `contrato(s) de seguro/resseguro` ou `atividade seguradora` nas descrições normalizadas do BPP, depois de demonstrar PL de empresa. Fonte: `cvm_provider.py`, `modelo_do_documento`; decisão de 25/10/2026 registrada no F2B-4. Não mede participação, materialidade ou contribuição do segmento segurador.

Todos os documentos abaixo são DFP de 31/12/2025, versão 1:

| Ticker / código CVM | Setor no índice / modelo pelo setor | Evidência no BPP | Modelo BPP vigente |
| --- | --- | --- | --- |
| HAPV3 / 24392 | Serviços Médicos / empresa | 2.01.05.02.08: Passivo de contratos de seguros; 2.01.06.02.04 e 2.02.04.02.06: provisões técnicas de assistência à saúde | seguradora |
| RDOR3 / 24821 | Serviços Médicos / empresa | 2.01.05.02.09 e 2.02.02.02.09: Passivos de contratos de seguro | seguradora |
| SAUD3 / 20125 | Serviços Médicos / empresa | 2.01.05.02.04: Passivos de Contratos de Seguro e Resseguro; 2.01.06.02.07: Outras Provisões Técnicas | seguradora |
| QUAL3 / 22497 | Seguradoras e Corretoras / seguradora | 2.01.02.01.04: Provisões técnicas de operações de assistência a saúde | seguradora |

Efeito mecânico demonstrado: três divergências setor/BPP entre os quatro; QUAL3 concorda nos dois critérios. Todos recebem o escopo seguradora pelo critério BPP vigente e, portanto, não recebem número de método de ação. Isso não conclui que a atividade principal de cada emissor seja seguradora, nem que o critério deva ser alterado.

**DECISÃO PENDENTE PARA O MARCOS — saúde:** manter o critério descritivo amplo para grupos de saúde/benefícios ou especificar outro escopo. Qualquer alternativa que use materialidade, segmentos ou separação de negócios precisa de fonte, regra e ficha; nenhum limiar é criado neste levantamento. Seguradora continua sem lente na 2C.

## 2. Leitura das contas por setor contra escopo pelo BPP

Há **sete tickers divergentes em seis códigos CVM** com BPP demonstrado:

| Ticker | Setor no índice | Modelo para leitura por setor | Modelo BPP |
| --- | --- | --- | --- |
| CXSE3 | Emp. Adm. Part. - Seguradoras e Corretoras | seguradora | empresa |
| HAPV3 | Serviços Médicos | empresa | seguradora |
| PEAB3 | Emp. Adm. Part. - Sem Setor Principal | empresa | seguradora |
| PEAB4 | Emp. Adm. Part. - Sem Setor Principal | empresa | seguradora |
| RDOR3 | Serviços Médicos | empresa | seguradora |
| SAUD3 | Serviços Médicos | empresa | seguradora |
| WIZC3 | Seguradoras e Corretoras | seguradora | empresa |

PEAB3/4 compartilham documento; as descrições de passivos de seguros em 2.01.05.02.06/07 e 2.02.04.02.06 ativam o critério. CXSE3 e WIZC3 têm PL de empresa e não têm descrição ativadora no BPP selecionado. “Holding” ou o setor segurador não substitui o documento.

A cascata ainda chama `contas_cvm.modelo_do_setor` antes de `calcular_indicadores`/série/TTM; o escopo posterior usa `modelo_bpp`. Essa separação é a decisão provisória 2 do F2B-4, não foi resolvida pela mudança de seleção do IF.data no F2C-36. Pares D20 podem abster uma conta quando o modelo de leitura não é demonstrável; não se deve transformar automaticamente o setor em prova do modelo. Os 99 sem BPP são categoria separada, não sete divergências adicionais nem correspondências confirmadas.

**DECISÃO PENDENTE PARA O MARCOS — origem do modelo das contas:** confirmar ou substituir a seleção por setor, especificando como obter o modelo documental antes da leitura e o que fazer quando ele não é demonstrado ou muda entre documentos. Se aprovada mudança, criar `fix:` com os sete casos, controles concordantes e regressão da preservação de séries/TTM; não implementar neste item.

## 3. Fora do índice, falha de fonte e modelo não demonstrado

Regra vigente no motor de ações: sem `modelo_bpp` demonstrado, abstém os métodos, sem valor ou variação fictícios. Uma cotação/fundamento de yfinance ou brapi não prova BPP. Na cascata, sem código CVM do índice não há consulta pelo mapa manual; falha/ausência de dados CVM pode deixar o modelo ausente. Os avisos de origem são preservados. Essa guarda não quer dizer que nenhuma outra informação do ativo possa ser exibida.

No recorte medido, são 99 tickers sem BPP/63 emissores; são ausência de conteúdo naquele arquivo, não 99 downloads falhos. Os oito nomes públicos fora do índice do universo inicial são outro recorte, que inclui FIIs históricos. Não somar esses oito aos 99: denominadores/classes distintos. A lente do FII usa Informe Mensal e contrato próprio; a falta de BPP não é critério adicional criado aqui para FIIs. Não há contagem de todos os tickers possíveis fora do índice ou de falhas operacionais de download nesta fotografia.

**DECISÃO PENDENTE PARA O MARCOS — falta de modelo/fonte:** confirmar a abstenção de todas as lentes de ação ou aprovar uma rota documental alternativa com escopo e disponibilidade temporal demonstráveis. Não usar contingência de setor/padrão empresa para preencher a lacuna. Nenhuma rota alternativa, demonstração individual ou substituição de ticker foi implementada.

## 4. Aviso de alavancagem no banco com lente aplicada

Regra vigente: banco cuja lente se abstém retorna antes dos ajustes gerais; banco com lente aplicada passa pelo trecho geral de avisos. Dívida líquida/EBITDA ausente ou inaplicável recebe `aviso_alavancagem`, fora dos riscos e sem penalidade numérica por ausência. F2C-40 passou a exibir o motivo CVM, preservando essa política. O resultado da lente não é alterado pelo texto do aviso.

**DECISÃO PENDENTE PARA O MARCOS — aviso no banco:** conservar uma explicação de medida inaplicável, especificar texto contextual próprio ou retirar o aviso de banco com lente aplicada. Não equiparar inaplicabilidade a falta de coleta. A decisão precisa de `fix:` próprio com regressão da presença/ausência do aviso e prova de números/classificação inalterados; este levantamento não a toma.

## Entrega e revisão

Nenhum módulo, fixture, método ou limiar muda. Os quatro marcadores permanecem pendentes. O JSON guarda os sete casos, os 99 sem modelo, as quatro companhias de saúde, cruzamento e hashes públicos para o Claude reproduzir. O script de extração e logs ficam em `outputs/validacao-fase2c/f2c45-*`, ignorados. O primeiro ponto da auditoria é distinguir critério descritivo de estrutura econômica; depois conferir o denominador por ticker/emissor e a separação entre modelo de leitura e escopo.
