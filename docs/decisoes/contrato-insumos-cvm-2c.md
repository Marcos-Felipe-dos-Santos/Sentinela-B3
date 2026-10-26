# F2C-29 — contrato dos insumos anuais e TTM

26/10/2026. Levantamento que prepara F2C-1 e delimita F2C-30/31; não altera método, janela ou produção. Prevalecem ADR-0003 D19/D20, ficha por ação 1.1, Gordon/bancos vigentes e pacote aprovado §§3–4. Contrato prospectivo difere do estado implementado quando indicado.

## Fonte e identidade

Dicionários oficiais CVM conferidos em 26/10/2026:

- [DFP, ZIP de metadados](https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/DFP/META/meta_dfp_cia_aberta_txt.zip), 6.794 bytes, SHA256 `a6e4d4dad8177a7cbbfd8042d4b46508b1cc9323f974cb9b9f7fa4666add1417`.
- [ITR, ZIP de metadados](https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/ITR/META/meta_itr_cia_aberta_txt.zip), 6.792 bytes, SHA256 `5baa9c0a2cda0eeedf6c1a2135611171a2a505077c5c3362ddc9dcf1868c24fd`.

Ambos contêm dicionários de BPP, DRE, DVA e composição do capital. A identificação usa companhia, tipo/agregação da demonstração, DT_REFER e VERSAO; fluxos também DT_INI_EXERC/DT_FIM_EXERC e ORDEM_EXERC. Escala monetária não é automaticamente escala da quantidade de ações. Dicionário define campos; não determina qual reserva econômica é válida. Isso vem das decisões aprovadas. O TXT direto do comentário do código retornou404; o portal oferece ZIP, baixado com sucesso após conferir o índice oficial. Arquivos locais `/tmp/2c29-meta-{dfp,itr}.zip`, manifesto `/tmp/2c29-fontes.json`.

## Matriz de disponibilidade do BPP e reserva D20

| Evidência do mesmo documento | Campo dos controladores válido e explícito | Campo ausente/zero que precisaria da reserva |
|---|---|---|
| BPP legível, não vazio, mesma companhia/data/versão/modelo; minoritários ausentes ou zero e DRE sem evidência minoritária | preserva leitura direta | permite somente a reserva D20 já aprovada; registra origem/reserva |
| BPP com participação minoritária não zero | preserva leitura direta | abstém, não atribui lucro consolidado à controladora |
| BPP ausente, tabela vazia, ilegível, sem companhia ou só outra data/versão | preserva leitura direta da DRE | abstém: ausência de evidência do balanço não demonstra ausência de minoritários |
| Conta presente inválida, par sem correspondência, valores conflitantes | aplica domínio da própria conta | nunca converte valor inválido em linha ausente para autorizar reserva |

Legibilidade não se prova criando DataFrame vazio com os nomes de colunas. É preciso ter lido linhas do BPP correspondente, distinguindo falha de fonte/parse de ausência da rubrica dentro de um balanço válido. Não exigir a presença da própria rubrica minoritária para declarar o BPP válido: a D20 admite que ela falte. Validação estrutural deve exigir colunas de identidade/conta/valor e linhas do documento correto, com modelo compatível; código e descrição continuam pareados pela tabela D20. Leitura direta da controladora não passa a depender artificialmente de balanço usado apenas para a reserva.

Estado atual: `_acumulados_do_arquivo` transforma certos erros do BPP em frame vazio e filtra DT_REFER/VERSAO antes de chamar `lucro_controladores_com_reserva`; frame vazio equivale à rubrica ausente para `controladores`. O filtro de versão existe, mas não prova que o documento correspondente foi lido. F2C-30 deve reproduzir cada sintoma com regressão estrita antes da correção, preservando campos independentes. Este documento não alega que já foi corrigido.

## Fluxos e janelas

- DRE legível continua fornecendo lucro/receita quando a DVA falha. Dividendos/JCP recebem motivo de indisponibilidade; falha de DVA não deve apagar DRE. Linha de provento ausente em DVA válida segue regra de rubrica única do F2B-46; arquivo ausente não é zero.
- TTM é soma de quatro trimestres completos, contíguos e encerrados até a referência; cada trimestre é diferença de acumulados comparáveis do mesmo exercício. Q4 deriva da DFP menos acumulado de nove meses. Datas vêm dos documentos; não impor janeiro–dezembro a exercício não civil.
- Somar fluxos monetários não requer ações. TTM sem composição pode existir em totais; não inventa LPA nem divide todo o histórico pelas ações atuais. Conversão por ação pertence ao contrato específico, com ações/escala/direitos do próprio documento e fator oficial quando necessário.
- DT_REFER/VERSAO diferentes não se tornam comparáveis só por datas contíguas. Perímetro consolidado, modelo, moeda e mudança estrutural devem ser reconciliados. Sem demonstração de comparabilidade, abster o campo/janela afetado; não misturar Banco Nacional com pares de empresa. Regras econômicas de reconciliação ainda não previstas permanecem pendentes, sem número provisório.
- Exercício encerrado em fevereiro: usar a DFP daquele ano quando disponível e encerrada antes da referência, sem esperar o próximo janeiro. Data de publicação/coleta é distinta da data final do exercício; reprodução histórica completa fica F3-1.
- Série com quatro exercícios deve expor os quatro e a lacuna; não preencher por repetição, nem deslocar o mais antigo para o corrente. Pacote §3 exige cinco completos/contínuos para os novos Graham/Lynch/qualidade da 2C-b. Gordon e bancos continuam exercício anual; Bazin continua12meses B3 por data ex.

## Competência, ações e proventos

| Entrada | Regime / uso | Abstenção ou limite |
|---|---|---|
| LPA anual por classe | D19: documento, ações, escala e direito do próprio exercício; divulgado coerente ou reserva autorizada | não usar quantidade atual para todos os anos; classes de direitos distintos não são intercambiáveis |
| Composição do capital | mesma data/versão; quantidade líquida de tesouraria segundo ficha | falta/escala indeterminada bloqueia conversão, não apaga fluxos monetários |
| DVA anual | dividendos e JCP bruto por competência do exercício; pares de empresa ou banco | não representa caixa/data ex B3; ausência da DVA não é ausência de pagamento |
| DVA, dividendos adicionais propostos | verificar rubrica de destinação/retidos e direitos conforme ficha; não somar retidos genéricos | sem marcação/atribuição demonstrada não promover proposta a pagamento por data ex; regra nova exige ficha/decisão |
| B3 | proventos brutos por data ex, janela nominal do Bazin e DY do perfil | calendário/eventos/fator oficial conforme pacote §7; extraordinário só marcação explícita; restituição fora da soma; RENDIMENTO em ação abstém |

JCP bruto da DVA não recebe desconto presumido de imposto para ser comparado ao líquido de outra fonte. Conferência de sete dias B3/yfinance é apenas aviso; não muda seleção nem valor. UNT é conferência. Ajuste de evento exige fator oficial, nunca preço ou quantidade presumidos. A direção de correção monetária do Graham e o CAGR do Lynch serão especificados nas fichas2.0; nenhum destes insumos informativos passa a método neste levantamento.

## Casos independentes para os próximos itens

Aritmética sintética, não valores copiados da implementação:

1. DRE consolidado100, controladora/terceiros0; BPP correspondente com participação0 e outras linhas válidas permite reserva100. BPP ausente/vazio/ilegível/outra versão deve deixar controladora sem valor; receita da DRE200 permanece.
2. Controladora explícita80 e DVA ilegível: lucro80/receita200 permanecem, dividendos/JCP indisponíveis com motivo. Provento declarado somente dividendos30, JCP ausente dentro da DVA válida, soma30 pela regra aprovada; DVA inteira ausente não autoriza30 nem0.
3. Acumulados de receita20,50,90 e DFP140, mesmo perímetro: trimestres20,30,40,50 e TTM140. Ações ausentes não impedem o total140; não há LPA calculável por essa evidência.
4. Documento anual março–fevereiro e acumulados trimestrais desse exercício: preservar limites publicados. Fevereiro bissexto não vira mês parcial. Intervalo31/01–01/03 não é trimestre completo (F2C-17).
5. Cinco LPAs2,3,4,5,6 com quantidades próprias e datas verificadas: série tem cinco observações. Remover uma cria cobertura4/5 e abstenção dos novos métodos de cinco exercícios, sem interpolação. Cinco observações contíguas não autorizam escolher denominador CAGR silenciosamente: a ficha2.0 deve explicitar número de intervalos.
6. Dois acumulados de modelos/perímetros distintos não autorizam a subtração do caso3; sem reconciliação, abstenção. Base de origem deve permitir auditar essa decisão.

## Entregue versus lacunas (não repetir trabalho)

| Item anterior | Evidência no código/testes | Lacuna/destino |
|---|---|---|
| F2B-37 | lucro_controladores_com_reserva já aplicado a cada acumulado com BPP filtrado por documento | legibilidade/presença efetiva do BPP não comprovada: F2C-30 |
| F2B-46 | domínios e rubrica única; negativos oficiais preservados; testes permanentes | não repetir soma de provento único nem domínio por método; novas falhas de fonte/perímetro em30/31 |
| F2B-48/F2B-54 | capital recente, escala e D0 oficial; DVA/UNT e eventos têm contratos próprios | conferência sharesOutstanding da composição em34; eventos22/23; não mudar lente anual |
| F2C-13/17/26 | leitura compartilhada, limites mensais completos, cache de leitura | preservar ganhos e controles, sem refactor misturado a fixes |

Consumidores: `CVMProvider.calcular_indicadores`, `indicadores_da_serie`, `_acumulados_do_arquivo`, `acumulados_ttm`, `_escala_da_composicao`, `gordon_do_documento`; `series_cvm.exercicio/serie_anual/trimestres/ttm`; `MarketEngine._serie_cvm/_por_acao_cvm`; relatórios de rastreabilidade e persistência integral. `serie_cvm`/`ttm_cvm` ainda são informativos para as novas janelas; lentes anuais vigentes têm contratos independentes. F2C-30 declara o predicado de campos informativos antes da correção; qualquer consumidor já econômico exige examinar o efeito e o golden.

Pendências econômicas explícitas para ficha/Marcos: reconciliação de mudanças estruturais/perímetros; atribuição entre classes com direitos distintos; tratamento que ultrapasse a regra vigente de dividendos adicionais propostos; convenção de cinco exercícios versus intervalos CAGR. Enquanto não houver regra, não calcular a transformação afetada. Casos de fonte/versão/legibilidade seguem abstenção conservadora, não aguardam escolha econômica nova.

## Aplicação conservadora no F2C-30

Comparabilidade é evidência de entrada, por campo: `proveniencia[campo].perimetro` identifica a base comparável, e `evidencia_comparabilidade` aponta a demonstração/reconciliação que a sustenta. Ambos precisam ser textos explícitos, não vazios; todos os documentos da subtração/soma precisam declarar o mesmo perímetro. Igualdade de modelo ou CNPJ não produz essa evidência automaticamente. A função pura confere o contrato recebido; o produtor dos dados responde por verificar a fonte. Nenhuma regra de reconciliação é criada aqui.

Sem essa evidência, a subtração ou soma afetada abstém com motivo, mantendo os acumulados e sua identidade documental. O provedor atual registra documento/modelo/janela, mas **não emite prova de comparabilidade estrutural**: o TTM que depender dela permanece indisponível até que uma fonte/reconciliação aprovada seja fornecida no contrato futuro. Não se troca isso por um sinalizador positivo presumido. Data, capital e método anual vigentes não mudam.

Nos casos de aritmética sintética da suíte, a homogeneidade é uma hipótese explícita da construção dos dados. As fixtures declaram essa hipótese como sintética, sem apresentá-la como confirmação oficial. Os controles separados sem evidência, com evidência inválida e com bases diferentes exigem abstenção. Não se altera nenhum número esperado nem se dispensa um teste antigo de cálculo.
