# ADR 0002 — Execução por loop, tempo como entrada e dados oficiais primeiro

**Status:** D1 a D15 aceitas (D5–D13 no checkpoint da Fase 0, em 2026-10-02: `docs/decisoes/checkpoint-fase0.md`)
**Data:** 2026-09-22
**Relação:** complementa o ADR-0001. Os princípios e contratos do 0001 continuam valendo; a ordem das fases passa a ser a do `docs/PLANO.md`.

---

## Contexto

Cinco coisas mudaram desde o ADR-0001:

1. A execução passou para um loop autônomo do Claude Code (`/goal` + modo auto), com commits locais e sem push por PR.
2. O mutmut 3 exige fork, então no Windows só roda dentro do WSL, e trocou a interface de linha de comando. O plano de setembro usava a sintaxe do mutmut 2.
3. A Selic entrou em ciclo de corte (14,25% em junho, 13,75% em 16/09/2026). Isso aumenta o custo do colapso metodológico: métodos que dividem DY pela taxa pendem para "sinal positivo" a cada corte.
4. A revisão do mapa V2.1 encontrou premissas a corrigir: "tempo real" com dado D-1, histórico gravado só para frente, vocabulário de "recomendação" em conflito com o `CLAUDE.md` e isolamento que cobria notícias mas não sinais técnicos.
5. Uma análise financeira do projeto mostrou que o plano cobria bem a engenharia, mas não o núcleo financeiro. Entre os pontos: a taxa de desconto é a Selic nominal; bancos não têm regra própria; só o último ano de dados é usado; a cobertura depende de mapas manuais (cerca de 50 ações e 30 FIIs); ETFs e BDRs são mal classificados; e o Markowitz devolve uma "Alocação Sugerida" estimada com um ano de dados.

---

## Decisões aceitas

**D1 — Modelo operacional.** Um branch por fase (`v2/fase-N`), um commit por item, diário em `docs/loop/`. O loop nunca faz push; há deny para isso no `.claude/settings.json`. No checkpoint `[DECISÃO]`, o mantenedor revisa e faz o push da fase, com PR opcional. É nesse momento que o CI roda e o Jules revisa.

**D2 — Ambiente.** WSL2 (Ubuntu), repositório no sistema de arquivos do Linux, Python 3.13 via uv (`venv` criada com `--seed`), Claude Code instalado no WSL, loop dentro do tmux e `instanceIdleTimeout=-1` no `.wslconfig`. CI também em Python 3.13.

**D3 — Mutação com mutmut 3.** Configuração em `[tool.mutmut]` no `pyproject.toml`; `mutants/` no `.gitignore`; `xfail_strict` desligado só nas rodadas de mutação, senão um XPASS acidental conta como mutante morto. Limite conhecido: só código dentro de funções é mutado.

**D4 — Dossiê antes da metodologia.** Na Fase 0, o loop prepara os números de que as decisões da Fase 2 dependem: E-1, matriz Selic e Gordon real × nominal.

**D14 — Limpeza como parte da fase.** Resíduo não é tarefa de fim de projeto. As regras:
- A Fase 0 faz um inventário classificado (`vulture`, `deptry`, `ruff`, módulos órfãos, arquivos rastreados indevidamente, documentos e branches).
- Toda fase termina com um item que remove o que ela tornou obsoleto.
- O CI relata resíduo novo a partir da Fase 1 e bloqueia a partir da Fase 6.
- O loop só remove o que o git pode devolver: arquivo rastreado, via `git rm`. Arquivo não rastreado, branch e item de uso incerto ficam para o mantenedor.
- Fases encerradas são arquivadas em `docs/loop/historico/`, não apagadas.

**D15 — Núcleo financeiro antes de qualquer feature.** O resultado precisa estar certo antes de ganhar interface, notícias ou alertas. As regras:
- **Dados de referência primeiro.** Mapa ticker ↔ CNPJ automático e classe do ativo por dado oficial, nunca pelo sufixo do ticker. Sem isso, a CVM só alcança os tickers dos mapas manuais — e o E-1 e os dados de bancos dependem dela.
- **Taxa de desconto real.** NTN-B longa + prêmio, com k e g no mesmo regime; a Selic deixa de ser taxa de desconto. Prêmio e vértice são decididos com o dossiê.
- **Bancos com lente própria.** P/VP justificado pelo ROE e pelo custo de capital, com Basileia e inadimplência como qualidade — não só abstenção.
- **Cinco anos e qualidade.** Cada método declara sua janela (último ano, TTM ou cinco anos), e uma lente de qualidade entra na classificação.
- **Alavancagem por dívida financeira líquida**, no lugar do endividamento contábil total.
- **Carteira sem sugestão.** O otimizador de Markowitz sai; no lugar, uma camada de risco que descreve concentração, volatilidade, correlação e sensibilidade a juros, sem alocação sugerida.
- **Quarentena imediata da V1.** Na Fase 0: aviso de revisão metodológica, "Alocação Sugerida" fora da tela e backtest marcado como baseado em fundamentos sintéticos.
- **Privacidade.** O repositório é público: dados da carteira do usuário nunca entram em arquivo versionado; análises que a usam ficam em `outputs/`.

---

## Decisões propostas

**D5 — Tempo como entrada.** `as_of` faz parte do `MethodInputs` desde a Fase 1. A macro vem da série do SGS na data; os fundamentos são os entregues até a data; o histórico é reconstruído para trás; o backtest passa a ser ponto-no-tempo real. Cuidados obrigatórios:
- reapresentações: guardar versões;
- viés de sobrevivência: universo com datas de listagem;
- preço bruto na data para múltiplos, série ajustada para retornos;
- eventos societários entre a demonstração e o preço.

**D6 — Cadência diária.** "Contínuo" vira fechamento diário: um job por dia, sem daemon, agendado pelo Agendador do Windows via `wsl.exe`, com digest e histerese. O dado já é D-1; "tempo real" seria ilusão.

**D7 — Dados oficiais primeiro.** Quantidade de ações vinda da seção Composição do Capital da DFP/ITR, o que resolve o E-1. COTAHIST da B3 para preço bruto e liquidez. yfinance para a série ajustada. Fundamentus conforme o F0-4.

**D8 — Notícias medidas antes de crescer.** Um estudo de evento sobre os fatos relevantes do IPE (CVM) decide os estágios 2–4.

**D9 — Rastreabilidade como produto.** Relatório estático por ativo com a proveniência de cada número: v0 na Fase 1, completo na Fase 4. Os templates viram as telas da interface.

**D10 — Vocabulário único.** "Classificação" e "sinal" em código, banco e telas; "histórico de recomendações" vira "histórico de classificações". Resolve o conflito entre o mapa V2.1 e a regra do `CLAUDE.md`.

**D11 — Métodos puros.** `sentinela/methods/` não importa notícias, análise técnica nem provedores, e não faz rede, banco ou leitura de relógio. Contrato de import no CI. Amplia o isolamento do ADR-0001, que só cobria notícias.

**D12 — Linha de corte.** Núcleo de portfólio = Fases 0–6, até a vitrine. Interface FastAPI e IA nas telas vêm depois.

**D13 — Nova ordem de fases.** A do `docs/PLANO.md`: a interface sai da Fase 4 e vai para a 7; operação diária, estudo de evento e vitrine entram antes.

---

## Alternativas consideradas

- **Mutação manual, com o loop no Windows nativo.** Exigiria o WSL do mesmo jeito e deixaria o loop commitar testes sem verificação. Rejeitada.
- **Zero push.** Deixa o CI sem rodar, o Jules sem base e a fase sem backup. Rejeitada; push por fase.
- **Gravar histórico só daqui para frente (E-14 puro).** A feature nasceria vazia e o backtest continuaria fabricado. Preterida por D5.
- **Monitoramento contínuo com agendador dentro do processo.** Complexidade de daemon para um dado que muda uma vez por dia. Preterido por D6.
- **Só abstenção para bancos.** Deixaria sem análise um setor central da bolsa e das carteiras de varejo. Rejeitada; lente própria (D15).
- **Manter o Markowitz sem evolução.** Continuaria exibindo sugestão de alocação com retorno esperado sem significância estatística. Rejeitada; camada de risco (D15).

---

## Consequências

**Positivas.** As Fases 0 e 1 ficam baratas com o loop. E-6, E-14, backtest e histórico viram um conceito só. O E-1 se resolve com dado oficial. O projeto ganha entregas visíveis antes da interface.

**Negativas.** A Fase 3 é a maior do plano. Ponto-no-tempo perfeito é impossível para o passado, por causa das reapresentações antigas. O ambiente muda para WSL, o que exige disciplina para manter uma única cópia do repositório.
