# Sentinela B3

Plataforma educacional de análise de ações e FIIs da B3.
Python + Streamlit, local-first, SQLite.

## Comandos
- App: `streamlit run app.py`
- Testes: `python -m pytest tests/ -x --tb=short`
- Teste único: `python -m pytest tests/test_arquivo.py::test_nome -v`
- Lint: `ruff check .`
- Format: `ruff format .`

## Arquitetura
- valuation_engine.py — Graham, Bazin, Lynch, Gordon
- fii_engine.py — análise de FIIs
- market_engine.py — coleta dados (yfinance → brapi → Fundamentus)
- technical_engine.py — indicadores técnicos
- peers_engine.py — comparação setorial
- database.py — SQLite WAL, queries parametrizadas
- config.py — constantes e parâmetros econômicos
- ai_core.py — LLM (Groq → Gemini → Ollama)
- auditoria.py — sanidade runtime (NAO é suíte de testes)
- tests/ — pytest (sendo criada agora)

## Prioridades atuais
1. Criar tests/ com testes econômicos sintéticos
2. Fix gate Bazin: dy >= 0.05 (atual: dy > 0)
3. Fix FII benchmark: Selic * 0.85 (atual: Selic bruta)
4. Mediana em vez de média para fair_value
5. Sincronizar README com código
6. MacroContext centralizando parâmetros econômicos

## Regras econômicas
- Selic via BCB SGS série 432, cache 24h, fallback hardcoded
- DY > 1 = Yahoo retornou %, dividir por 100; DY > 0.25 = suspeito
- Bazin = pagadoras consistentes (DY >= 5%), NAO qualquer dy > 0
- FII: DY isento de IR → comparar com Selic * 0.85, NAO Selic bruta
- Graham/Bazin divergindo >2x → média sem sentido econômico, usar mediana
- Todo output é educacional — NUNCA recomendação de compra/venda

## Segurança
- SQL sempre parametrizado com ? — nunca f-strings em queries
- Nunca ler .env
- Nunca git push sem aprovação explícita

## Bugs conhecidos (nao corrija sem teste baseline primeiro)
- Bazin dispara com dy > 0 → deve ser dy >= 0.05
- FII usa Selic bruta → deve usar Selic * 0.85
- Fair value = média → deve ser mediana
- README documenta fórmulas diferentes do código
- auditoria.py tem 936 linhas (god module)

## Git
- Conventional commits: feat/fix/test/docs/refactor/chore
- Testes devem passar antes de qualquer commit
- Nunca commitar .env, __pycache__, *.db, outputs/

