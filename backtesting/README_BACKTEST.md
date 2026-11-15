# Backtest do Sentinela B3

## Backtest ponto-no-tempo (Fase 3)

- Código: `backtesting/backtest_pit.py` (`BacktestPIT.executar`), API nova e separada.
- Regras: `docs/metodologia/backtest.md` (ficha aprovada pelas decisões 41 e 42).
- Em cada data D, só o que foi publicado antes do dia de D chega às lentes, pelo
  `AnalysisService.analisar(ticker, as_of=D)` com o motor histórico. As lentes são
  ordenadas em quintis por distância ao preço; o retorno total vai do fechamento de D
  ao de T, com proventos brutos reinvestidos e eventos em ações na mesma base.
- O relatório descreve cada quintil e a diferença Q1 − Q5, sempre com a contagem de
  observações. Não há score agregado nem regra de seleção de ativos.
- **Metodologia ainda não validada:** não há resultado do backtest PIT que sirva de
  evidência (ficha §11, "O que ainda impede números").
- Limitações abertas: `docs/loop/pendencias.md` (ficha §11; FII, units e classes 5/6
  ainda sem retorno).

## Caminho legado

- `backtesting/backtest_engine.py` (`BacktestEngine.simular_analise_mensal`) devolve
  `INDISPONIVEL` no caminho de análise elegível desde a Fase 2C. Fica como está.

## Arquivos removidos (F3-8c)

- `fundamentos_point_in_time.csv`: 15 linhas retro-estimadas de dados atuais
  (auditoria de 9/9/2026, F-1). Não eram evidência.
- `backtest_results_v1.csv`: gerado por versão anterior do motor, com texto que não
  existe mais no código (F-29). Não era reprodutível.
- Os dois continuam recuperáveis pelo histórico do git.
