# Plano de execução do restante da Fase 2B — decisões antecipadas

**Decisões do Marcos de 20/10/2026.** Proposta preparada pelo Claude (chat) a partir da fila em `c64d020` e aprovada pelo Marcos. Objetivo: rodar o resto da fila numa sessão longa, sem paradas que dependam de uma decisão já previsível. Este documento complementa a fila. Cada item da fila cita a sua seção aqui, e uma decisão escrita no item vale mais que este documento.

## 1. Regras de execução até o fim da fase

1. **Um executor só.** O Claude Code executa todos os itens que faltam. O Codex não executa nesta fase, salvo pedido do Marcos.
2. **Auditorias no fechamento.** Não há auditoria externa no meio do caminho. No fechamento:
   - o Codex audita, em modo FASE, todos os commits do Claude Code desde `c64d020` (D30);
   - o Gemini faz a auditoria de fase;
   - o Claude (chat) consolida.

   Cada item continua passando pela revisão interna do loop.
3. **Dúvida que não é de regra não para o loop.** Quando a fila e este plano não cobrem um caso de dado, de fonte ou de borda, o executor:
   - escolhe o lado da abstenção, com motivo explícito;
   - registra no diário como **"decisão provisória: <caso> → <escolha>"**;
   - segue em frente.

   O resumo do F2B-6 lista todas as decisões provisórias numa seção própria, para o Marcos confirmar ou reverter no fechamento.
4. **`[!]` só nestes casos:**
   - (a) mudança de regra econômica não prevista: fórmula, parâmetro, taxa, ou o escopo de um método além do decidido;
   - (b) arquivo fora das permissões da fila e da seção 2;
   - (c) teste existente que só passaria se enfraquecido;
   - (d) golden fora do predicado do item;
   - (e) fonte oficial indisponível que impede o aceite (fonte fora do ar não vira dado inventado);
   - (f) bug confirmado que exige decisão de destino e não cabe no item em curso.

   Nos outros casos vale a regra 3.
5. **Revisão interna reprovada só por texto não para o loop.** Se a reprovação é de citação, redação ou registro (sem código nem regra), o executor corrige e commita sem nova parada e anota no diário. O limite de rodadas do protocolo continua valendo para os achados de código ou de regra.
6. **Bug achado no caminho.** Segue o rito (`tests/regressao/`, xfail estrito antes da correção). Se cabe no item em curso, é corrigido nele. Se não cabe, vai para a proposta da 2C (F2B-34) com destino escrito, sem parar.
7. **Contexto da sessão.** Antes de o contexto acabar, o executor usa a skill `passagem` e retoma pela skill `retomar`, sem perguntar.
8. **Nada muda nas proibições:** sem push, sem `.env`, sem dados da carteira, sem apagar arquivo não rastreado, sem o vocabulário proibido em código novo.

## 2. Permissão geral de arquivos

Além das permissões da fila, qualquer item que falta pode alterar `sentinela/methods/base.py`, `sentinela/domain/units.py` e `sentinela/domain/enums.py`, **só de forma aditiva**:
- novos campos opcionais, tipos e enums, validados como no F2B-29;
- nenhum campo existente muda de nome, tipo ou padrão.

O F2B-5 continua com a permissão própria de remoção.

## 3. F2B-2 — rendimento do FII contra NTN-B + spread

1. **População da calibração:** todos os FIIs do Informe Mensal classificados como tijolo naquele mês, não só os 25 do universo inicial. A ligação ao ticker é pelo índice oficial (ISIN do COTAHIST). Os fundos sem ligação ficam fora e são contados. O viés de sobrevivência que sobra é declarado.
2. **Classificação temporal:** a composição do `ativo_passivo` do próprio mês, pela regra do universo inicial (maioria estrita sobre os ativos imobiliários identificados).
3. **Liquidez na calibração:** em cada mês, entram só os fundos que passam na regra de liquidez de FII decidida para o F2A-10 (presença ≥ 80% e volume mediano ≥ R$ 100 mil nos 63 pregões até o último pregão do mês), medida pela função de liquidez existente. É a mesma população que a lente vai aceitar depois do F2A-10.
4. **Eventos de cota na calibração:**
   - desdobramento ou grupamento oficial na janela de 12 meses do fundo exclui aquele fundo-mês;
   - fonte de eventos indisponível para um fundo-mês também exclui o fundo-mês, e não o mês inteiro;
   - as exclusões são contadas;
   - emissão com VP contínuo continua dentro.
5. **Série:** para cada mês, mediana entre os fundos válidos de (R de 12 meses ÷ fechamento do último pregão do mês) − média da taxa de aplicação da última data-base elegível até esse pregão. O spread é a mediana das 60 medianas mensais contíguas encerradas no último mês com Informe elegível. Mês sem fundo válido é lacuna; com lacuna nos 60 meses, o spread fica indisponível e a lente abstém. A janela não é reduzida.
6. **Constante:** o spread calibrado vira uma constante versionada, com valor, data da calibração, janela, número de fundos por mês (mínimo, mediana, máximo), exclusões e p25/p75. Ela fica no `MacroContext` e na ficha FII (registro da calibração). Não há recalibração automática em tempo de execução: uma nova calibração é um item novo. O valor não para o loop: vai para o resumo do F2B-6 como primeiro ponto de revisão do Marcos.
7. **Score:** os pontos de P/VP e o score continuam iguais (decisão de 19/10). A Selic líquida fica como contexto.

## 4. F2A-39 — BTG

- Composição da unit "1 ON e 2 PNA": a lente que vale é a de bancos (F2B-32), e o VPA por ação é o mesmo para ON e PNA. A unit recebe VPA × 3 × múltiplo.
- Gordon e Bazin não se aplicam ao BTG pelo modelo banco.
- Se a ligação pela tabela de correções falhar na leitura da fonte da B3, `[!]` pela regra 4(e).

## 5. F2B-4 — escopo

- **Sem BPP consolidado:** a companhia abstém (decisão de 19/10), mesmo quando só publica demonstrações individuais. Ler as demonstrações individuais vai para a 2C (F2B-34), com a contagem de afetados no diário.
- **Seguradora:** abstém de todos os métodos até ter lente própria. **Holding com BPP de empresa:** métodos de empresa.
- **Classe fora do índice:** vale a classe do classificador do F2A-43, e o modelo continua exigindo BPP.
- **Bancos:** de 2.03 em diante, ficam em abstenção de escopo até o F2B-32. Os casos de banco no golden ganham o `modelo` exigido pelo predicado do F2B-32.

## 6. F2B-44 — IF.data

Sem decisão nova. O instante de referência é sempre explícito, inclusive nos testes.

## 7. F2B-3 e F2B-32 — bancos

- **Ligação ao IF.data:** CNPJ da companhia → conglomerado prudencial pelo cadastro do próprio IF.data (instituição líder). Sem o vínculo, "inadimplência IF.data não informada: conglomerado não identificado", sem efeito no valor.
- **Unit (SANB11, BPAC11):** VPA da unit = VPA por ação × ações por unit. O múltiplo é da companhia. Composição inválida abstém.
- **Classes ON e PN (ITUB3/ITUB4, BBDC3/BBDC4):** mesmo VPA por ação e mesmo múltiplo. **PNA/PNB com direitos distintos (BRSR5/BRSR6):** abstém, como decidido.
- **Um método só por banco:** a mediana é a da própria lente. A confiança e os rótulos seguem as regras da V1, que o F2C refaz. Isso não é motivo de parada.
- **Inadimplência** só para leitura, como já está decidido. Basileia fica fora.

## 8. F2A-10 — liquidez

Sem decisão nova: a regra de 18/10 está completa. A guarda vem depois da de classe e da de escopo do F2B-4, e antes da de distressed.

## 9. F2B-33, F2B-34, F2B-45, F2B-5, F2B-6

- **F2B-34:** inclui todos os destinos "2C" deste plano e do diário (demonstrações individuais; Lynch; reconciliação de UNT; distribuição extraordinária; ressalvas do Gemini sem item na 2B; decisões provisórias que o Marcos mandar para a 2C).
- **F2B-5:** sai o campo `selic` do `MethodInputs` se nenhum método o exigir. `FII_DY_SELIC_RATIO_MIN` fica, porque o score do FII não mudou.
- **F2B-6:** o resumo traz, nesta ordem de revisão:
  1. o spread calibrado do FII;
  2. as decisões provisórias;
  3. o antes → depois da taxa real (prêmio de 4%, 5% e 7%);
  4. o golden de cada item;
  5. os bancos com a lente.

## 10. Fechamento — roteiro do Marcos

1. Push da branch: `git push origin v2/fase-2b`.
2. Auditorias:
   - `python scripts/auditar.py codex fase --fase 2b --foco "commits do Claude Code desde c64d020; decisões provisórias do diário"`;
   - `python scripts/auditar.py gemini fase --fase 2b`.
3. O Claude (chat) consolida as duas em `docs/loop/historico/fase-2b/auditoria-externa.md`. O que bloquear vira fila de fechamento curta.
4. O Marcos revisa o resumo (seção 9), confirma ou reverte as decisões provisórias e gera os relatórios do F1-12 do `[DECISÃO]` final.
5. Índice reconstruído, cache de fundamentos limpo, PR com merge commit, tag `v2-fase-2b`, "Fase atual" do `AGENTS.md`.
