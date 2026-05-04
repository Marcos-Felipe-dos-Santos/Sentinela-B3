# Backtesting Sentinela-B3

## Dados Utilizados
- **Periodo:** Janeiro 2024 - Maio 2026
- **Tickers:** PETR4, ITUB4, VALE3
- **Snapshots:** 87 (mensais)
- **Fundamentos:** 15 point-in-time (coletados manualmente em 04/05/2026)

## Fonte dos Fundamentos
- Data points coletados de: https://www.fundamentus.com.br/
- Valores historicos estimados via comparacao com dados atuais
- Sem lookahead bias: fundamentos limitados a data efetiva da analise

## Resultados
- Resultados gerados em `backtesting/backtest_results_v1.csv`
- Snapshots totais: 87
- Casos avaliados: 15
- Casos ignorados: 72
- Taxa geral de acerto: 46.7%
- COMPRA acuracia: 25.0% (4 casos)
- VENDA acuracia: 16.7% (6 casos)
- NEUTRO acuracia: 100.0% (5 casos)
- Graham acuracia: 0.0% (4 casos)
- Bazin acuracia: 25.0% (4 casos)
- Gordon acuracia: 100.0% (5 casos)
- Lynch acuracia: 50.0% (2 casos)
- O backtest avalia apenas os meses com snapshot point-in-time disponivel.
- Os demais snapshots mensais permanecem ignorados para evitar reutilizar fundamentos fora do mes de referencia.

## Proximos Passos
- [ ] Expandir para 30+ data points (automatico via scraper)
- [ ] Incluir mais tickers (20+)
- [ ] Validar contra outros periodos (2020-2023)
