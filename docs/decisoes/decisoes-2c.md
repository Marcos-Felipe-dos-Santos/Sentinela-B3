# Decisões antecipadas da Fase 2C — proposta para aprovação

**Preparada pelo Claude (chat) em 25/10/2026** sobre `docs/loop/fila-fase2c-proposta.md` (47 itens, 8 marcadores `[DECISÃO]`, contando o "Bazin na mediana" da `docs/pos-2b`). Cada linha traz a sugestão e o motivo. As decisões só valem depois que o Marcos as aprovar. Quando uma decisão exige ficha (D21), a ficha continua obrigatória antes do código: a decisão fixa a direção, e a ficha fixa os números.

## 0. Estrutura da fase: duas metades

A proposta mistura itens mecânicos (bugs adiados, levantamentos, testes) com itens que dependem de ficha (janelas, qualidade, apresentação, Lynch). **Sugestão:** ativar em duas filas.
- **2C-a, sem ficha e sem golden.** F2C-13 a 21, 26 a 47 (os `fix:` de bugs, os levantamentos e os testes), F2C-7 (pares), F2C-8 (auditoria.py) e F2C-9 (fim do Markowitz). Roda logo depois da auditoria DOCUMENTO, num loop longo como o plano final da 2B.
- **2C-b, com fichas.** F2C-1, 12, 2, 3, 5 e 4. Começa quando as fichas de janelas, Lynch, qualidade e apresentação estiverem aprovadas. As fichas são escritas em paralelo à 2C-a.

Ganho: o loop não para esperando ficha, e as fichas são escritas sobre um código já sem os bugs adiados.

## 1. Bazin na mediana, e a apresentação (F2C-5)

**Sugestão:** acabar com a mediana única de valor justo. Cada lente aparece separada (D24, F2C-5), com hipótese, regime, janela e resultado ou motivo. A mistura apontada pela auditoria não é só do Bazin. Graham e Lynch também não são modelos de desconto, e a mediana junta critério nominal, fórmulas heurísticas e avaliação real. Separar as lentes resolve a mistura na raiz. "Tirar só o Bazin" deixaria o problema nos outros dois.
- O Bazin vira **critério de rendimento** ("atinge / não atinge os 6%"), com o preço-limite como informação, e não como "valor justo".
- A classificação deixa de sair da mediana e passa a seguir a seção 2.

## 2. Qualidade, classificação e histerese (F2C-2, F2C-3)

- **Lente de qualidade (F2C-2):**
  - indicadores de 5 exercícios, mostrados como **faixas descritivas, sem nota única e sem pesos**: ROE médio e dispersão, lucro positivo em N de 5, margem, dívida líquida/EBITDA com o caso EBITDA ≤ 0 explícito, regularidade de proventos;
  - as faixas vêm da ficha, com fonte;
  - a qualidade fica num bloco próprio e não altera o valor de nenhuma lente.
- **Classificação (F2C-3):**
  - por lente, com três estados ("sinal positivo", "neutro", "sinal negativo") pela distância entre o preço e o resultado da lente, com banda neutra;
  - a largura da banda vai na ficha de apresentação, com a dispersão das lentes no universo como evidência, e não um número escolhido pelo resultado;
  - a sigmoide sai;
  - não há classificação agregada nesta fase. Quando houver mais de uma lente, o relatório mostra o quadro das lentes, e não um rótulo-síntese.
- **Histerese:** pertence aos alertas, que têm estado (D26), e não ao motor. Na 2C, só a especificação do contrato (banda, entrada, saída, repetição), entregue ao **F4-2**, que é a fase do monitoramento contínuo. O motor continua sem estado e determinístico.

## 3. Janelas por lente (F2C-1)

- **Gordon e bancos:** **não mudam**. Mantêm o exercício anual (DFP), aprovado em 19 a 25/10 com ficha e auditoria.
- **Bazin:** **mantém os 12 meses por data ex da B3** (ficha 1.2). A média de 5 anos aparece como contexto, sem entrar no critério.
- **Graham:** o **LPA médio de 5 exercícios**, cada um com as ações do próprio documento, convertido para a moeda do último exercício pelo IPCA (é um valor nominal médio). O VPA é o último. A referência é a recomendação de lucro médio de Graham e Dodd, a conferir na ficha. **Ficha Graham 2.0.**
- **Lynch:** **CAGR de 5 anos do LPA dos controladores**. Abstém com LPA ≤ 0 no início ou no fim, e com menos de 5 exercícios contínuos. **Ficha Lynch 2.0.**
- **Regras comuns:**
  - 5 exercícios completos e contínuos, senão abstém;
  - pela revisão 2.1 aprovada em 28/10 (§12), razões de ações consecutivas estritamente em (0,9; 1,1) demonstram compatibilidade; fora, fator oficial B3 ou abstenção;
  - reorganização societária recebe aviso fixo sem abstenção; detecção destinada à Fase 3 (§12).

## 4. Lynch e perfil (F2C-12)

- O payout do Lynch passa a usar a **mesma fonte de DY do perfil**: B3 quando válida, a cascata com aviso caso contrário. Assim, nenhum ativo tem perfil e payout de fontes diferentes.
- Um ativo que perde Lynch e Bazin pelas regras **continua sem os dois**. Abster é honesto; preencher não.
- O CAGR é a versão 2.0 do Lynch, com ficha (D21/D28), no mesmo item.

## 5. Escopos futuros (F2C-24, F2C-25)

- **Só levantamento na 2C, sem implementação.**
  - F2C-24: contar e caracterizar os 78 tickers só com demonstrações individuais, e conferir os casos suspeitos (**ASAI3** primeiro: confirmar na CVM se ela de fato não publica consolidado em 2025, ou se é erro de leitura; se for erro de leitura, vira bug);
  - F2C-25: fontes para papel e fundos de fundos.
- **Seguradora:** sem lente na 2C.

## 6. Reverso (F2C-6)

**Dispensar na 2C.** É opcional, exige ficha completa (DFC, horizonte, terminal, solver), e a fase já é grande. Vai para a fila de ideias da Fase 3 ou posterior.

## 7. Proventos e eventos (F2C-22, 23, 26)

- **Emissor com barra (BUG-2B-29):** consultar a relação de proventos da B3 pelo **código CVM** (a mesma chave do registro GetDetail usado no BTG), e não pelo nome de pregão. Se a API não aceitar o código, usar o nome de pregão do próprio registro GetDetail, sem montar o nome à mão.
- **UNT:** só conferência (já decidido em 20/10).
- **Desdobramento e grupamento:** pela lista oficial de eventos em ações da B3, com o fator. Sem o fator oficial, abstém.
- **Distribuição extraordinária:** continua com o aviso fixo. A identificação só entra se a fonte oficial trouxer marcação explícita, e o F2C-22 confere isso.
- **Conferência B3 × yfinance com 7 dias de tolerância na data ex:** mantida **só como aviso**, sem efeito no cálculo, e documentada como hipótese de conferência.
- **"Restituição de capital":** fica **fora da soma de proventos**, com aviso, porque é devolução de capital e não rendimento. A natureza "RENDIMENTO" em ação faz a série abster, com motivo.

## 8. Compatibilidade, banco e interface (F2C-4, F2C-27)

- **Sem migração de SQLite na 2C.** As análises antigas são lidas por um **adaptador na leitura** (COMPRA/NEUTRO/VENDA → sinal positivo/neutro/sinal negativo), com teste. O trabalho de schema vai para a Fase 3, com o backup e a restauração da D29.
- **`app.py`: permissão limitada.**
  - pode trocar os textos dos rótulos para o vocabulário novo;
  - pode remover a seção "Alocação Sugerida" (F2C-9) e mostrar as lentes separadas (F2C-5);
  - o executor lista as linhas exatas antes de mexer;
  - nenhuma outra mudança de interface (a migração é a Fase 7).

## 9. Ordem e paradas

Valem as regras da seção 1 do plano final da 2B (`docs/decisoes/plano-final-2b.md`):
- decisão provisória pelo lado da abstenção, sem parar;
- `[!]` só nos seis casos listados lá;
- revisão reprovada só por texto não para;
- auditorias externas no fechamento de cada metade.

## 10. Próximos passos

1. O Marcos aprova este documento, ou ajusta por número de seção.
2. O executor grava as decisões na proposta (marcadores e aceites) e divide a fila em 2C-a e 2C-b.
3. Auditoria DOCUMENTO da proposta revisada (Codex).
4. Ativação da 2C-a, enquanto as fichas Graham 2.0, Lynch 2.0, qualidade e apresentação são escritas e auditadas (FICHA).

## 11. Aprovação e decisões finais do Marcos — 28/10/2026

Após `auditoria-2c-a-final-e-fichas-claude-relatorio.md` (Claude,D30), 2C-a pode seguir. As decisões seguintes prevalecem sobre propostas anteriores e fichas emrascunho:

- Qualidade1.0 aprovada: PLinicial, desvio populacional, B3data-ex, quadroparcial com cobertura; sem pesos/nota e sem alterarvalores.
- Graham2.0 aprovada: LPA médio de5exercícios, ações/fatoresoficiais por documento, IPCA do fim de cadaexercício eVPAúltimo. Retirar pisoP/L7 e guardasP/L25/PVP2,5/3; limiteé22,5=15×1,5 na fórmula.
- Lynch2.0 aprovada:5observações/4intervalos, expoente1/4; m1; teto g25%; semPLmáximo; payoutapenascontexto, fontecomumDYperfil; prejuízointermediáriopermitido comextremospositivos.
- Apresentação1.0 aprovada: **sem rótulo por lente na2C**; valoroumotivo,regime,janela,distânciaaopreçoem%; Bazin “atinge/nãoatinge6%”. Banda/sinaisFase3combacktest; rejeitada banda33,50% da discordânciaentremétodos. HisteresesomentecontratoF4-2.
- F2C-3/4semrótulosporlente; F2C-4vocabulário “distânciaaopreço” e adaptadordeleiturahistórica, semmigração.
- Ativar2C-b:1,12,2,3,5,4; merge da main antesdofechamento emcommitpróprio;10limpeza(inclusiveFNETtrechomínimo+hashoriginal),11resumo/arquivo. Parar “Checkpointda2C”. Sempush.

Aprovação da fila não aprova novos critérios econômicos além dessas fichas/decisões. Mesmasregrasdeparada/D27/G; golden só nopredicado préviodecadaitem.


## 12. Desbloqueio do F2C-1 — fichas 2.1 aprovadas em 28/10/2026

Decisões expressas do Marcos posteriores ao §11, que prevalecem sobre as exigências anteriores de reconciliação histórica:

1. **Compatibilidade da base de ações:** aplicar a mesma regra do Gordon 1.1 entre cada par de exercícios consecutivos dos cinco documentos. A razão ações em circulação posteriores ÷ anteriores, com a escala de cada documento pela ficha por ação 1.1, estritamente em **(0,9; 1,1)** demonstra ausência de desdobramento/grupamento. Fora do intervalo, ajustar o LPA pelo fator oficial B3 quando existir; sem fator oficial, abster com motivo. Limites 0,9 e 1,1 não pertencem ao intervalo; não usar a razão como fator estimado. Acumular os fatores oficiais até a base final. Quantidade ou escala ausente não prova compatibilidade.
2. **Reorganização societária:** exibir o aviso fixo **"reorganização societária no período não é detectada"**, sem abstenção por fusão/cisão/perímetro. **Destino: Fase 3**, detecção com fonte e contrato próprios antes da implementação. Não confundir essa limitação com escala, fator ou direitos de classe ausentes, que mantêm seus motivos próprios.
3. **IPCA do Graham:** estender o produtor existente do SIDRA **1737, variável 63**, com produto dos fatores mensais e corte pelo calendário de publicação do IBGE, à janela de cinco exercícios e aos respectivos encerramentos. Cobertura incompleta, IPCA indisponível ou não publicado até as_of produz abstenção com motivo. Não substituir pela variável de número-índice. **Lynch continua nominal, sem IPCA.**

Fichas Graham e Lynch passam a **2.1**, aprovadas, com exemplos e matriz da compatibilidade. O F2C-1 deve completar produtores, testes e gates antes de fechar; retirar o bloqueio não equivale a declarar entrega parcial aceita. Registrar no diário novas contagens antes → depois e abstenções por motivo no universo inicial. A ordem restante e a parada no "Checkpoint da 2C" permanecem; sem push.
