# Sentinela B3

Plataforma educacional e local para estudar ações e FIIs da B3 com dados oficiais. **Não é recomendação de investimento.**

**Status: V2 em desenvolvimento ativo — Fase 3 de 8 concluída na branch de desenvolvimento, em revisão antes do merge.** A interface disponível hoje usa Streamlit; a interface FastAPI + HTMX está planejada para a Fase 7.

## Da V1 para a V2

A V1 reuniu coleta de dados, análise de ativos, indicadores, gráficos e armazenamento local numa aplicação Streamlit. Ela tornou o projeto utilizável e deu uma base para medir a evolução. A V2 preserva esse uso local enquanto refaz a origem dos dados, os contratos dos métodos e a forma de apresentar resultados.

As lentes agora aparecem **separadas**: cada uma mostra seu valor e premissas, ou um motivo explícito para se abster. Não há score nem valor único agregado. A V2 usa documentos e séries da **CVM, B3, BCB, IBGE e Tesouro**; registra a versão e a data em que a informação estava disponível; e permite estudar uma data passada pelo caminho ponto no tempo. Regressões, um golden de comportamento e testes de mutação ajudam a detectar mudanças acidentais. A [metodologia](docs/metodologia/README.md) registra o que cada lente calcula e onde se abstém.

## O que a V2 já entregou

| Fase | Entrega verificada | Registro |
|---|---|---|
| **1 · Fundação** | Tipos de unidade, contrato e registro dos métodos; fórmulas extraídas dos motores da V1. O golden de extração comparou **2.247 casos**. | [Resumo da Fase 1](docs/loop/historico/fase-1/pr-fase-1.md) |
| **2A · Dados corretos** | Referência oficial de ticker, emissor e classe; demonstrações CVM, números por ação, série de **cinco exercícios** e TTM, proveniência e liquidez pelo COTAHIST. | [Resumo da Fase 2A](docs/loop/historico/fase-2a/pr-fase-2a.md) |
| **2B · Taxa e escopo** | Taxa real, lentes de Gordon, Bazin, FII e bancos com insumos documentados; regras de escopo pelo modelo das demonstrações e liquidez mínima. | [Resumo da Fase 2B](docs/loop/historico/fase-2b/pr-fase-2b.md) |
| **2C · Qualidade e apresentação** | Graham e Lynch revistos; lentes independentes com abstenção e distância ao preço; quadro descritivo de qualidade de **cinco exercícios**, sem nota única. | [Resumo da Fase 2C](docs/loop/historico/fase-2c/pr-fase-2c.md) |
| **3 · Tempo como entrada** | A data vira entrada: `analisar(ticker, as_of)` numa data passada lê só o banco único, com DFP, FCA, Informe de FII, COTAHIST, proventos da B3 e séries macro carregados ponto no tempo; a disponibilidade é a data de publicação. Universo histórico com deslistadas e backtest ponto no tempo com retorno total, relatório por lente, data e motivo de abstenção, e banda neutra só como proposta. A sonda final, refeita no checkpoint em oito datas de 2018 a 2025, mediu a cobertura por lente, ano e horizonte: Gordon com valor em até 44 ações por data, Bazin em até 20, Graham só em 2025 (43), Lynch em 1 ação só em 2025, Bancos em até 3 bancos por data só de 2023 a 2025, e a lente do FII sem número em nenhuma data (o complemento da B3 do fundo é fonte só corrente e fica desligado no histórico, então a continuidade dos eventos de cota não se demonstra), com o retorno total do FII também sem ligação. Contra a sonda anterior, nenhum retorno perdido e 1.085 recuperados nos três horizontes (440 em 12 meses, 355 em 24 e 290 em 36). Limitações declaradas, com destino na Fase 4: no Informe de FII, arquivo vigente vazio ou malformado deixa recuar ao ano anterior; na CVM, período cuja versão vigente em D está no índice sem números nos arquivos abertos (reapresentada depois de D ou retida por conflito de carga) recua em silêncio ao período anterior, e a versão ainda é a maior entregue antes de D, não a última entrega; e a lente do FII sem prova de ponta a ponta. | [Resumo da Fase 3](docs/loop/historico/fase-3/pr-fase-3.md) |

Na branch de desenvolvimento, o gate do checkpoint de **20/11/2026** registrou **5.210 testes passando, 1 ignorado e 24 falhas esperadas estritas**, todas limitações declaradas da Fase 3. Esse número descreve a branch naquele ponto, não a `main` publicada. Bugs confirmados e seus destinos ficam no [registro de regressões](tests/regressao/README.md).

## Próximos passos

| Fase | Direção prevista |
|---|---|
| **4** | Primeiro, as limitações herdadas da Fase 3; depois, operação diária por CLI, fechamento, rastreabilidade, backup e descrição de risco da carteira, sem alocação sugerida. A fila está em [proposta](docs/loop/fila-fase4-proposta.md), sem efeito até a aprovação. |
| **5** | Fatos relevantes e estudo de evento para medir se notícias acrescentam informação. |
| **6** | Vitrine técnica: documentação consolidada, página de metodologia e limpeza do núcleo. |
| **7** | Interface FastAPI + HTMX com paridade funcional com a V1. |
| **8** | IA nas telas para explicar premissas e limitações; expansão de notícias condicionada ao estudo da Fase 5. |

O [plano da V2](docs/PLANO.md) descreve dependências e critérios. A fila ativa define a execução; as fases futuras ainda não são entregas.

## Instalar e rodar localmente

Requer **Python 3.13**. No Linux ou WSL2:

```bash
git clone https://github.com/Marcos-Felipe-dos-Santos/Sentinela-B3.git
cd Sentinela-B3
python3.13 -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
streamlit run app.py
```

A interface local abre em `http://localhost:8501`. O arquivo [`.env.example`](.env.example) documenta integrações opcionais; configure apenas as que usar e mantenha credenciais fora do Git. A aplicação depende da disponibilidade das fontes para coletar dados novos. A interface usa Streamlit enquanto a migração da Fase 7 não acontece.

## Desenvolvimento e testes

```bash
python -m pip install -r requirements-dev.txt
python -m pytest tests/ --tb=short -rxX
ruff check --select E9,F63,F7,F82 .
```

O [CI](.github/workflows/ci.yml) roda pytest e Ruff. Cada correção de bug confirmado começa com uma [regressão](tests/regressao/README.md) que falha antes e passa depois; bugs abertos ficam em `xfail` estrito. O [golden](tests/fixtures/golden_motores.jsonl) detecta alterações de comportamento no conjunto de casos protegido (os motores rodam com uma data de análise fixa sobre entradas sintéticas; o caminho histórico é coberto por testes próprios), e as [regras de contribuição](AGENTS.md) exigem mutação de pelo menos **80%** nos módulos alvo dos itens de teste. A [auditoria cruzada](docs/loop/auditoria-externa.md) usa uma família de modelo diferente da do executor.

Consulte a [fila e o diário](docs/loop/), o [histórico das fases](docs/loop/historico/), os [ADRs](docs/adr/) e as [fichas metodológicas](docs/metodologia/) para critérios, decisões e limites de cada entrega.

Desenvolvido por **Marcos Felipe dos Santos**.
