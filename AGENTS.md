# AGENTS.md — Sentinela B3

> Instruções para agentes de IA externos (Jules, Codex, Copilot).
> Autocontido: não assuma acesso a nenhum outro arquivo de instrução.

## Projeto

Plataforma educacional de análise de ações e FIIs da B3.
Python 3.13 + Streamlit (interface FastAPI + HTMX prevista para a Fase 7), local-first, SQLite.
**Não é consultoria financeira.**
Suíte: ~255 testes, 23 módulos em `tests/`, ~2 s.

---

## Fase atual

**Fase 0 — Preparação.** O mantenedor trabalha num branch local por fase e só
publica no fim de cada fase. Baseie seu branch sempre na `main` mais recente.

Arquivos travados enquanto esta fase estiver em andamento. Não abra PR que toque
em nenhum deles:

```
CLAUDE.md  AGENTS.md  docs/  pytest.ini  pyproject.toml  .gitignore  tests/conftest.py  .github/  app.py
```

Esta seção é atualizada pelo mantenedor a cada fase.

---

## Regra fundamental: especificação externa

**Você só escreve teste ou código quando existe uma definição de "correto" fora
deste repositório.**

Sem isso, um teste escrito a partir do código apenas descreve o que o código faz —
inclusive os bugs. Isso cimenta o erro com aparência de garantia.

**Tem spec externa — pode trabalhar:**
- `technical_engine.py` — RSI, MACD, Bollinger, ATR têm definição publicada
- `fundamentus_scraper._limpar_valor` — formato numérico brasileiro
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
- Cascata de dados: `yfinance → brapi → CVM → Fundamentus`. Preço do
  yfinance (brapi só se o yfinance falhar), fechamento D-1. O README descreve outra ordem e está errado
- Duas camadas de orquestração: `app.py` (roda) e `sentinela/services/`
  (implementada, não conectada). Não adicione a mesma feature nas duas
- Importar `config` dispara uma chamada HTTP ao Banco Central. A suíte só fica sem
  rede com a fixture de Selic do `tests/conftest.py` (criada no item F0-2)
- `cloudscraper` é importado por `fundamentus_scraper.py` e não está no
  `requirements.txt` — decisão pendente do mantenedor, não resolva sozinho
- `BRAPI_TOKEN` é lido em `brapi_provider.py:72` e, segundo o levantamento, falta no `.env.example` (o loop não lê `.env*`; não verificado)

---

## Convenções

- Conventional Commits em inglês, imperativo: `fix: normalize DY at provider boundary`
- Comentários e docstrings em português, seguindo o código existente
- Type hints em código novo
