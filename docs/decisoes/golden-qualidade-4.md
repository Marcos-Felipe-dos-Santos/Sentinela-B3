# Cobertura da Qualidade no golden dos motores — plano (F4-A19)

Levantamento do achado 12 do Gemini, em 25/11/2026, sobre o HEAD `3a63b2a`. O golden está em
`tests/fixtures/golden_motores.jsonl`, SHA-256 `1759c55f7e5995f5…`, com 2291 casos: 2003 de
ações e 288 de FII. **Nenhuma regeneração neste item.** A decisão é do Marcos no checkpoint do
bloco 0 (pacote P1).

## 1. O que o golden fixa hoje

Contagem feita sobre o próprio arquivo, lendo `saida.qualidade` de cada caso de ações:

| Situação da Qualidade | Casos |
|---|---|
| Cinco exercícios observados (`cobertura.observados = 5`) | 1924 |
| Banco sem comparabilidade demonstrada (`motivo`: "comparabilidade dos cinco exercícios não demonstrada; dados individuais preservados") | 60 |
| Classe ou modelo fora do quadro (ETF, BDR, UNKNOWN, seguradora) | 14 |
| Sem quadro (preço não finito e caso vazio, que não chegam ao motor) | 5 |

O achado diz "0 observações", e a leitura exata é outra. Nos 1924 casos, os exercícios existem: o
`apoio_janelas.enriquecer_janelas` grava a `serie_cvm` de 2021 a 2025 com perímetro e evidência de
comparabilidade. Mas **os cinco indicadores estão vazios em todos os 9620 exercícios**:

| Indicador | Preenchido | Motivo dominante |
|---|---|---|
| Lucros (`lucro_controladores`) | 0 | "lucro dos controladores não demonstrado ou inválido" (9620) |
| ROE | 0 | "PL inicial não positivo, ausente ou razão não representável" (9620) |
| Margem consolidada | 0 | "receita consolidada não positiva/ausente ou lucro consolidado inválido" (9600); "não aplicável ao modelo banco" (20) |
| Alavancagem | 0 | "EBITDA não demonstrado ou dívida financeira não demonstrada/razão inválida" (9600); "não aplicável ao modelo banco" (20) |
| Proventos | 0 | "calendário anual B3 sem cobertura demonstrada" (9585); "relação B3 anual indisponível" (35) |

O golden prova a identidade dos exercícios e os motivos de abstenção, mas nenhum valor da Qualidade.
Um erro de fórmula em `sentinela/methods/qualidade.py` passaria pelo golden. Hoje o que o
pegaria são os testes unitários do método.

## 2. Insumos que faltam

Por exercício, `qualidade._linha` lê os números de `serie_cvm.exercicios[i]`:
- `lucro_controladores`, `pl_inicial_controladores`, `lucro_liquido`, `receita_liquida`,
  `divida_liquida` e `ebitda`;
- a identidade e a janela do documento: `cnpj`, `modelo`, `dt_refer`, `versao`, `proveniencia`
  (com `data_entrega` e `data_coleta` até o as_of), `pl_inicial_proveniencia` e
  `pl_inicial_motivo`.

O `enriquecer_janelas` não grava nenhum dos seis números nem `cnpj`, `modelo` e `pl_inicial_*`.

Para os proventos, `qualidade_inputs._provento` exige, além da relação `proventos_b3` (que o
`enriquecer_bazin` já grava), um `calendario_proventos_b3` com:
- `fonte`;
- `coleta` até o as_of;
- `inicio` e `fim` cobrindo cada exercício com 7 dias de folga nas bordas;
- `pregoes` com pregões nas duas bordas.

A janela de 12 meses do `proventos_b3.serie_12_meses` precisa coincidir com o exercício contábil.

## 3. Opções

**(A) Enriquecer o apoio comum.** O `enriquecer_janelas` passa a gravar os seis números, a
identidade e o calendário. Atinge os 1924 casos de uma vez: todos mudam no campo `qualidade`.
- Predicado: em cada caso, só `saida.qualidade` muda, e todas as outras chaves ficam idênticas,
  byte a byte, depois da serialização do golden.
- Custo: diff do golden em ~1924 linhas, difícil de revisar à mão. Os valores sintéticos seriam
  os mesmos em quase todos os casos, então a cobertura cresce pouco.

**(B) Família nova de casos de Qualidade (recomendada).** Um gerador `_acoes_qualidade()` em
`tests/golden_motores.py`, com um apoio novo `tests/apoio_qualidade.py`. Ele acrescenta casos
pequenos e legíveis, sem tocar nos existentes.
- Predicado: os 2291 casos atuais ficam byte a byte iguais, na mesma ordem, e só entram as linhas
  novas, no fim da grade de ações (antes do FII, na ordem de `montar_casos`).

**(C) Lacuna declarada.** Sem regeneração na Fase 4. A limitação vai para o `CLAUDE.md`, na
armadilha 7 ("suíte verde não é sinal"), e para a proposta do bloco 2.

## 4. Casos da opção (B)

Na opção (A), os casos a enriquecer seriam os 1924 do §1. Na (B), os casos abaixo ocupam esse lugar. `_acoes_taxa_bazin()` é hoje o último gerador de ações em `montar_casos`. Os cenários de entrega depois do as_of e de leitura por publicação devem ser conferidos contra `qualidade._janela` e `_fonte` antes de gerar.

Todos com classe STOCK (ou UNIT, onde dito), as_of `AS_OF_GORDON` e valores sintéticos redondos,
anotados no próprio caso, sem dado de mercado.

| Id | Cenário | O que prova |
|---|---|---|
| `qualidade-empresa-completa` | Empresa, cinco exercícios com os seis números positivos e calendário cobrindo 2021–2025 | Os cinco indicadores preenchidos, com cobertura 5/5 e o resumo (média e desvio populacional do ROE) |
| `qualidade-banco-completo` | Banco com perímetro e evidência de comparabilidade | ROE, lucros e proventos preenchidos; margem e alavancagem "não aplicável ao modelo banco" |
| `qualidade-unit` | UNIT com `acoes_por_unit` | Proventos pela composição da unit |
| `qualidade-sem-lucro` | Um exercício sem `lucro_controladores` | Só lucros e ROE do ano abstêm, com motivo; o resto fica |
| `qualidade-pl-inicial-zero` | PL inicial 0 num exercício | ROE abstém com o motivo de PL |
| `qualidade-sem-ebitda` | EBITDA ausente | Só a alavancagem abstém |
| `qualidade-receita-zero` | Receita 0 | Só a margem abstém |
| `qualidade-calendario-curto` | Calendário sem os 7 dias de folga no fim | Proventos abstêm com "calendário anual sem cobertura das bordas data-com/data-ex" |
| `qualidade-relacao-abstida` | `proventos_b3` com `abstencao` | Proventos abstêm com "relação B3 anual indisponível" |
| `qualidade-entrega-depois-do-as_of` | `data_entrega` de 2025 depois do as_of | O exercício sai da janela, e a cobertura fica 4/5 |
| `qualidade-por-publicacao` | `disponibilidade_por_publicacao = True` | Fonte lida pela publicação, como no backtest |
| `qualidade-perimetro-misto` | Perímetro diferente num ano | `comparavel = False`, com os dados individuais preservados |

Doze casos, com os valores esperados calculados à mão no próprio item de regeneração, antes de
gerar, para que o golden não seja o próprio oráculo.

## 5. Arquivos de uma futura regeneração (opção B)

- `tests/apoio_qualidade.py` (novo): monta `serie_cvm` e `calendario_proventos_b3` sintéticos.
- `tests/golden_motores.py`: `_acoes_qualidade()` e a chamada em `montar_casos`, depois de
  `_acoes_taxa_bazin()`.
- `tests/fixtures/golden_motores.jsonl`: só as linhas novas.
- `tests/test_qualidade_golden_valores.py` (novo): confere os valores à mão dos casos completos,
  independente do golden.
- `docs/decisoes/predicados-golden-4.md` (novo): o predicado do §3 (B), com o SHA anterior, o
  posterior e a lista de ids novos.
- Fila, diário e `tests/regressao/README.md` (se algum caso revelar bug, com xfail estrito antes).

Arquivos que não mudam: `sentinela/methods/**`, `valuation_engine.py`,
`sentinela/data/qualidade_inputs.py` e os testes protegidos (seções A/B/C e
`tests/test_equivalencia_motores.py`).

## 6. Recomendação

(B). Doze casos dão cobertura de valor aos cinco indicadores, aos dois modelos e às abstenções por
indicador, com um predicado verificável por comparação direta: as 2291 linhas antigas ficam
idênticas. A opção (A) muda quase todo o golden por um ganho pequeno. A (C) deixa a fórmula da
Qualidade sem trava de ponta a ponta.
