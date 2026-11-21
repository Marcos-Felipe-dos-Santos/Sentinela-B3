**Modo FICHA — segunda rodada restrita.** Base: `v2/fase-3 @ 29d14c9`; diff `648d769..29d14c9`, somente `docs/metodologia/backtest.md`. Critérios gerais aplicados apenas aos trechos alterados, conforme decisão 42. Nenhum arquivo alterado; relatório anterior preservado; aprovação 41 não aplicada.

### Status e §1 — finalidade

Sem achado nos acréscimos do status: autoria, transcrição e aprovação condicionada estão explícitas (`backtest.md:3`). §1 inalterado, não reaberto.

### §2 — dados e período

Sem achado: ações e units desde 2018 aparecem como decisão expressa e limitação de ligação emissor→ticker, preservando a regra própria dos FIIs (`backtest.md:16–17`; `fila.md:88`).

### §3 — elegibilidade e preços

Sem achado: fechamento anterior a D permanece referência informacional da lente; fechamento de D passa a ser explicitamente a entrada do retorno (`backtest.md:25`).

### §4 — quintis

Inalterado; não reaberto.

### §5 — retorno total

**FB-01 confere.** Provento e preço recebem o mesmo divisor `F(ex)`, produto dos fatores posteriores à ex até o fim da série (`backtest.md:37`). Isso corresponde à condição `dia < data_ex` e à divisão pelo acumulado em `sentinela/data/pit/serie_ajustada.py:97–105`.

A identidade independente é:

\[
\frac{d_{ex}/F(ex)}{P_{ex}/F(ex)}=\frac{d_{ex}}{P_{ex}}.
\]

Logo, cada reinvestimento compra a mesma fração relativa nas duas representações. O fator de quantidade de cada evento também equivale ao ajuste dos preços anteriores.

**FB-02 confere.** O intervalo está definido como fechamento de D até fechamento de T, com proventos em `(D,T]` (`backtest.md:39`). Deslistagem limita os reinvestimentos ao último pregão dentro do horizonte e mantém o CDI posterior; suspensão conserva as mesmas fronteiras (`backtest.md:40–41`). Não identifiquei mudança adicional dessas regras.

As razões são adimensionais; preços e proventos permanecem por ação, unit ou cota na mesma base. A correção não introduz desconto real, IPCA, valores contábeis totais ou mistura entre controladores e consolidado. A demonstração usada aqui é aritmética de quantidades e caixa; não depende de norma contábil.

### §6 — benchmarks

Sem achado: os instantes inicial e final agora coincidem expressamente com os do retorno dos ativos (`backtest.md:48`). A convenção diária preexistente do CDI não foi reaberta.

### §§7–9 — relatório, observações incompletas e calibração

Inalterados; não reabertos.

### §10 — exemplos independentes

Sem achado nos casos acrescentados (`backtest.md:93–95`). Os casos 10 e 11 fornecem entradas, trajetória de quantidades e resultados esperados independentes do código. O caso 12 distingue corretamente referência da lente, entrada do retorno e inclusão da ex terminal.

### §11 — impedimentos para números

Inalterado; não reaberto. Este parecer não declara resolvidas as limitações dessa seção.

### Recalculado por mim

Cálculo com frações exatas, sem importar o projeto:

| Caso | Quantidades e preços brutos | Base ajustada | Resultado |
|---|---|---|---|
| Desdobramento posterior 1:2 | `1 → 1,1 → 2,2`; final `2,2×5=11`, investimento 10 | `P_D=P_ex=5`; provento `1/2=0,5`; fator `1+0,5/5` | **10%** |
| Grupamento posterior 2:1 | `1 → 1,1 → 0,55`; final `0,55×20=11` | `P_D=P_ex=20`; provento `1/(1/2)=2`; fator `1+2/20` | **10%** |
| Fronteiras | Entrada 10; provento 2 em D excluído; em T, `1+1/12` ações a 12, total 13 | Sem eventos: mesma conta | **30%** |
| Benchmark | Nível 10 em D e 12 em T | `12/10−1` | **20%** |

Na deslistagem em L dentro do horizonte, o exemplo terminal vale `13×C/10−1`, sendo C o fator CDI de L até T. Se L=T, C=1 e o retorno é 30%. A ex em D fica excluída; a ex em L entra.

Na suspensão, mantendo preço 12 e provento 1 em T, a quantidade final continua `13/12`, com valor 13. A suspensão não autoriza incluir a ex em D.

Eventos posteriores a T também não distorcem o resultado se a base for comum: seu fator divide igualmente os preços de D e T e cancela; divide igualmente provento e preço de cada ex e cancela novamente.

### D21 e limites desta rodada

Nos trechos corrigidos, fórmula, base acionária, datas e exemplos independentes estão definidos. **Não identifiquei requisito adicional da D21 faltante em decorrência dessas alterações.** Isso não constitui nova certificação integral dos seis requisitos da ficha.

Não foram acrescentadas matrizes completas para ausência, zero, negativo, NaN ou fora de faixa, nem exemplos específicos de bancos, seguradoras, holdings, units, preferenciais, prejuízos e FIIs de papel/tijolo. Esses conteúdos preexistentes ficaram fora desta rodada; não os classifico como nova pendência ou como cobertura comprovada.

### Não verificado

- A disponibilidade histórica efetiva do FCA e a cobertura dos dados oficiais: sem rede, bancos ou coleta.
- A implementação futura do backtest, seus testes e os resultados integrados da Fase 3-b.
- A validade integral dos trechos inalterados, incluindo abstenções, sensibilidade e casos reais.
- Não executei pytest, Ruff, mutmut ou regeneração de golden; o objeto desta rodada é documental e aritmético.

### Perguntas para o Marcos

Nenhuma nova escolha metodológica nos trechos corrigidos. As decisões 41 e 42 já definem as alternativas relevantes. **FB-01 e FB-02 conferem; não há nova contestação de método nesta rodada.**

**Veredito: pode seguir — no escopo restrito desta segunda rodada FICHA.**