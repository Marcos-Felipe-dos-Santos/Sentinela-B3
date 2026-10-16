# Fichas metodológicas

Uma ficha por lente ou definição de cálculo (ADR-0003, D21). Nenhuma implementação começa sem a ficha aprovada pelo Marcos e revisada pelo auditor externo (`docs/loop/auditoria-externa.md`, modo FICHA).

## Modelo

```markdown
# <Lente ou definição> — versão <x.y>

**Status:** rascunho | revisada | aprovada (data, por quem)
**Itens que dependem:** F2A-…, F2B-…

## 1. Fórmula e referência
<fórmula> — fonte: <norma, livro ou artigo, com página ou seção>

## 2. Insumos
| Insumo | Definição exata | Fonte | Unidade e escala | Data de referência |

## 3. Regime, janela e data
Real ou nominal; janela e por quê; qual data de referência vale.

## 4. Hipóteses e inaplicabilidade
Quando a lente se abstém, com o texto do motivo.

## 5. Exemplo calculado de forma independente
Dados de entrada (empresa real ou sintética), conta passo a passo, resultado. Calculado sem usar o código do projeto.

## 6. Sensibilidade
Como o resultado muda com as premissas principais (tabela).

## 7. Parâmetros e justificativa
Cada parâmetro com valor e motivo (D23).
```
