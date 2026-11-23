# Política de decisão autônoma dos executores — Fase 3 em diante

**Aprovada pelo Marcos em 10/11/2026.** Vale para o Claude Code e para o Codex, que se revezam como executores. O objetivo é que o loop não pare à espera do Marcos ou do Claude (chat) por decisões que podem ser tomadas com critério fixo e revistas depois. Uma decisão escrita do Marcos num item vale mais que esta política. Esta política vale mais que um texto escrito pelo executor.

## 1. O executor decide sozinho ("decisão delegada")

O executor decide sem parar quando o caso cabe numa destas classes:

1. **Dado, fonte ou borda** que a fila não cobre: escolhe o lado da abstenção com motivo explícito.
2. **Regra derivável** do que já está aprovado (fichas, decisões numeradas, ADRs, pacote da fase): aplica a leitura mais restritiva compatível com o texto.
3. **Regra de identidade ou conferência de dado** (como o ISIN do F3-P01): adota a conferência mais forte que a fonte permite. Se nenhuma conferência for possível, abstém.
4. **Escolhas técnicas e de processo:** nome de arquivo, arquivo de teste novo, ordem de itens independentes, divisão de um item em dois, item `fix:` novo para um bug fora do escopo.
5. **Destino de bug:** registra com regressão (xfail estrito) e destino no item mais próximo que o cobre.
6. **Ressalva de auditoria** que não muda regra econômica: corrige no item, ou cria um item próprio.

**Desempates, nesta ordem:**
1. abstenção em vez de número;
2. fonte oficial em vez de derivada;
3. a opção reversível;
4. o escopo menor;
5. a opção que preserva o golden e os testes protegidos;
6. a opção mais simples de auditar.

**Registro obrigatório:** no diário, a linha `decisão delegada DD-NN: <caso> → <escolha> (classe <n>, desempate <n>; alternativas: …)`, e a mesma linha em `docs/loop/pendencias.md`, na seção "Para ratificar". O resumo de cada metade lista todas, e o Marcos ratifica ou reverte em lote no checkpoint. Reverter uma decisão vira item `fix:` com regressão.

## 2. Revisão cruzada no lugar da consulta

Toda decisão delegada das classes 2 e 3 é revista pela **outra família** na primeira oportunidade:
- na troca de executor, quem entra lê as decisões delegadas abertas e marca cada uma "confere" ou "contesta, com motivo";
- uma contestada que não tiver acordo entre as duas famílias vira `[!]` para o Marcos;
- se não houver troca até o checkpoint, a revisão acontece na auditoria cruzada do checkpoint (D30).

## 3. Parada real (`[!]`) só nestes casos

1. **Método:** mudar fórmula, parâmetro, regime, taxa, ficha aprovada ou escopo de método.
2. **Golden** fora do predicado do item, ou teste protegido (seções A/B/C, equivalência, `tests/regressao/`) que só passaria enfraquecido.
3. **Risco de perda de dado do Marcos:** carteira, banco ou backup. Qualquer migração, sobrescrita ou remoção sem backup verificado.
4. **Publicação e segredo:** push, PR, `.env`, dados da carteira em arquivo versionado.
5. **Volume:** projeção de brutos acima de 100 GB, ou disco livre abaixo do dobro da projeção, medido no sistema de arquivos onde está `data/`, dentro do WSL (decisão 39 do Marcos, 11/11/2026; antes, 20 GB).
6. **Decisão delegada contestada** sem acordo entre as duas famílias.
7. **Três reprovações de código ou de regra** no mesmo item (o limite do protocolo). Reprovação só de texto não conta. Exceção da decisão 49 do Marcos (19/11/2026), regra 3, só para itens de auditoria: na Fase 3 os `F3-AUD-*`; na Fase 4 (mantida em 23/11/2026) os do bloco 0 e os criados por uma auditoria de bloco (R2). A terceira reprovação de código não para o loop. Salve o stage como patch em `outputs/<item>.patch` (`git diff --cached`), guarde-o com `git stash` (nada se apaga), registre o achado com xfail estrito como limitação declarada da fase, mova a correção para a proposta da fase seguinte e siga a fila.
8. **Aceite escrito que não se cumpre** (Marcos, 16/11/2026, depois da DD-85): quando a condição de aceite de um item não pode ser cumprida, a saída é `[!]`, não uma decisão delegada da classe 2 que a contorne.

Num `[!]`, vale a regra "Item bloqueado": registrar, pular para os itens independentes e parar quando não houver mais nenhum.

## 4. Proibições que nenhuma decisão delegada muda

- sem push e sem PR;
- sem `.env`;
- sem dados da carteira em arquivo versionado;
- **sem apagar arquivo não rastreado ou branch: resíduo, mesmo criado pelo próprio executor, vai para a lista de resíduos**;
  exceção (Marcos, 16/11/2026): `mutants/`, o cache do mutmut ignorado pelo git, pode ser apagado pelo executor antes de uma mutação;
- nada de rede, banco ou relógio em `sentinela/methods/`;
- nenhum vocabulário proibido em código novo;
- refactor e mudança de comportamento nunca no mesmo commit.
