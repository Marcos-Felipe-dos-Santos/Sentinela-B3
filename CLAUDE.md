

\# Contexto do Projeto

Estou trabalhando no repositório Sentinela-B3, uma plataforma de análise fundamentalista para ações e FIIs da B3. Stack: Python 3.10+, Streamlit, SQLite, yfinance, Fundamentus scraper, integração com Groq/Gemini/Ollama. Objetivo: uso pessoal + showcase de portfólio no GitHub para atrair atenção de recrutadores da área de dados/fintech.



\## Arquivos atuais (todos na raiz):

app.py, config.py, database.py, market\_engine.py, valuation\_engine.py, fii\_engine.py, technical\_engine.py, portfolio\_engine.py, peers\_engine.py, ai\_core.py, fundamentus\_scraper.py, auditoria.py, limpar\_banco.py, requirements.txt



\## Tarefas — executar nesta ordem:



\### TAREFA 1 — Reestruturar diretórios

Reorganizar para a seguinte estrutura de pacote Python sem quebrar os imports:

&#x20; sentinela/

&#x20;   \_\_init\_\_.py

&#x20;   config.py

&#x20;   database.py

&#x20;   engines/

&#x20;     \_\_init\_\_.py

&#x20;     market.py       (era market\_engine.py)

&#x20;     valuation.py    (era valuation\_engine.py)

&#x20;     fii.py          (era fii\_engine.py)

&#x20;     technical.py    (era technical\_engine.py)

&#x20;     portfolio.py    (era portfolio\_engine.py)

&#x20;     peers.py        (era peers\_engine.py)

&#x20;   ai/

&#x20;     \_\_init\_\_.py

&#x20;     core.py         (era ai\_core.py)

&#x20;   scrapers/

&#x20;     \_\_init\_\_.py

&#x20;     fundamentus.py  (era fundamentus\_scraper.py)

&#x20;   utils/

&#x20;     \_\_init\_\_.py

&#x20;     audit.py        (era auditoria.py)

&#x20;     db\_cleaner.py   (era limpar\_banco.py)

&#x20; tests/

&#x20;   \_\_init\_\_.py

&#x20;   test\_valuation.py

&#x20;   test\_fii.py

&#x20;   test\_market.py

&#x20; docs/

&#x20;   screenshot-terminal.png   (placeholder vazio)

&#x20; app.py                      (permanece na raiz, atualizar imports)

&#x20; pyproject.toml              (novo)

&#x20; .env.example                (renomear de "Env Exanple.txt")

&#x20; .github/

&#x20;   workflows/

&#x20;     ci.yml



\### TAREFA 2 — Adicionar type hints

Em todos os métodos públicos dos engines, adicionar type hints completos. Exemplo:

&#x20; def processar(self, dados: dict\[str, Any]) -> dict\[str, Any] | None:



\### TAREFA 3 — Adicionar docstrings Google-style

Em todas as classes e métodos públicos. Exemplo:

&#x20; """Calcula o Fair Value via fórmula de Graham.

&#x20; Args:

&#x20;     lpa: Lucro por ação.

&#x20;     vpa: Valor patrimonial por ação.

&#x20; Returns:

&#x20;     Fair value calculado ou None se dados inválidos.

&#x20; """



\### TAREFA 4 — Criar testes pytest básicos

Criar tests/test\_valuation.py com testes para:

\- graham\_formula(lpa=2.5, vpa=10) retorna valor positivo

\- bazin\_formula com DY=0 retorna None

\- score\_final está entre 0 e 100

\- detecção de FII: "HGLG11" é FII, "WEGE3" não é



Criar tests/test\_fii.py com testes para:

\- analisar() com dados válidos retorna dict com 'fair\_value'

\- analisar() com DY=0 retorna score <= 30



Usar pytest + unittest.mock para mockar yfinance.



\### TAREFA 5 — Criar GitHub Actions CI

Criar .github/workflows/ci.yml que:

\- Roda em push e pull\_request na branch main

\- Python 3.11

\- Instala dependências do pyproject.toml

\- Roda flake8 (max-line-length=100)

\- Roda pytest com cobertura mínima de 40%



\### TAREFA 6 — Adicionar cloudscraper e tenacity

No sentinela/scrapers/fundamentus.py:

\- Substituir requests por cloudscraper para contornar proteção anti-bot

\- Adicionar @retry(stop=stop\_after\_attempt(3), wait=wait\_exponential()) em buscar\_dados()



No sentinela/engines/market.py e sentinela/ai/core.py:

\- Adicionar @retry do tenacity nas chamadas externas



\### TAREFA 7 — Substituir logging por loguru

\- Remover todos os print() de debug dos engines

\- Adicionar from loguru import logger

\- Usar logger.info(), logger.warning(), logger.error()

\- Configurar RotatingFileHandler para sentinela.log



\### TAREFA 8 — Criar pyproject.toml

Criar pyproject.toml com:

\- name = "sentinela-b3"

\- version = "1.0.0"  (unificar versão)

\- Python >= 3.10

\- Todas as dependências do requirements.txt

\- \[tool.pytest] com testpaths = \["tests"]

\- \[tool.flake8] max-line-length = 100



\### TAREFA 9 — Corrigir inconsistências

\- Renomear "Env Exanple.txt" para ".env.example"

\- Atualizar versão em app.py para 1.0.0

\- Criar docs/ com um README.md placeholder

\- Atualizar todos os imports em app.py para nova estrutura de pacote



\## Restrições importantes:

\- NÃO quebrar a lógica de negócio existente (valuation, FII detection, Markowitz)

\- NÃO alterar o fluxo do Streamlit em app.py além de imports e versão

\- NÃO adicionar dependências pagas ou APIs que precisem de conta premium

\- Manter SQLite como banco (não migrar para Postgres)

\- Manter compatibilidade com Python 3.10+



