# F2B-31 — Bazin pelo critério fixo e pela relação B3, 20/10/2026

Executor: Claude Code. Referência normativa: ficha Bazin 1.0 e marcador da 2B (§2 a §2.3),
aprovados em 19/10/2026. Este relatório registra a fonte, o leiaute conferido, as escolhas
operacionais que a ficha deixava abertas e o antes → depois no universo inicial. Nenhum
parâmetro metodológico novo: taxa de 6%, gate de 5%, alerta de 15% e limite de 25% são os
da ficha.

## Fonte: relação de proventos em dinheiro da B3

Serviço CompanyCall de `sistemaswebb3-listados.b3.com.br`, parâmetros em JSON codificado
em base64 no fim do caminho. Respondeu em 20/10/2026 (contrato D18:
`tests/fixtures/contratos/b3_proventos_lren_2026.json`, coleta 2026-10-20T20:40:20Z,
SHA-256 da página de proventos `03dccd4333fed8554f9be6e205b90177fae83aa869a9303455d445e39d0c0e66`).

| Chamada | Parâmetro | Campos usados |
|---|---|---|
| `GetDetail` | código CVM do índice oficial | `tradingName`, `issuingCompany` |
| `GetListedCashDividends` | `tradingName`, `pageNumber`, `pageSize` (máximo 120: com 500 vem vazia e `totalRecords` nulo) | `page.totalRecords`, `page.totalPages`; por evento: `typeStock`, `corporateAction`, `valueCash`, `lastDatePriorEx`, `dateApproval`, `quotedPerShares` |
| `GetListedSupplementCompany` | `issuingCompany` | `stockDividends` (eventos em ações) e `cashDividends` (proventos recentes com ISIN) |

**Leiaute e escala, conferidos:**
- `valueCash` é **bruto** por ação, com vírgula decimal. O JCP da Lojas Renner com data
  com em 2025 soma R$ 0,83829 por ação; pela DVA de 2025, JCP de 834.310 mil sobre
  982.199 mil ações do fim do ano, R$ 0,8494 (diferença do denominador, com recompras); o
  líquido de 15% seria R$ 0,7220.
- `typeStock` separa ON, PN, PNA e PNB (USIMINAS: 55 ON, 48 PNA, 48 PNB nas três
  primeiras páginas). A unit não tem linha própria: a TAEE11 sai como ON e PN.
- `lastDatePriorEx` é o último dia com direito; a data ex é o pregão seguinte. Na Renner,
  as datas com 11/12/2025, 24/03/2026, 23/06/2026 e 22/09/2026 correspondem às datas ex
  12/12/2025, 25/03/2026, 24/06/2026 e 23/09/2026 da conferência do yfinance da ficha.
- `quotedPerShares` é 1 desde os anos 2000; nos anos 1990 aparece 1000 (valor por lote).

**Exemplo da ficha, §5, pela fonte escolhida:** LREN3, preço de 30/09/2026 (R$ 11,60),
janela (30/09/2025, 30/09/2026]: quatro JCPs brutos, D = R$ 0,920447, DY = 7,934888%,
critério = R$ 15,340783 — os mesmos números da conferência do yfinance da ficha, agora pela
relação B3 (`tests/test_contratos_provedores.py::test_contrato_proventos_b3`).

## Escolhas operacionais (a ficha não as detalhava)

Cada uma é conservadora no sentido da ficha ("sem insumo, abstém-se") e fica declarada para
a auditoria:

1. **Data ex pela data com.** Com o preço num pregão, data ex ≤ referência ⇔ data com <
   referência; data ex > início ⇔ data com ≥ início. Data com até sete dias antes do início
   fica fora (hipótese declarada: a B3 não fica sete dias seguidos sem pregão); entre seis
   dias e um dia antes, a data ex é decidida pelo calendário de pregões do COTAHIST, e sem
   ele a série se abstém.
2. **Preço de referência.** O fechamento do último pregão encerrado antes do dia do as_of
   (marcador, §2.2), entre os últimos fechamentos do histórico do yfinance. O valor do
   critério é D ÷ 0,06; o DY é D sobre esse fechamento. Sem fechamento anterior ao dia do
   as_of, abstenção.
3. **Natureza.** Somam-se só "DIVIDENDO" e "JRS CAP PROPRIO". Outra natureza na janela
   ("REST CAP DIN", "RENDIMENTO") abstém, com o rótulo no motivo (ficha, §4: natureza
   desconhecida invalida a série).
4. **Eventos em ações na janela** (bonificação, desdobramento, grupamento, cisão, resgate):
   abstenção por direito não reconciliado. Esta versão não converte os proventos anteriores
   pelo fator; a reconciliação fica para um item futuro, se decidido.
5. **Cobertura.** Todas as páginas lidas (registros = `totalRecords`) e algum provento,
   de qualquer espécie, com data com antes do início da janela. Sem isso, abstenção.
6. **Emissor.** A relação vem pelo nome de pregão, e a busca é instável com barra
   ("AMBEV S/A" devolve 0 registros; "AMBEV SA", 40; "AMBEV", 134; "KLABIN S/A", 0;
   "KLABIN SA", 219). Os proventos recentes do complemento, que vem pelo código do emissor e
   com o ISIN, têm de estar todos na relação (espécie, natureza, data com e valor), quando
   a data com é anterior à referência. Falta qualquer um: abstenção. Não se tentam variações
   do nome.
7. **Disponibilidade.** Provento aprovado depois do dia do as_of não entra; sem data de
   aprovação na janela, abstenção. A relação coletada depois do as_of não prova
   disponibilidade anterior (marcador, §2): abstenção.
8. **Conferência no yfinance.** Mesma janela, data ex do yfinance, valor por papel; aviso se
   a soma diverge mais de R$ 0,000001 por evento conferido (o yfinance publica seis casas:
   TAEE11, B3 R$ 3,0064572, yfinance R$ 3,006456). Sem dividendos no histórico, aviso de
   indisponibilidade. Nunca muda a série.
9. **Escopo pelo BPP.** O modelo vem das contas do BPP consolidado do documento da CVM
   (`CVMProvider.modelo_do_documento`, a regra do Gordon), não do setor. Banco e documento
   sem o PL do modelo empresa se abstêm.

## Lacunas frente à ficha (não implementadas nesta versão)

- **Distribuição extraordinária** (ficha, §3: "identificada com aviso de não recorrência"):
  a relação B3 não marca o provento extraordinário, e nenhum aviso é gerado. No universo,
  RECV3 (DY de 10,7% pela B3 contra 5,4% na cascata) e VALE3 (8,6% contra 6,6%) calculam
  sem esse aviso.
- **Conferência no yfinance por evento** (ficha, §2: valor, natureza, data ex e cobertura,
  com as diferenças): compara-se só a soma da janela; divergências que se compensam passam
  sem aviso.
- **Perfil:** o Bazin usa o perfil pelo DY da B3; Graham e Lynch seguem com o perfil pelo
  DY da cascata. Com ROE acima de 20%, DY da cascata abaixo de 4% e DY da B3 a partir de 5%,
  Lynch e Bazin entram juntos na mediana, o que antes não acontecia.
- **Duplicatas:** registros idênticos (espécie, natureza, valor, data com e aprovação) contam
  uma vez; dois proventos legítimos idênticos seriam somados uma vez só.
- **Preço:** o histórico do yfinance vem ajustado por proventos (`auto_adjust`); no pregão
  ex, o fechamento anterior de referência pode vir ajustado, e o DY do gate, levemente
  maior. O valor do critério (D ÷ 0,06) não depende do preço.

## Universo inicial: antes e depois

Os 51 papéis STOCK/UNIT do retrato público do F2B-21. A cascata atual coletou os dados uma
vez (20/10/2026, 21:05 UTC; `outputs/f2b31_b3/universo_dados.pkl`, fora do git, SHA-256
`a36b026a526eaeea23f55a11793dcd90e0254e5191edb8bd8902894e477ff3fe`), e os mesmos `dados`
passaram pelo motor do HEAD (e7907fb, Bazin 1.0.1 pela Selic) e pelo da árvore do item,
com as_of 20/10/2026 23:00 UTC e Selic de 14,75% nos dois. A diferença vem só do código.
Tabela por papel em `docs/decisoes/f2b31-universo.csv`.

| Medida | Antes | Depois |
|---|---|---|
| Papéis com Bazin calculado | 14 | 7 |
| Mediana de Bazin ÷ preço − 1, entre os calculados | −56,3% | +20,2% |
| Mediana do preço justo do motor (R$) | 14,36 | 19,38 |
| Classificações sinal positivo / neutro / sinal negativo | 11 / 23 / 17 | 17 / 25 / 9 |

Os sete que calculam nos dois: CMIG4 7,87 → 10,71; LREN3 6,59 → 15,34; RECV3 4,66 → 22,74;
TIMS3 11,50 → 24,54; VALE3 29,19 → 93,54; TAEE11 21,02 → 50,11; BRBI11 9,97 → 23,00. Os que
perdem o Bazin: CYRE3 (bonificação com data com em 30/12/2025), KLBN11 (relação pelo nome sem um provento do complemento), PETR4 e VIVT3 (outra natureza na janela) e os bancos BRSR6, BMGB4 e
SANB11 (fora do escopo pelo modelo). Doze classificações mudam, todas pelo Bazin (o Gordon é
o mesmo nos dois motores).

Motivo do Bazin depois, nos 51: 10 com série B3 válida e o método se abstendo (gate, perfil
ou confiança); 1 pela guarda de situação especial, antes de qualquer método (MGLU3); 10 bancos; 8 eventos em ações na janela (seis bonificações de novembro e
dezembro de 2025, um desdobramento e um resgate total); 7 calculam; 6 sem provento na janela (rendimento zero: CSAN3, ENEV3, HAPV3, MRVE3, USIM5, NATU3);
4 com a relação pelo nome sem um provento do complemento (ABEV3 e KLBN11 pelo nome com
barra; RADL3 e IGTI11 com anúncio de outubro de 2026 ainda fora da relação); 3 com outra
natureza na janela (LWSA3 e VIVT3 com restituição de capital, PETR4 com "RENDIMENTO"); 1 sem
modelo empresa demonstrado (ASAI3); 1 sem provento antes da janela (AZUL3).

Limites desta comparação: preços e históricos de uma única coleta, com o fechamento de
19/10/2026 como referência; a Selic de 14,75% é a de contingência, também semente dos
testes; os eventos em ações e a busca pelo nome deixam fora papéis que pagaram proventos, e
isso é abstenção, não rendimento zero.
