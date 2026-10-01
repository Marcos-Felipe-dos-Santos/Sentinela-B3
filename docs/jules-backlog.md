# Backlog do Jules

Três grupos de trabalho para o Jules, conforme a divisão do `docs/PLANO.md`, seção 8.
**Nenhuma issue foi aberta**: este documento é a fonte. O Marcos transforma cada ticket em tarefa do Jules quando a janela do ticket abrir.

Regras que valem para todos os tickets:

- Leia `AGENTS.md` antes de começar. Sem critério de aceite explícito no ticket, não comece.
- O ticket só vale na sua **janela**: o Jules não abre PR que toque arquivo travado da fase em andamento (`docs/PLANO.md`, seção 8). Na dúvida sobre a fase, pergunte ao Marcos.
- O Jules nunca escreve código cujo comportamento correto ainda está sendo decidido, nem toca `methods/`, valuation ou FastAPI.
- Vocabulário: "classificação", "sinal positivo". Nunca "recomendação", "compra" ou "venda" em código, tabela ou tela novos.
- Dados da carteira do Marcos (posições, pesos, lista de ativos) nunca entram em teste, fixture ou documento. Use tickers genéricos (`TST3`, `TST11`).
- IDs de achado (E-*, F-*) vêm de `docs/auditoria/2026-09-red-team.md`.

Janelas, resumidas dos arquivos travados por fase:

| Fase | Trava (resumo) |
|---|---|
| 0 | `CLAUDE.md`, `AGENTS.md`, `docs/`, `pytest.ini`, `pyproject.toml`, `.gitignore`, `tests/conftest.py`, `.github/`, `app.py` |
| 1 | `valuation_engine.py`, `fii_engine.py`, `sentinela/domain/`, `sentinela/methods/` |
| 2A | `market_engine.py`, `cvm_provider.py`, `cvm_fii_provider.py`, `cvm_ticker_map.py`, `cvm_fii_map.py`, `fii_engine.py`, `brapi_provider.py`, `data_quality.py`, `config.py`, `sentinela/data/` |
| 2B | `sentinela/methods/`, `config.py` |
| 2C | `sentinela/methods/`, `config.py`, `peers_engine.py`, `auditoria.py`, `portfolio_engine.py` |
| 3 | `config.py`, `database.py`, `backtesting/`, `sentinela/data/`, `sentinela/services/`, `app.py`, `limpar_banco.py`, `auditar_recomendacoes.py` |
| 4 | `sentinela/jobs/`, `sentinela/reports/`, `sentinela/risk/`, `sentinela/cli.py`, `pyproject.toml`, `requirements*.txt` |
| 6 | `README.md`, `docs/`, arquivos da raiz |
| 7 | `sentinela/api/`, `sentinela/web/`, `app.py`, módulos da V1 na raiz |

---

## Grupo A — Revisão dos PRs de fase

**Objetivo:** o Jules revisa o PR de cada fase (`v2/fase-N`) antes do Marcos aprovar o merge. Ele aponta; não corrige, não remove, não faz commit no branch da fase.

**Configuração (colar no pedido de revisão do Jules):**

1. Contexto obrigatório de leitura: `CLAUDE.md` (armadilhas 1 a 17), `AGENTS.md`, `docs/PLANO.md` (a fase em revisão), o resumo `docs/loop/historico/fase-N/pr-fase-N.md` e o diário da fase.
2. Para cada commit do PR, confirmar:
   - **Um commit por item da fila**, título em Conventional Commit igual ao da fila.
   - **Refactor e mudança de comportamento não se misturam.** Em fase de refactor (Fase 1), nenhum teste das seções A, B e C de `tests/test_financeiro_pre_refactor.py` pode ter mudado.
   - **Sem teste removido, pulado ou enfraquecido.** Todo teste novo falha quando o código coberto é quebrado (pedir a evidência do `mutmut` do diário).
   - **Sem resíduo novo:** código comentado, import sem uso, `print` de depuração, arquivo temporário, TODO sem item na fila.
   - **Arquivos intocáveis da fase** (cabeçalho da fila) sem alteração.
   - **Privacidade:** nenhum dado da carteira em arquivo versionado; nada em `.env`.
   - **Vocabulário:** nenhuma ocorrência nova de "recomendação", "compra", "venda" ou "alocação sugerida".
   - **Rede, banco e relógio** ausentes de `sentinela/methods/`.
3. Resíduos: o Jules **aponta** no PR (arquivo, linha, motivo) e não remove. Quem remove é o loop, com `git rm`, ou o Marcos, no caso de arquivo não rastreado.
4. Formato da resposta: lista por commit, com severidade (bloqueia / ressalva / sugestão) e a evidência (arquivo:linha). Não reescrever o diff.
5. Fora de escopo: decidir metodologia, taxa, janela ou limiar. Dúvida desse tipo vira pergunta ao Marcos, não correção.

**Janela:** a cada checkpoint de fase, depois do `/review-diff` do loop e antes do push.
**Aceite:** comentário de revisão por commit, com a lista de conferências acima respondida.

---

## Grupo B — Testes com especificação externa

Gate de todos os tickets do grupo: **mutation score ≥ 80%** no módulo alvo, medido com `python -m mutmut run "<modulo>*"` e `python -m mutmut export-cicd-stats` (configuração em `[tool.mutmut]`).

> **Aviso explícito: um teste vermelho pode ser o resultado correto.** Os testes abaixo são escritos a partir da especificação externa, não do código. Se o código diverge da especificação, entregue o teste **vermelho** (marcado `xfail(strict=True, raises=AssertionError)` com o motivo) e descreva a divergência no PR. Não "conserte" o código e não ajuste o teste para ficar verde: um teste verde nesse caso significa que você descreveu o código em vez de verificá-lo. Exemplo conhecido: o RSI hoje devolve 50 onde Wilder manda 100.

Mutação sempre com a configuração do `[tool.mutmut]`; `mutants/` nunca entra em commit.

**Mutantes e testes vermelhos.** A mutação roda com `xfail_strict=False`, então um teste `xfail` que falha não mata mutante. Linhas cuja única especificação é um teste vermelho (por exemplo `technical_engine.py:49` e `:72`, ou o ramo de `"3.5"` no B2) deixam mutantes sobreviventes. Nesse caso, calcule o score excluindo os mutantes dessas linhas, liste-os no PR e **não** escreva teste verde que descreva o código só para subir a nota.

### B1 · `technical_engine`

- **Título:** `test: specify technical indicators against Wilder and standard references`
- **Arquivos:** `tests/test_technical_engine_spec.py` (novo). **Não alterar** `technical_engine.py` neste ticket.
- **Janela:** Fases 0 a 5 (as Fases 6 e 7 travam a raiz e os módulos da V1; o ticket só cria um arquivo em `tests/`).
- **Especificação externa** (cite a fonte de cada valor no próprio teste; use exemplos publicados, nunca valores calculados pelo código):
  - RSI de Wilder (período 14): `RSI = 100 − 100/(1+RS)`, com RS = média de ganhos ÷ média de perdas com suavização de Wilder. Sem perdas na janela e com ganhos, **RSI = 100**. Sem ganhos nem perdas, a convenção é 50 (registrar como convenção no teste).
  - MACD (12, 26, 9): linha = EMA12 − EMA26; sinal = EMA9 da linha; histograma = linha − sinal.
  - Bandas de Bollinger (20, 2): média de 20 períodos ± 2 desvios-padrão. A definição original usa o desvio **populacional** (`ddof=0`).
  - ATR de Wilder (14): média móvel suavizada à Wilder do true range, com `TR = max(H−L, |H−C₋₁|, |L−C₋₁|)`.
- **Cenários de falha conhecidos (esperar teste vermelho):**
  1. `technical_engine.py:22-23`: série só de altas (sem perdas) devolve RSI 50 em vez de 100 (achado E-24).
  2. `technical_engine.py:49`: `rolling(20).std()` usa `ddof=1` (amostral), então as bandas ficam mais largas que as de Bollinger.
  3. `technical_engine.py:72`: o ATR usa média simples de 14 (`rolling(14).mean()`), não a suavização de Wilder.
  4. O RSI usa `ewm(alpha=1/14, adjust=False)`, que parte do primeiro valor; Wilder parte da média simples dos 14 primeiros. A diferença decai com o tempo, mas aparece em séries curtas. O MACD tem a mesma característica (`ewm(span=…, adjust=False)`), então `test_macd_valores_de_referencia` pode sair vermelho em série curta.
- **Correção esperada (do loop, depois):** cada divergência confirmada vira item do loop com teste xfail → correção → XPASS. O Jules só reporta.
- **Aceite:** `tests/test_technical_engine_spec.py::test_rsi_sem_perdas_e_100`, `::test_rsi_valor_de_referencia_wilder`, `::test_macd_valores_de_referencia`, `::test_bollinger_usa_desvio_populacional`, `::test_atr_suavizacao_de_wilder`; mutation score ≥ 80% em `technical_engine*`; lista das divergências no PR.

### B2 · `fundamentus_scraper._limpar_valor`

- **Título:** `test: specify brazilian number parsing in the Fundamentus scraper`
- **Arquivos:** `tests/test_fundamentus_limpar_valor.py` (novo). **Não alterar** `fundamentus_scraper.py`.
- **Janela:** Fases 0 a 2C. Atenção: o destino do scraper está em decisão (`docs/decisoes/scraper-fundamentus.md`). Se o Marcos decidir remover o módulo, **cancele o ticket**.
- **Especificação externa:** convenção numérica pt-BR — ponto separa milhar, vírgula separa decimal; `%` é descartado; `-`, `N/A` e vazio são ausência de dado (`None`).
- **Casos mínimos (15 formatos, parametrizados):** `"1.234,56"` → 1234.56; `"15,2%"` → 15.2; `"-"`, `"N/A"`, `""`, `None`, `"   "` → `None`; `"12.345.678"` → 12345678; `"1.500"` → 1500; `"0,5"` → 0.5; `"-0,5"` → −0.5; `"-1.234,56"` → −1234.56; `"35.664.000"` → 35664000; `"35.664.000,00"` → 35664000.0; `"1.234.567,89"` → 1234567.89; `"100"` → 100.0; entrada com espaços internos.
- **Cenários de falha conhecidos (esperar teste vermelho, reportar):**
  1. `"3.5"` hoje vira 3.5 (decimal US) e `"1.500"` vira 1500: a mesma forma de string é interpretada de dois jeitos conforme o número de dígitos depois do ponto. Pela convenção pt-BR, `"3.5"` é inválido ou ambíguo; registre a divergência e **não** escreva teste verde para esse caso: só reporte (um teste exige um valor esperado, e quem o escolhe é o Marcos).
  2. `"35,664,000"` (formato US) vira `None`: as vírgulas viram pontos, `float("35.664.000")` levanta `ValueError` e o dado é descartado sem aviso.
  3. O teste existente `test_scraper_divida_liq_ebitda_parser` (`tests/test_fundamentus_scraper.py:22`) aceita `None` ou qualquer float para `"-0,5"`: não conta como cobertura.
- **Aceite:** `tests/test_fundamentus_limpar_valor.py::test_limpar_valor_formatos_pt_br[...]` (parametrizado, ≥ 15 casos); mutation score ≥ 80% em `fundamentus_scraper._limpar_valor`; divergências listadas no PR.

### B3 · `database.adicionar_posicao`

- **Título:** `test: specify weighted average price in the portfolio ledger`
- **Arquivos:** `tests/test_database_posicoes.py` (novo). **Não alterar** `database.py`.
- **Janela:** Fases 0 a 2C (a Fase 3 trava `database.py`). Use banco temporário (`tmp_path`); sem rede.
- **Especificação externa:** custo médio ponderado da posição. Compra adicional: `PM = (Q₀·PM₀ + Q·P) / (Q₀ + Q)`. **Venda parcial reduz a quantidade e não altera o preço médio** (regra do custo médio usada na apuração de ganho de capital). Venda total zera e remove a posição.
- **Casos:** primeira compra (insere com data de hoje); aporte adicional (média ponderada, comparada com `pytest.approx`; o código não arredonda); venda parcial (`qtd` negativa); zeragem exata; venda maior que a posição (documente o comportamento, não escolha); compra de quantidade zero; ticker em minúsculas com espaços; venda de ticker inexistente (não insere).
- **Cenário de falha conhecido (esperar teste vermelho):** `database.py:69-72` recalcula o PM também na venda, usando o preço de venda: `novo_pm = (Q₀·PM₀ + qtd·preço) / nova_qtd` com `qtd < 0`. Vender 50 de 100 a preço diferente do PM muda o preço médio, contrariando a regra do custo médio.
- **Aceite:** `tests/test_database_posicoes.py::test_aporte_adicional_media_ponderada`, `::test_venda_parcial_preserva_preco_medio`, `::test_zeragem_remove_posicao`, `::test_ticker_normalizado`, `::test_venda_de_ticker_inexistente_nao_insere`; mutation score ≥ 80% em `database.adicionar_posicao`; divergência da venda parcial no PR.

### B4 · `cvm_provider` (E-7, E-8, E-20)

Três tickets **sequenciais** (mesmo arquivo; não abrir em paralelo). **Janela: Fase 1, e todos os três devem estar mergeados antes de começar a Fase 2A**, que trava `cvm_provider.py` e `cvm_fii_provider.py`. Ordem: B4.1 → B4.2 → B4.3. Teste primeiro (xfail estrito → correção → XPASS); estes três mexem em código de produção porque a correção é especificada pela auditoria. Sem rede: ZIPs sintéticos em `tmp_path`. `cvm_provider.py` hoje é coberto por `tests/test_cvm_provider.py`; as seções A, B e C de `tests/test_financeiro_pre_refactor.py` não podem mudar.

**B4.1 · E-20 — um único parser de demonstrativo**
- **Título:** `fix: apply monetary scale in the single CVM statement parser`
- **Arquivos:** `cvm_provider.py` (linhas 89-128), `tests/test_cvm_provider.py`.
- **Cenário de falha:** `parsear_demonstrativo` (público, testado, sem `ESCALA_MOEDA`) e `_parsear_com_cvm` (privado, com ×1000 para "MIL") divergem; reutilizar o público dá valores monetários 1000× menores.
- **Correção esperada:** um parser que aplica a escala; o outro sai. O parâmetro `include_cd_cvm` deve ter padrão que preserve as 5 colunas do contrato público atual (`_OUTPUT_COLS`). Isto **muda comportamento** (valores do parser público passam a ser ×1000 para "MIL"), por isso o título é `fix:`; os testes existentes que fixam o valor sem escala mudam de propósito, com justificativa no PR.
- **Aceite:** `tests/test_cvm_provider.py::test_parser_aplica_escala_mil`, `::test_parser_unico_sem_duplicata`; nenhuma asserção removida (só os valores esperados que ignoravam a escala mudam, com justificativa); mutation ≥ 80% em `cvm_provider*`. Comportamento idêntico para quem usava o parser privado.

**B4.2 · E-8 — seleção determinística do período**
- **Título:** `fix: select most recent CVM statement row deterministically`
- **Arquivos:** `cvm_provider.py` (função `_conta`, linhas 162-167), `tests/test_cvm_provider.py`.
- **Cenário de falha:** a CVM republica um DFP; a versão nova entra em outra posição do CSV; `rows.iloc[0]` escolhe pela ordem física e o ROE muda entre duas execuções sem mudança de código.
- **DECISÃO DO MARCOS ANTES DE ABRIR ESTE TICKET:** a correção da auditoria (ordenar por `DT_REFER`) não separa uma republicação, que mantém o mesmo `DT_REFER` e muda a coluna `VERSAO` (presente na fixture de `tests/test_cvm_provider.py`). Além disso, a regra "erro se houver mais de uma linha na mesma data" dispararia justamente na republicação e o ano sumiria em silêncio (`calcular_indicadores` envolve o ano em `try`). Critério candidato: `VERSAO` decrescente, com `DT_REFER` como chave secundária. Até o Marcos escolher o critério, o ticket **não é aberto**.
- **Correção esperada (após a decisão):** o critério escolhido antes de `iloc[0]`; propagar `DT_REFER` e a versão usada como `cvm_dt_refer` e `cvm_versao` em `dados`.
- **Aceite:** `tests/test_cvm_provider.py::test_conta_prefere_dt_refer_mais_recente` (xfail estrito → XPASS), `::test_conta_republicada_usa_maior_versao`, `::test_cvm_dt_refer_propagado` (nomes sujeitos ao critério decidido).

**B4.3 · E-7 — download atômico dos ZIPs**
- **Título:** `fix: make CVM ZIP downloads atomic and verified`
- **Arquivos:** `cvm_provider.py` (49-57), `cvm_fii_provider.py` (56-64), novo módulo compartilhado de download, testes.
- **Cenário de falha:** a conexão cai no meio de `resp.content`; o arquivo parcial fica com `mtime` atual e passa no teste de frescor por 7 dias; toda análise perde a CVM em silêncio.
- **Correção esperada:** baixar para `dest.with_suffix('.tmp')`, validar com `zipfile.ZipFile(tmp).testzip()`, só então `os.replace(tmp, dest)`; retry com backoff exponencial (3 tentativas); extrair `_baixar` para um módulo compartilhado (hoje duplicado nos dois providers).
- **Aceite:** `tests/test_cvm_download.py::test_zip_corrompido_nao_substitui_cache`, `::test_download_interrompido_nao_deixa_destino_parcial`, `::test_retry_com_backoff`; os dois providers usam o módulo compartilhado.

---

## Grupo C — Achados de baixa severidade, por arquivo

Os achados de menor severidade da auditoria (E-23 a E-30 e F-16 a F-30), agrupados pelo arquivo que tocam. **Sequencial** = não abrir PR em paralelo com outro ticket do mesmo arquivo. Só entra aqui o que tem comportamento correto especificado pela auditoria; o resto fica com o loop ou com o Marcos (tabela C-fora).

### C-A · `README.md` (docs; 1 ticket, sequencial entre si)

- **Título:** `docs: fix cascade diagram and roadmap claims in README`
- **Achados:** E-28 (README diz brapi como "cotação preferencial"; o código só usa o preço da brapi se o yfinance falhar), F-27 (roadmap marca ✅ "cálculo de vacância", e o provider documenta que vacância não existe no informe mensal).
- **Arquivos:** `README.md`. **Janela:** Fases 0 a 5 (a Fase 6 trava o README).
- **Correção:** ordem real da cascata (`market_engine.py:327-342`): yfinance → brapi → CVM → Fundamentus; fundamentos: CVM > brapi > yfinance > Fundamentus; vacância como item não iniciado.
- **Aceite:** o diagrama bate com `CLAUDE.md` ("Fluxo de dados real"); diff só no `README.md`. Cada afirmação conferida contra o código no PR.

### C-B · `.env.example` (config; 1 ticket)

- **Título:** `chore: document BRAPI_TOKEN in .env.example`
- **Achado:** `BRAPI_TOKEN` é lido em `brapi_provider.py:72` e falta no `.env.example` (levantamento da análise financeira; não verificado pelo loop, que não lê arquivos `.env*`).
- **Arquivos:** `.env.example`. **Janela:** qualquer fase, exceto a 6 (arquivos da raiz). Nunca tocar em `.env`.
- **Aceite:** a variável aparece com valor vazio e comentário (opcional; sem token a brapi fica desligada); `git diff` só nessa linha.

### C-C · `peers_engine.py` (1 ticket)

- **Título:** `fix: use median and reliable P/E in peer comparison`
- **Achado:** F-23 — média aritmética de P/L entre pares, sem excluir `pl_confiavel=False` (`peers_engine.py:86-88`).
- **Arquivos:** `peers_engine.py`, `tests/test_peers_engine.py`. **Janela:** Fases 0 a 2B (a 2C trava `peers_engine.py`). Teste xfail estrito primeiro.
- **Correção:** mediana no lugar da média e filtro por `pl_confiavel`, **só no P/L** (as médias de P/VP e DY e os nomes das chaves, como `PL_Media_Peers`, ficam como estão; o Marcos decide se estendem). **Fora do ticket:** a incoerência de MGLU3 (par de varejo e ao mesmo tempo distressed) é decisão do F2C-7; não mexer na lista.
- **Aceite:** `tests/test_peers_engine.py::test_pl_setorial_usa_mediana`, `::test_pl_nao_confiavel_fica_fora_da_mediana`.

### C-D · `data_quality.py` (1 ticket; sequencial com o F2A-5 do loop)

- **Título:** `fix: stop crediting cached data as fresh collection`
- **Achado:** E-23 — o alias `fundamentals_cache → fundamentus` (confiança 40) torna inalcançável a entrada `cache` (30) em `data_quality.py:45-58`.
- **Arquivos:** `data_quality.py`, `tests/test_data_quality.py`. **Janela: Fase 1.** A Fase 2A trava o arquivo, e o F2A-5 (validação cruzada) mexe no mesmo módulo: este ticket tem de estar mergeado antes.
- **Correção:** remover o alias; `cache` passa a ser fonte própria com sua confiança.
- **Aceite:** `tests/test_data_quality.py::test_fonte_cache_tem_confianca_propria` (xfail estrito → XPASS); score de dados em cache menor ou igual ao de coleta fresca.

### C-E · `config.py` (comentários; 1 ticket)

- **Título:** `docs: correct FII segment comments in config`
- **Achado:** F-26 — segundo a auditoria, os comentários de segmento de `FIIS_CONHECIDOS` estão errados (HGLG11 sob "Papel"; KNIP11 e HGCR11 sob "Tijolo"; BCFF11 é fundo de fundos sob "Tijolo") e nenhum código distingue segmento (`config.py:41-53`).
- **Arquivos:** `config.py`, **somente comentários** — nenhuma constante muda. **Janela: Fase 1** (as Fases 2A, 2B, 2C e 3 travam `config.py`). Confira o segmento de cada FII em fonte oficial (B3 ou regulamento) e cite-a no PR; sem fonte, **remova o comentário** em vez de corrigi-lo.
- **Aceite:** `python -m pytest tests/` verde; `git diff` só com linhas de comentário.

### C-fora · Não vão ao Jules

| Achado | Por que fica fora | Onde vive |
|---|---|---|
| E-24 RSI 50 em vez de 100 | A correção é do loop, depois do teste do B1 | B1 e item futuro do loop |
| E-25 vacância duplicada (`config` × `fii_engine`) | Duas tabelas ignoradas; `fii_engine` travado nas Fases 1 e 2A e `config` em quase todas | F2A-13 |
| E-26 caminho do banco e versão de schema | Absorvido pelo SQLite único com migrations | F3-2 e F3-9 |
| E-27 `CLAUDE.md` desatualizado | Reescrito no bootstrap e conferido no F0-1 | F0-1 |
| E-29 sem autenticação | Não publicar sem auth; decisão do Marcos | Fase 7 |
| E-30 código morto | Limpeza com `git rm` pelo loop | F0-7, F0-8 |
| F-16 bounds do Markowitz | O otimizador é aposentado | F2C-9 |
| F-17 custos e IR ausentes | Decisão metodológica | Fases 3 e 4 |
| F-18 `auto_adjust=False` no backtest, F-19 horizonte zero, F-20 sem survivorship, F-29 CSV de resultados antigo | Backtest e `backtesting/` são do loop | F3-8 |
| F-21 rentabilidade sem proventos nem ajuste de eventos | Modelo de dados novo | Fase 4 |
| F-22 lista de distressed manual | Critério derivado de dado, decisão do Marcos | F2C-7 |
| F-24 TTM via ITR | Código de dados, trava da 2A | F2A-7 |
| F-25 scraper e ToS | Decisão do Marcos | `docs/decisoes/scraper-fundamentus.md` |
| F-28 score colado no gate | Histerese é decisão de valuation | F2C-3 |
| F-30 mensagem "ticker fora do mapa CVM" | Mexe em `app.py` (travado nas Fases 0, 3 e 7) e depende do mapa novo | F2A-1 |
