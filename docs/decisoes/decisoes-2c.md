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
  - evento societário no período só entra com o fator oficial (F2C-22), senão abstém;
  - mudança estrutural sem reconciliação abstém.

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
