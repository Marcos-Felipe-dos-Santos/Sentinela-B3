# AGENTS.md — Sentinela B3

> Instruções para agentes de IA externos (Jules, Codex, Copilot).
> Autocontido: não assuma acesso a nenhum outro arquivo de instrução.

## Projeto

Plataforma educacional de análise de ações e FIIs da B3.
Python 3.13 + Streamlit (interface FastAPI + HTMX prevista para a Fase 7), local-first, SQLite.
**Não é consultoria financeira.**
Suíte em 25/10/2026: 2.575 passed, 1 skipped, 14 xfailed (~10 s).

---

## Fase atual

**Entre fases: a 2B (Taxa real, bancos e escopo) foi concluída** (tag `v2-fase-2b`;
histórico em `docs/loop/historico/fase-2b/`). A **Fase 2C (Qualidade e apresentação)**
está em proposta, em `docs/loop/fila-fase2c-proposta.md`, aguardando auditoria e
aprovação. O mantenedor trabalha num branch local por fase e só publica no fim de cada
fase. Baseie seu branch sempre na `main` mais recente.

Até a 2C ser ativada, nenhum arquivo está travado por fase. Ainda assim, PR que toque
`sentinela/methods/`, `sentinela/data/`, os motores (`valuation_engine.py`,
`fii_engine.py`, `market_engine.py`), `config.py` ou `tests/fixtures/` precisa de
aprovação do mantenedor antes de abrir. A lista de arquivos travados da 2C entra aqui
na ativação.

## Regra fundamental: especificação externa

**Você só escreve teste ou código quando existe uma definição de "correto" fora
deste repositório.**

Sem isso, um teste escrito a partir do código apenas descreve o que o código faz —
inclusive os bugs. Isso cimenta o erro com aparência de garantia.

**Tem spec externa — pode trabalhar:**
- `technical_engine.py` — RSI, MACD, Bollinger, ATR têm definição publicada
- `database.adicionar_posicao` — média ponderada é aritmética
- `cvm_provider.py` — o layout dos arquivos da CVM é documentado pela CVM
- Invariantes de unidade: DY em `[0, 0.30]`, score em `[0, 100]`, fair value e
  preço na mesma escala
- Regressão para qualquer correção que você mesmo fizer

**Não tem spec externa — pare e reporte:**
- Qualquer coisa sobre qual método de valuation está certo
- O que preservar e o que deve mudar num refactor de metodologia

Na dúvida sobre qual caso é o seu: **pare e pergunte.** Uma tarefa devolvida com
pergunta é barata; um bug cimentado em teste custa meses.

---

## Arquivos proibidos

Contêm decisões metodológicas em revisão. Uma mudança que passa nos testes pode
dobrar todos os valores calculados pelo sistema.

```
valuation_engine.py
fii_engine.py
portfolio_engine.py
config.py  (seções MacroContext e _normalizar_dy)
sentinela/methods/**
sentinela/api/**        sentinela/web/**
backtesting/fundamentos_point_in_time.csv
backtesting/backtest_results_v1.csv
tests/test_financeiro_pre_refactor.py
tests/test_equivalencia_motores.py  tests/golden_motores.py
tests/fixtures/golden_motores.jsonl
docs/loop/**
```

Se a tarefa parecer exigir mudança em algum deles: **pare e reporte.**
Editar outro arquivo para obter o mesmo efeito conta como violação.

---

## Regras obrigatórias

- Nunca gerar recomendação de compra ou venda de ativo, nem sugestão de alocação de carteira.
  Vocabulário: "classificação", "sinal positivo", "classificação heurística", "apoio ao estudo"
- **O repositório é público.** Nunca coloque em arquivo versionado dados da carteira do
  mantenedor (posições, pesos, lista de ativos) — nem em testes ou fixtures. Use tickers genéricos
- SQL sempre parametrizado com `?` — nunca f-strings em queries
- Nunca ler, modificar ou commitar `.env`, tokens ou credenciais
- Nunca `git push` sem aprovação explícita
- **Não remover, pular (`skip`) ou enfraquecer testes para a suíte passar**
- Uma tarefa = um PR = um assunto. Não agregue correções não pedidas
- Não reformate arquivos que a tarefa não pede para mudar
- Não delete arquivos que o ticket não lista. Resíduo que você encontrar vira
  comentário no PR, não remoção
- Não deixe resíduo: código comentado, import sem uso, print de depuração,
  arquivo temporário
- Nenhuma dependência nova sem pedido explícito no ticket
- Código de cálculo não ganha rede, banco nem leitura de relógio

---

## Bugs e regressão

Decisão do mantenedor de 15/10/2026. Registro e detalhe em `tests/regressao/README.md`.

1. Bug confirmado (auditoria, revisão ou uso) vira teste em `tests/regressao/` no mesmo dia,
   antes de qualquer correção
2. Bug ainda não corrigido fica xfail estrito com ID e item que corrige; o `xfail_strict` do
   `pytest.ini` faz o CI quebrar se ele passar sem a marca ser retirada
3. A correção retira a marca, o teste fica para sempre e o registro muda para "corrigido"
4. Nenhum item `fix:` fecha sem o teste de regressão do bug que corrige

---

## Comandos

```bash
python -m pytest tests/ -x --tb=short
python -m mutmut run "<modulo>*"        # mutmut 3; configuração em [tool.mutmut] do pyproject.toml
python -m mutmut export-cicd-stats      # mortos e sobreviventes, para o mutation score
ruff check .
```

---

## Critério de aceite

Toda tarefa traz critério explícito no ticket. Sem ele, **não comece** — peça.

1. O teste nomeado no ticket passa
2. A suíte inteira continua verde
3. `ruff check .` sem erros novos
4. O diff toca apenas os arquivos previstos
5. **Para tarefas de teste: mutation score ≥ 80% no módulo alvo, medido com o mutmut 3**

**Suíte verde não é suficiente.** `app.py`, `auditoria.py` e `limpar_banco.py`
têm 0% de cobertura. Se sua mudança toca código sem cobertura, escreva o teste —
e confirme que ele falha quando você quebra o código de propósito.

**Se um ticket diz que espera um teste vermelho, entregue-o vermelho.** Alguns
tickets pedem teste escrito a partir da especificação contra código que pode estar
errado. Um teste verde nesse caso significa que você descreveu o código em vez de
verificá-lo. Reporte a divergência; não a "conserte".

---

## Contexto que evita retrabalho

- Os IDs de achado (E-*, F-*) citados nos tickets vêm de `docs/auditoria/2026-09-red-team.md`
- Cascata de dados: `índice oficial → yfinance → brapi → CVM`, depois IF.data (bancos), Informe
  Mensal/rendimento do FII, proventos B3, liquidez (COTAHIST), taxa real e cache. O Fundamentus saiu. Preço do yfinance (brapi só se
  o yfinance falhar), fechamento D-1. O README descreve outra ordem e está errado
- Gordon usa DVA dos controladores e taxa/crescimento reais (Fisher, teto PIB); a taxa real
  vem de NTN-B/Principal ≥ 2035, pesos iguais, mais 5 pp das ações, sem contingência numérica.
  Bazin usa proventos brutos B3 de 12 meses e critério nominal fixo de 6%, DY mínimo de 5%.
  FII de tijolo elegível usa rendimento do Informe ÷ (NTN-B real + spread versionado); Selic fica no score/contexto.
- Escopo pelo modelo do BPP consolidado (F2B-4): empresa recebe os métodos de ação; banco, só a
  lente de bancos (F2B-32; Basileia e inadimplência do IF.data só como contexto); seguradora e
  sem BPP se abstêm sem número. FII (ficha 1.3) e bancos abstidos não trazem valor nem upside.
- Liquidez: 63 pregões, presença ≥ 80%, volume mediano diário ≥ R$ 500 mil (ações/units)
  ou R$ 100 mil (FII). Incompletude/falha de coleta produz aviso, sem tratar ausência como zero.
- Duas camadas de orquestração: `app.py` (roda) e `sentinela/services/`
  (implementada, não conectada). Não adicione a mesma feature nas duas
- Importar `config` dispara uma chamada HTTP ao Banco Central. A suíte só fica sem
  rede com a fixture de Selic do `tests/conftest.py` (criada no item F0-2)
- `BRAPI_TOKEN` é lido em `brapi_provider.py:64` e, segundo o levantamento, falta no `.env.example` (o loop não lê `.env*`; não verificado)

---

## Convenções

- Conventional Commits em inglês, imperativo: `fix: normalize DY at provider boundary`
- Comentários e docstrings em português, seguindo o código existente
- Type hints em código novo

<!-- multiagente 14/10/2026 -->
## Multiagente (Claude Code, Codex, Antigravity)

- A fila (`docs/loop/fila.md`) é a única lista de trabalho. Um executor por item, nunca dois ao mesmo tempo.
- Procedimentos compartilhados em `.agents/skills/<nome>/SKILL.md`: `retomar`, `passagem`, `verificar-entrega` e `executar-fila`. Agente que não carrega skills sozinho lê o arquivo quando o pedido citar o nome.
- Ao abrir uma sessão de trabalho já começado, rode `retomar` antes de editar qualquer arquivo.
- A memória do `ai-memory` é pista, não autoridade: fila, diário, ADRs e o git prevalecem.
- Quem executou cada item fica no diário (`**Executor:**`) e no corpo do commit (`Executor: <ferramenta>`).
- Auditoria externa sempre por família de modelo diferente da do executor (ADR-0003, D30, revisão de 14/10/2026).
- Workflow completo: `docs/loop/workflow-multiagente.md`.
- Ordem das etapas de uma fase e comandos de auditoria: `docs/loop/ciclo-de-fase.md`.
