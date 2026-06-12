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

## Bugs conhecidos (não corrija sem teste baseline primeiro)
- Bazin dispara com dy > 0 — deve ser dy >= 0.05
- FII usa Selic bruta — deve usar Selic * 0.85
- Fair value = média — deve ser mediana
