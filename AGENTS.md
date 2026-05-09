# AGENTS.md — Sentinela B3

## Objetivo do projeto

Sentinela B3 é uma aplicação educacional e de portfólio em Python/Streamlit para análise de ações e FIIs da B3.

O projeto NÃO é consultoria financeira, NÃO é recomendador profissional de investimento e NÃO deve usar linguagem de decisão direta como “comprar”, “vender” ou “forte compra” como orientação ao usuário.

Prefira sempre:
- classificação heurística;
- sinal positivo;
- sinal de atenção;
- ativo com indicadores favoráveis;
- ativo com inconsistências;
- dados insuficientes;
- necessita análise adicional.

## Stack principal

- Python 3.11+
- Streamlit
- Pandas / NumPy
- SQLite
- Plotly
- yfinance
- Brapi, quando `BRAPI_TOKEN` estiver configurado
- Fundamentus como fallback/complemento
- pytest
- Groq / Gemini / Ollama para explicação textual, quando configurado

## Estrutura atual

Arquivos principais na raiz:

- `app.py`: interface Streamlit.
- `market_engine.py`: preço, histórico, fundamentos, cache e fontes externas.
- `valuation_engine.py`: análise de ações.
- `fii_engine.py`: análise de FIIs.
- `technical_engine.py`: indicadores técnicos.
- `portfolio_engine.py`: carteira e otimização.
- `peers_engine.py`: comparação com pares.
- `database.py`: persistência SQLite.
- `ai_core.py`: camada de IA.
- `auditar_recomendacoes.py`: auditoria operacional.
- `auditoria.py`: diagnóstico legado/profundo.
- `limpar_banco.py`: utilitário manual de limpeza.
- `sentinela/services/asset_classifier.py`: classificação central de ações, FIIs e Units.
- `tests/`: testes automatizados.
- `docs/`: documentação técnica.

## Regras obrigatórias

1. Antes de alterar código, inspecione os arquivos relacionados.
2. Não invente nomes de funções, classes, engines, tabelas, colunas ou fórmulas.
3. Não mude fórmulas financeiras sem tarefa explícita de validação financeira.
4. Não altere thresholds, pesos ou scores sem teste e justificativa.
5. Não trate dados ausentes como zero silenciosamente.
6. Não misture regras de ações e FIIs.
7. Não reintroduza lógica duplicada para identificar FII/Unit. Use `AssetClassifier` quando aplicável.
8. Preserve compatibilidade com Windows.
9. Não adicione dependência nova sem justificar necessidade e impacto.
10. Não salve API keys, tokens, banco local, logs, caches ou arquivos gerados no Git.
11. Não faça refatoração ampla quando a tarefa pedir correção pequena.
12. Se encontrar problema fora do escopo, registre no relatório final, mas não corrija sem autorização.

## Regras financeiras

Para ações, valide separadamente quando aplicável:
- P/L;
- P/VP;
- ROE;
- margem líquida;
- dívida líquida / EBITDA;
- dividend yield;
- crescimento;
- valuation por múltiplos;
- margem de segurança;
- qualidade dos dados.

Para FIIs, valide separadamente quando aplicável:
- dividend yield;
- P/VP;
- vacância;
- liquidez;
- tipo de FII;
- recorrência dos rendimentos;
- concentração;
- risco de gestão;
- risco de emissão;
- dados manuais ou cacheados.

Qualquer saída deve deixar claro quando for:
- heurística;
- simplificada;
- dependente de dados externos;
- incompleta;
- experimental.

## Comandos de validação

Para mudanças de código Python:

```bash
python -m pytest -q
python -m py_compile app.py market_engine.py valuation_engine.py fii_engine.py technical_engine.py portfolio_engine.py peers_engine.py database.py ai_core.py
```

## Definition of Done

Uma tarefa só está concluída quando:

1. O escopo solicitado foi respeitado.
2. Os arquivos alterados foram listados.
3. Os testes relevantes foram executados ou a impossibilidade foi explicada.
4. A lógica financeira não foi alterada sem autorização.
5. A linguagem de recomendação direta foi evitada.
6. O diff foi revisado.
7. Riscos remanescentes foram reportados.

## Saída final obrigatória

Ao finalizar qualquer tarefa, responda com:

1. Resumo do que foi feito.
2. Arquivos alterados.
3. Arquivos inspecionados.
4. Testes executados.
5. Resultado dos testes.
6. Riscos remanescentes.
7. Pontos que precisam de revisão humana.
8. Próximos passos recomendados.