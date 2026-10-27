# Ações ON, classes preferenciais e units — F2C-38

**Levantamento em27/10/2026. Decisão metodológica pendente do Marcos.**
Nenhum código, método, parâmetro ou fixture financeira muda aqui. Não aprova lente para os casos abstidos.

## Fontes atuais e distinção de datas

Os arquivos foram localizados na categoria de estatutos dos **sites oficiais de RI**, seguindo o JavaScript público para a consulta de documentos publicados. As respostas das listas, PDFs, metadados e scripts estão em `outputs/validacao-fase2c/f2c38-*`. A lista do RI informa data do documento e publicação; a coleta local é outra data. Não se chama PDF legado2019 de vigente só por aparecer na pesquisa.

| Emissor | Documento indicado no RI | Publicação informada no RI | Coleta UTC27/10 | Hash SHA256 |
|---|---|---|---|---|
| Banrisul |20/07/2026|20/07/2026|12:15:31|793764e445be0f01d3c644b5a5efac390bc154433aed9d8accd04a025bcd4daf|
| Usiminas |23/04/2026|27/04/2026|12:15:33|85da09b8e0e1304a86544deee23181ebe95d0dbc3d28faf0a1ed0b284c14ed26|

- [Banrisul, estatuto do RI atual](https://api.mziq.com/mzfilemanager/v2/d/fafdeaf3-7820-4ec2-9477-ce501c563c96/1f9b0e24-4851-bcf5-39a6-12a652d4948c?origin=2), arts5,7–9e88, páginas2/3e18 para direitos/distribuição. A referência do rodapé à homologação e a data exibida no RI não são automaticamente a data inicial de cada cláusula; verificar a vigência histórica antes de aplicar a exercícios anteriores. O PDF legado encontrado pela pesquisa remetia a2019 e foi descartado como prova de atualidade.
- [Usiminas, estatuto2026](https://api.mziq.com/mzfilemanager/v2/d/5dcf459c-823d-4c02-ac4b-a2aa54a63486/5e0d6b29-0d77-e2e0-549a-a7073cef09de?origin=2), arts5/6, páginas1–3; os direitos também aparecem no [FAQ oficial](https://ri.usiminas.com/servicos-de-ri/perguntas-frequentes/).
- [Lei6.404, texto compilado no Planalto, art17§1](https://www.planalto.gov.br/ccivil_03/leis/l6404consol.htm): há alternativas de preferência. O incisoIIpermite vantagem de dividendo de pelo menos10%; não torna10%regra universal para qualquerPN.
- [Santander, governança oficial](https://www.santander.com.br/ri/conheca-o-santander-brasil/administracao-e-governanca-corporativa/governanca/), seção sobre direitos das preferenciais: vantagem de10%em dividendos/JCP e prioridade. A composição daunit continua sendo dadoFCA do índice; esta página não substitui estatuto/vigência para uma implementação futura.

## Direitos efetivamente conferidos nos dois casos do universo

| Papel | Direitos relevantes ao problema |
|---|---|
| BRSR3 ON |voto por ação; participação no saldo dos dividendos conforme ordem estatutária, depois da prioridadePNA|
| BRSR5 PNA |prioridade de6%anuais sobre capital social/número de ações, não cumulativa; participação posterior com acréscimo de10%na etapa definida noart8(ii); conversível emONouPNB|
| BRSR6 PNB |participação conforme art88, prioridade de reembolso; não conversível. Não recebe automaticamente a vantagemPNA só por serPN|
| USIM3 ON |voto; sem a vantagem de dividendo das preferenciais|
| USIM5 PNA |dividendo10%maior queON; prioridade de reembolso apósPNB|
| USIM6 PNB |mesma vantagem de dividendo, prioridade de reembolso antesPNA; pode converter emPNA|

Banrisul: o art88descreve distribuição em etapas. Não substituir essa ordem por um multiplicador universal1,1aplicado a todaPN. Usiminas: classesA/Btêm diferenças de liquidação/conversão, embora a vantagem de dividendo frente àONseja a mesma. Diferença de sigla, diferença de direitos patrimoniais e diferença de fluxo ordinário não são sinônimos.

## Inventário e cobertura

`classes-preferenciais-amostra-2c.json` foi extraído do índice público local (hash noJSON). Há15emissores e46tickersSTOCK/UNIT com mais de uma siglaPN. É inventário de candidatos: não prova que todos tenham direitos econômicos distintos nem que todos os tickers sejam atuais/negociados. Nenhuma quantidade de uma classe foi obtida dividindo o agregadoPN.

Nas tabelas de `universo-inicial.md` (extração de todas as primeiras colunas, incluindo sucessores/BTG), os emissores dessa seleção são **Banrisul** (BRSR3/5/6) e **Usiminas** (USIM5). Os estatutos acima demonstram diferenças de direitos nesses dois emissores. USIM3/6 são controles oficiais do mesmo emissor no índice, não novos membros inventados para o universo inicial. Os demais13ficam no inventário, sem atribuição presumida de direitos. A definiçãoD32não é ampliada por este levantamento.

## Atribuição à ON e o limite do cálculo atual

1. **Lucro:** o LPA divulgado daON é a atribuição apresentada pela companhia segundoCPC41/ficha por-ação1.1. Não substituir pelo lucro total dividido por todas as ações quando há direitos diferentes. Rateio aproximado de lucro não demonstra o método das duas classes, nem iguala lucro atribuído a dividendo pago.
2. **PL:** PL dos controladores não é automaticamente a soma de parcelas econômicas iguais por classe. Reembolso prioritário e conversibilidade exigem convenção explícita paraB0porclasse; estatuto isolado não fornece uma série conciliada dePLatribuído àON. Ausência dessa convenção continua motivo para não ativar a extensão.
3. **Proventos:** reconciliar DVA dos controladores por competência com dividendos/JCP aprovados e atribuídos a cada classe, incluindo prioridadePNAe tesouraria da mesma janela. Não usar dataexB3como se fosse competênciaDVA nem trocar a fonte da lente vigente de passagem.

Hoje `gordon_cvm.entradas(..., modelo="banco")` divide proventos totais dos controladores pelas ações-base totais e multiplica pelo fator daunit; `classes_preferenciais` com mais de uma classe abstém. Assim o Banrisul continua abstido pela guarda já aprovada, inclusive aONdoBRSR3. A extensão daONnão está implementada. A unit de banco comON+PNde direitos diferentes pode passar pela aproximação de número comum por ação quando existe só uma classePN: é a limitação econômica já declarada da ficha, não bug novo contra uma regra de rateio aprovada.

Exemplo **condicional e independente**, sem afirmar que sejam quantidades reais de um banco:100ON+200PN, PNrecebe1,1vez o fluxoON, distribuição total320. Então dON=320/(100+1,1×200)=1;dPN=1,1. Umaunit1ON+1PNrecebe2,1. Dividir320/300×2produz2,133333…, diferença≈1,5873%. Não aplicar esse exemplo ao Banrisul: suaPNAtem prioridade fixa e etapas adicionais. Se quantidadesON/PNfossem iguais e unit1+1, o total médio poderia coincidir; isso não demonstra atribuição individual ou equivalência dos direitos.

## Proposta para ficha, sem ativação

Propor uma revisão própria de **bancos** e, quando necessário, da ficha por ação, com matriz porON/PNA/PNB/unit. Exigir fonte/vigência dos direitos, quantidades da classe e tesouraria, lucro/PL/proventos atribuíveis e exemplo independente. Para fluxo por classe, separar a alternativa de observar valores oficialmente atribuídos da alternativa de ratear pelo estatuto; não confundir escolha de fonte com escolha de modelo. Na ausência de reconciliação, conservar abstenção. Nenhum algoritmo de rateio fica aprovado por este texto.

**Decisões pendentes do Marcos:**

- manter a abstenção daONem emissor com váriasPNou autorizar revisão específica da ficha para aON;
- escolher comoB0e lucro serão atribuídos por classe quando a informação oficial não os separa, ou manter abstenção;
- paraunitsde bancos, manter aproximação comum ou exigir reconciliação por componente, fonte e vigência, inclusive quando há somente uma classePN;
- aprovar fichaD21auditada e ticketfixpróprio com regressão antes de qualquer implementação. Auditor externoClaude, sem fazer a própria implementação valer como definição de correto.

Nenhuma dessas decisões foi tomada pelo executor. Nenhum parâmetro/regra econômica novo entra no código nesta etapa.
