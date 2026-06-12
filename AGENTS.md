# AGENTS.md — Sentinela B3

> Instruções para agentes de IA genéricos (GitHub Copilot, Codex, etc).
> Para Claude Code CLI, a fonte primária é CLAUDE.md.

## Projeto
Plataforma educacional de análise de ações e FIIs da B3.
Python + Streamlit, local-first, SQLite. NÃO é consultoria financeira.

## Regras obrigatórias
- Nunca gerar recomendação de compra/venda
- Usar linguagem: "classificação heurística", "sinal positivo", "apoio ao estudo"
- SQL sempre parametrizado com ? — nunca f-strings em queries
- Nunca ler ou modificar .env, tokens ou credenciais
- Nunca fazer git push sem aprovação explícita
- Não remover testes para fazer passar

## Comandos
- App: streamlit run app.py
- Testes: python -m pytest tests/ -x --tb=short
- Lint: ruff check .

## Bugs corrigidos (branch refactor/economic-fixes)
- Gate Bazin dy >= 5% (era dy > 0)
- FII compara com Selic líquida ×0.85 (era bruta)
- Fair value usa mediana (era média)
