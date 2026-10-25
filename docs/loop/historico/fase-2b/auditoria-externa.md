# Auditoria externa da Fase 2B — consolidação

**25/10/2026. Consolidação pelo Claude (chat), com as decisões do Marcos da mesma data.** Branch `v2/fase-2b`, HEAD `e75ebe7`.

## Pareceres

| Auditoria | Executor auditado | Veredito |
|---|---|---|
| Codex, modo FASE (`auditoria-fase-2b-codex-3-relatorio.md`) | fase inteira, com foco nos itens do Claude Code | **não pode seguir** |
| Gemini, modo FASE (pacote em 10 partes) | fase inteira | **aprovado com ressalvas**, sem bloqueio |
| Claude (chat), D30 dos itens do Codex | F2B-46, 27, 29, 47, 48, 30, 1, F2A-39, F2B-44, 3, F2A-10, 33, 34 | pode seguir; as ressalvas foram fechadas no F2B-45 e no F2B-54 |

Os dois pareceres de fase conferem toda a aritmética das fichas: taxa real, Gordon ABEV3, bancos ITUB4, Bazin e FII HGLG11. A divergência entre eles está toda na **fronteira de elegibilidade da lente de FII** (F2B-2) e na integração da completude dos bancos. O Gemini não reproduziu esses casos; o Codex reproduziu cada um.

## Bloqueios — fila de fechamento

Todos confirmados por reprodução do Codex. Cada um vira regressão em `tests/regressao/` antes da correção (D27).

| ID | Defeito | Correção exigida |
|---|---|---|
| BUG-2B-37 (reaberto) | o conflito de mesma versão no Informe só compara DY e VP; cotas e amortização ficam fora, e a ordem das linhas muda a elegibilidade | conflito em qualquer campo usado (DY, VP, cotas, amortização, composição) abstém, nas duas ordens |
| BUG-2B-46 | a lente de FII não confere o as_of, a data-base nem a idade do registro da NTN-B; a coleta do Informe e da B3 posterior ao as_of é aceita | mesmo corte do F2B-30 e do Gordon: registro da taxa com as_of ≤ análise e idade válida; coleta e entrega do Informe e da B3 até o as_of |
| BUG-2B-47 | composição de outra versão, ou conflitante, autoriza a lente | a composição precisa ser da mesma versão do complemento selecionado; conflito abstém |
| BUG-2B-48 | VP final inválido (None, 0, negativo, NaN, inf) não impede a elegibilidade | os 13 VPs validados, inclusive o último |
| BUG-2B-49 | amortização ausente aceita como "sem amortização" | pela decisão 4 abaixo |
| BUG-2B-50 | a abstenção do FII devolve `fair_value = preço` e `upside = 0` | sem valor e sem upside numéricos, com o motivo; score contextual como decidido em 25/10 |
| BUG-2B-06 (reaberto) | a completude lê `modelo`, e a cascata grava `modelo_bpp`: um banco completo sai com 70% | alinhar produtor e consumidor; regressão pela saída real da cascata |

Depois das correções, a calibração do spread do FII é refeita **só para medir** o efeito na amostra. A constante de 3,5058% não muda sem decisão do Marcos.

Também na fila de fechamento:
- **Sincronizar `CLAUDE.md` e `docs/PLANO.md`** com o estado final (F2B-4 e F2B-32 entregues, escopo por BPP, liquidez, lente de bancos, FII). A seção "Fase atual" do `AGENTS.md` continua do Marcos.
- **Contraprova da D27 refeita** para o F2B-54 e o F2B-2 nos testes em que a falha registrada foi de importação, interface ou coleta, e não econômica. Isso vale salvo quando a contraprova correta for impossível; nesse caso, a dispensa fica escrita no diário com o motivo.

## Decisões do Marcos, 25/10/2026 (perguntas do Codex)

1. **Decisões provisórias restantes, ratificadas:**
   - exceções de proveniência nas chamadas diretas;
   - IF.data escolhido pelo setor (só leitura, sem efeito no valor; a escolha pelo BPP vai para a 2C);
   - inadimplência sem o calendário oficial de publicação (data-base declarada; o calendário vai para a 2C);
   - banco abstido sem valor numérico.
2. **BRSR3:** a abstenção da companhia inteira é mantida. Separar a ON das preferenciais exige demonstrar direitos e atribuição dos insumos, e vai para a 2C.
3. **Células vazias na composição do Informe:** vazio = zero só quando o registro de composição do fundo-mês existe, é da mesma versão e tem ao menos uma posição preenchida. Registro ausente, ou todo vazio, é tipo desconhecido e abstém.
4. **Amortização vazia (ficha FII 1.3):** vazio dentro de um registro de complemento válido, da mesma versão, vale como amortização zero, pela mesma lógica do item 3 (campo do formulário preenchido só quando há evento). NaN, texto ou negativo abstém. Se o executor achar especificação oficial em sentido contrário, `[!]`.
5. **Desvios da D27:** contraprovas refeitas, como acima, sem dispensa genérica.

## Ressalvas não bloqueantes, para a proposta da 2C (F2B-34)

Do Gemini:
- `CVMFIIProvider._preco_cotahist` sem conferir `meses_ausentes` nem a idade da cotação;
- `_escala_da_composicao` sem a confirmação pela `sharesOutstanding` da §7.7: alinhar, ou documentar que a razão (0,9; 1,1) contra a DFP cumpre esse papel;
- BUG-2B-09, já em F2C-19;
- teste da DVA extraordinária no layout 7.09 de bancos.

Do Codex:
- vocabulário legado dos motores, já destinado à 2C.
