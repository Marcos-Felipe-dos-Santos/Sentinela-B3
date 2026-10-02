# RED TEAM AUDIT — SENTINELA B3

**Repositório auditado:** `Marcos-Felipe-dos-Santos/Sentinela-B3`
**Commit:** `ac19541` (merge PR #8, `feat/ui-improvements`)
**Data da auditoria:** 09/09/2026
**Escopo:** 11.466 linhas Python, 80 arquivos, suíte de 255 testes executada (2,13s, sem rede), cobertura medida (73% global).

**Método:** leitura integral de `config.py`, `valuation_engine.py`, `market_engine.py`, `fii_engine.py`, `cvm_provider.py`, `cvm_fii_provider.py`, `brapi_provider.py`, `fundamentus_scraper.py`, `data_quality.py`, `database.py`, `portfolio_engine.py`, `technical_engine.py`, `peers_engine.py`, `ai_core.py`, `app.py`, `backtesting/`, `sentinela/`; execução da suíte; inspeção dos CSVs commitados; análise do histórico Git.

**Convenção:** cada achado traz `SEVERIDADE` explícita, exigida pela matriz consolidada ao final.

---

# FASE 1 — AUDITORIA DE ENGENHARIA DE SOFTWARE

## 1.1 Arquitetura real (não a pretendida)

O README descreve uma cascata `CVM → brapi → yfinance → Fundamentus`. O código executa outra coisa.

Ordem real em `market_engine.buscar_dados_ticker` (linhas 327-342):

1. **yfinance sempre primeiro** — define `preco_atual`, `historico`, `_shares_outstanding` e fundamentos básicos.
2. **brapi** — sobrescreve fundamentos (`overwrite=True`), mas só preenche preço **se yfinance falhou**.
3. **CVM** — sobrescreve fundamentos; deriva `lpa`, `vpa`, `pl`, `pvp` a partir de `_shares_outstanding` do yfinance.
4. **Fundamentus** — apenas preenche lacunas (`overwrite` ausente).
5. Cache SQLite (7d) → fallback manual FII.

Precedência efetiva de fundamentos: CVM > brapi > yfinance > Fundamentus. Precedência de **preço**: yfinance > brapi > Fundamentus — o inverso do documentado.

Existem **duas camadas de orquestração paralelas**: `app.py` (linhas 200-235) e `sentinela/services/analyze_asset.py::AnalysisService`. A segunda replica exatamente a primeira e é importada apenas por `tests/test_analysis_service.py`. A migração para Clean Architecture está iniciada e desconectada.

**Single points of failure arquiteturais:**

| Ponto | Consequência da falha |
|---|---|
| `_shares_outstanding` do yfinance | Sem ele, CVM não produz `lpa`/`vpa`/`pl`/`pvp` — a "fonte primária auditada" vira apenas ROE e margens |
| `MACRO = MacroContext()` no import de `config.py` | I/O de rede em tempo de import; Selic congelada no processo |
| `hist['Close'].iloc[-1]` | Único caminho de preço na prática; define o denominador de todo múltiplo |
| `FundamentusScraper._lock` | Serializa todas as threads do `peers_engine` em 2,5s cada |

**Escalabilidade:** a arquitetura **não** sobrevive a 10x. `CVMProvider.calcular_indicadores` reabre e reparseia os CSVs completos do ZIP DFP (centenas de MB) a cada chamada, sem memoização do DataFrame. `peers_engine` dispara até 8 threads, cada uma chamando `_buscar_cvm`. Com 5 peers isso são 5 parses completos simultâneos do mesmo arquivo.

## 1.2 Code smells por categoria

**Bloaters:** `auditoria.py` (936 linhas, 0% cobertura), `market_engine.py` (691), `app.py` (543, 0% cobertura), `backtest_engine.py` (740). `ValuationEngine.processar` é uma função única de 240 linhas com 4 modelos, normalização, scoring, 3 guards e logging.

**Object-Orientation Abusers:** `PortfolioResult(dict)` sobrescreve `values()` para esconder chaves com `_` — herança usada para contrabandear metadados num contrato de dicionário.

**Change Preventers:** vacância de FII duplicada em `config.FII_MANUAL_FALLBACK` e `fii_engine.VACANCIA_CONHECIDA` com os mesmos tickers e valores. Normalização de DY replicada em três lugares com três regras distintas.

**Dispensables (código morto confirmado por grep):** `CVMProvider.baixar_itr`, `CVMProvider.parsear_demonstrativo` (só testes), `MacroContext.cdi`, `.ipca_12m`, `.ntnb_longa`, `.cost_of_equity_real()` (só testes), `cvm_fii_provider.dy_mes_decimal` (nunca lido), `_FONTE_CONFIANCA["cache"]` (inalcançável), filtro `p > 0.01` em `portfolio_engine:96` (impossível dado `bounds` mínimo 0.05).

**Couplers:** `valuation_engine` importa `_normalizar_dy` — função privada de `config`. `market_engine` conhece a estrutura interna de resposta de quatro provedores diferentes.

**Naming ambíguo:** `div_liq_patrimonio` recebe `(passivo_total − PL)/PL` (ver F-12); `dados_manual`, `dados_cache`, `dados_parciais` como flags booleanas paralelas em vez de um enum de estado; `_CVM_TO_MARKET` mapeia `divida_pl` → `div_liq_patrimonio`, dois nomes errados para a mesma grandeza.

**TODOs/comentários fossilizados:** `database.py:10-14` propõe uma tabela `cache_fundamentos` que **já existe** (`fundamentals_cache`, linha 41) — o TODO sobreviveu à própria implementação. `app.py` tem comentários `CORREÇÃO CRÍTICA v12.1`, `RESTAURADA v12.1`, `CORRIGIDO:` espalhados como changelog inline. `CLAUDE.md` lista quatro "bugs conhecidos" já corrigidos.

## 1.3 Cobertura de testes — o que os 255 testes realmente cobrem

```
app.py                       0%   (543 linhas — UI + orquestração + persistência)
auditoria.py                 0%   (936 linhas)
limpar_banco.py              0%   (196 linhas)
fundamentus_scraper.py      39%   (buscar_dados e _limpar_valor: 0%)
database.py                 58%   (adicionar_posicao — média ponderada: 0%)
valuation_engine.py         96%
data_quality.py             97%
TOTAL                       73%
```

Os testes são sintéticos e sem rede — bom para velocidade, mas cobrem funções puras, não integração. **Nenhum teste** exercita: o parser de números brasileiros que alimenta todo fundamento do Fundamentus, a matemática de preço médio da carteira, a mutação `dados.update(analise)`, ou o comportamento de qualquer provedor sob resposta malformada real. O badge "255 testes" no README mede volume, não risco coberto.

---

## ACHADOS — ENGENHARIA

---

```
[ID: E-1]
[FASE: ENGENHARIA]
[CATEGORIA: 1.5 Dados e Persistência — integridade de derivação]
```
**ACHADO:** `lpa` e `vpa` são calculados dividindo o lucro/PL **consolidado** da CVM pelo `sharesOutstanding` do yfinance, sem nenhuma verificação de que o denominador cobre todas as classes de ação da empresa.

**LOCAL:** `market_engine.py:503-519`; `cvm_ticker_map.py:15-68` (`_MANUAL_MAP` mapeia CD_CVM → **um único** ticker por empresa).

**PROBLEMA:** `CD_CVM` identifica a **companhia**; `sharesOutstanding` do Yahoo para `PETR4.SA` tende a refletir a classe cotada, não o total ON+PN. O numerador é consolidado, o denominador é de escopo indeterminado e vem de outra fonte. Não há reconciliação (`shares × preço ≈ market cap`, ou `lpa_cvm ≈ lpa_brapi`).

**CENÁRIO DE FALHA:** PETR4, lucro consolidado R$ 36bi, PL R$ 375bi, preço R$ 32. Total real ≈ 13,04bn ações; PN isoladas ≈ 5,60bn.
- Com denominador correto: LPA 2,76 → P/L 11,6; VPA 28,8 → P/VP 1,11; Graham = √(22,5 × 2,76 × 28,8) = **R$ 42,3** (+32%).
- Com denominador da classe PN: LPA 6,43 → P/L 4,98 → piso de 7 dispara → `lpa_adj` = 32/7 = 4,57; VPA 66,9 → P/VP 0,48; Graham = √(22,5 × 4,57 × 66,9) = **R$ 82,9** (+159%).

O gate `pvp ≤ 2,5` passa folgadamente (0,48), o gate `pl ≤ 25` passa, `pl_confiavel` continua `True`, e o badge exibido é 🟢 **Dados CVM**. O usuário vê o selo de maior confiança do sistema sobre o número mais errado que ele produz.

**SEVERIDADE:** CRÍTICO

**CORREÇÃO:** (a) Estender `_MANUAL_MAP` para `CD_CVM → {classes: [ON, PN, UNIT], shares_por_classe}` a partir do formulário CVM ou do arquivo de composição de capital da B3. (b) Guard obrigatório: rejeitar a derivação se `|shares × preço − market_cap_yfinance| / market_cap > 0,05`. (c) Enquanto (a) não existir, **não derivar `pl`/`pvp` da CVM** — usar brapi/yfinance para múltiplos e CVM só para ROE/margens/receita. `REQUER VALIDAÇÃO`: confirmar empiricamente o escopo de `sharesOutstanding` do yfinance para 5 tickers dual-class (PETR4, ITUB4, BBDC4, ELET6, GGBR4) antes de escolher entre (a) e (c).

**ESFORÇO:** 2 dias para (b)+(c); 4-5 dias para (a).

---

```
[ID: E-2]
[FASE: ENGENHARIA]
[CATEGORIA: 1.5 Dados e Persistência — validação de esquema/consistência]
```
**ACHADO:** A validação cruzada de P/L e P/VP é matematicamente incapaz de disparar no caminho CVM — exatamente o caminho de maior risco.

**LOCAL:** `data_quality.py:198-217` (checks 2 e 3) versus `market_engine.py:513` (`cvm_campos['pl'] = preco / lpa_cvm`) e `:519` (`cvm_campos['pvp'] = preco / vpa_cvm`).

**PROBLEMA:** O check calcula `pl_derivado = preco / lpa` e alerta se divergir >10% de `pl`. Mas `pl` **foi definido como** `preco / lpa`. A identidade é tautológica: divergência ≡ 0 sempre. O README anuncia esse check como "alertas de consistência (ex.: P/L declarado diverge > 10% de preço/LPA derivado)" — é a rede de segurança que deveria capturar o achado anterior, e ela está estruturalmente desligada.

**CENÁRIO DE FALHA:** Qualquer erro no `sharesOutstanding` propaga por `lpa` → `pl` de forma perfeitamente consistente. O relatório de qualidade retorna zero alertas, `completude_pct` = 100%, badge 🟢, e a análise sai com fair value 2x errado e selo verde.

**SEVERIDADE:** CRÍTICO

**CORREÇÃO:** Preservar `_raw_source_values` em `market_engine` (o próprio docstring de `data_quality.py:6-8` reconhece a lacuna e a classifica como "fora do escopo desta sessão"). Comparar **fonte contra fonte**: `pl_cvm` vs `pl_brapi` vs `pl_yfinance`. Adicionar check de identidade contábil: `|pl × lpa − preco| < 0,01` deve ser **excluído** dos alertas por ser trivial, e `|market_cap_derivado − market_cap_yfinance|` incluído.

**ESFORÇO:** 1,5 dia.

---

```
[ID: E-3]
[FASE: ENGENHARIA]
[CATEGORIA: 1.5 Dados e Persistência — ponto de mutação silenciosa]
```
**ACHADO:** `dados.update(analise)` sobrescreve os valores de entrada com as saídas derivadas, antes do relatório de qualidade e antes da persistência.

**LOCAL:** `app.py:227` (`dados.update(analise)`), `:228`, `:234-235` (persistência), `:255` (`DataQualityReport(dados)`).

**PROBLEMA:** Para FIIs, `FIIEngine.analisar` retorna `dy`, `dy_efetivo` e `pvp` (linhas 144-146). O `update` substitui `dados['dy']` (bruto da fonte) pelo DY normalizado e ajustado por vacância, e `dados['pvp']` pelo P/VP recalculado. Depois disso, `DataQualityReport` avalia o valor **pós-processado** achando que avalia o bruto, e `field_provenance` — construído em `market_engine:302-307` sobre os valores originais — passa a descrever números que não estão mais no dicionário. Para ações, o mesmo `update` não sobrescreve `dy`, então o relatório avalia o valor bruto. Duas semânticas diferentes para a mesma tela.

**CENÁRIO DE FALHA:** FII com DY bruto 30% (bug de fonte) e vacância manual 25%: `dy_efetivo` = 0,225. O check 1 de `validacao_cruzada` (`dy > 0,25`) **não dispara** porque avalia 0,225 pós-ajuste. O alerta que existe exatamente para pegar esse bug foi desarmado pela mutação. O registro persistido em `analises.dados_completos` mistura entrada e saída de forma irreversível — impossível auditar depois qual foi o dado de origem.

**SEVERIDADE:** CRÍTICO

**CORREÇÃO:** Nunca mutar `dados`. Usar `AnalysisResult` (já existe em `sentinela/domain/models.py`, 98% coberto) com campos separados `raw`/`derived`. Construir o `DataQualityReport` **antes** de qualquer engine rodar. Persistir os dois blocos separados.

**ESFORÇO:** 1 dia (o modelo de domínio já existe; é ligação).

---

```
[ID: E-4]
[FASE: ENGENHARIA]
[CATEGORIA: 1.5 Dados e Persistência — unidades e normalização]
```
**ACHADO:** Três normalizadores de DY independentes, com regras diferentes, aplicados em cascata sobre o mesmo campo.

**LOCAL:**
- `market_engine.py:377-379` — `if dy_raw > 1: dy_raw /= 100`
- `brapi_provider.py:35-43` — `if numero > 1 or (assume_subunit_percent and numero > 0.25): numero /= 100`
- `config.py:311-317` (`_normalizar_dy`) — `>1 → /100`; `>0.25 → (0.0, False)`
- `fundamentus_scraper.py:174-176` — `/100` incondicional

**PROBLEMA:** Não existe fronteira canônica de unidade. O mesmo campo atravessa 2-3 conversões dependendo da fonte que venceu a cascata, e a terceira (`_normalizar_dy`, chamada por `valuation_engine:46` e `fii_engine:50`) roda sobre um valor já normalizado.

**CENÁRIO DE FALHA:** brapi retorna `dividendYield = 0.30` para um FII de papel (30%, plausível em fundo com amortização). `_percent_to_decimal(..., assume_subunit_percent=True)`: 0,30 > 0,25 → divide por 100 → **0,003**. `_normalizar_dy(0.003)` → 0,003, `dy_confiavel=True`. Um DY de 30% vira 0,3% com flag de confiança verde. `FIIEngine` calcula `preco_justo = p × 0,003 / 0,1254` = **2,4% do preço**, `upside` = −97,6%, recomendação **VENDA** com score mínimo. Erro de duas ordens de grandeza, sem um único alerta.

**SEVERIDADE:** ALTO

**CORREÇÃO:** Normalizar **uma vez**, na fronteira de cada provider, para `ratio` decimal, e marcar o campo como já-normalizado (`FieldValue.unit` já existe em `sentinela/domain/provenance.py` e não é usado para isso). `_normalizar_dy` deve virar assert de invariante (`0 ≤ dy ≤ 0.30`), não conversor. Teste de propriedade: para cada provider, o mesmo DY de entrada em qualquer representação deve produzir o mesmo decimal.

**ESFORÇO:** 1,5 dia.

---

```
[ID: E-5]
[FASE: ENGENHARIA]
[CATEGORIA: 1.2 Qualidade de código — ordem de guards]
```
**ACHADO:** `_normalizar_dy` nunca aplica `DY_SANIDADE_MAX` ao ramo percentual — o teto de sanidade só existe para valores já decimais.

**LOCAL:** `config.py:311-317`.

```python
if dy_raw > MACRO.DY_PERCENTUAL_THRESHOLD:   # > 1.0
    return dy_raw / 100, True                # ← sai sem checar 0.25
if dy_raw > MACRO.DY_SANIDADE_MAX:           # > 0.25
    return 0.0, False
```

**PROBLEMA:** `dy_raw = 40` (40%) retorna `(0.40, True)` — acima de `DY_SANIDADE_MAX = 0.25`, mas com `dy_confiavel=True`. Já `dy_raw = 0.40` retorna `(0.0, False)`. A mesma grandeza econômica recebe tratamentos opostos conforme a representação de entrada. Adicionalmente, a faixa 0,25 < x ≤ 1,0 é **sempre descartada**: um ativo com DY de 0,5% reportado como `0.5` é jogado fora como "impossível".

**CENÁRIO DE FALHA:** Cache do Fundamentus guarda `dy` já dividido por 100. Se uma leitura futura desse cache passar por um caminho que não divide de novo, tudo bem. Mas qualquer fonte que entregue percentual bruto acima de 25 escapa do gate de sanidade e alimenta Bazin/Gordon/FII com um DY absurdo marcado como confiável.

**SEVERIDADE:** ALTO

**CORREÇÃO:** Normalizar primeiro, validar depois, sempre nessa ordem:
```python
dy = dy_raw / 100 if dy_raw > 1.0 else dy_raw
return (dy, True) if dy <= DY_SANIDADE_MAX else (0.0, False)
```
Adicionar teste parametrizado cobrindo a faixa 0,20 a 1,20 em passos de 0,05.

**ESFORÇO:** 1 hora + testes.

---

```
[ID: E-6]
[FASE: ENGENHARIA]
[CATEGORIA: 1.1 Arquitetura — efeito colateral em import / 1.5 cache]
```
**ACHADO:** `MACRO = MacroContext()` executa no import de `config.py`, dispara HTTP para o BCB, e congela a Selic pelo tempo de vida do processo. O TTL de 24h nunca refresca a instância global.

**LOCAL:** `config.py:308` (instanciação), `:196-198` (`__init__` chama `get_selic_atual()`), `:82-117` (cache com TTL).

**PROBLEMA:** Três consequências distintas. (1) Importar `config` — o que qualquer módulo, teste ou script CLI faz — dispara I/O de rede com timeout de 5s. (2) `MACRO._selic` é lido uma vez; `SELIC_CACHE_TTL = 86400` protege `get_selic_atual()`, mas `MACRO.selic` já capturou o float. Um processo Streamlit rodando por uma semana usa a Selic do momento do boot. (3) `valuation_engine:58` e `fii_engine:102` chamam `get_selic_atual()` diretamente em vez de `MACRO.selic`, criando dois caminhos que só coincidem por acidente do cache compartilhado — enquanto o README afirma que "todos os parâmetros econômicos são buscados pelo MacroContext e compartilhados por todos os engines via MACRO global".

**CENÁRIO DE FALHA:** Copom corta a Selic de 14,75% para 13,25% numa quarta-feira. O app, aberto desde segunda, continua descontando com 14,75%. Todo Bazin e todo Gordon saem sistematicamente baixos, e nada na tela indica que o parâmetro está velho — não há timestamp da Selic em lugar nenhum da UI.

**SEVERIDADE:** ALTO

**CORREÇÃO:** Remover a instanciação em tempo de import; expor `get_macro()` com `@st.cache_resource(ttl=3600)` ou lazy singleton. Tornar `MacroContext.selic` uma property que consulta o cache com TTL a cada acesso. Expor `macro.selic_atualizado_em` na UI. Unificar: nenhum engine deve chamar `get_selic_atual()` diretamente.

**ESFORÇO:** 4 horas.

---

```
[ID: E-7]
[FASE: ENGENHARIA]
[CATEGORIA: 1.4 Resiliência — cache envenenado]
```
**ACHADO:** O download dos ZIPs da CVM não é atômico e não valida integridade. Um arquivo corrompido passa no teste de frescor por 7 dias.

**LOCAL:** `cvm_provider.py:49-57` e `cvm_fii_provider.py:56-64` (implementações duplicadas).

```python
resp = requests.get(url, timeout=60, stream=True)
resp.raise_for_status()
dest.write_bytes(resp.content)     # escrita direta no destino final
```

**PROBLEMA:** `_is_fresh` julga apenas `mtime`. Se a conexão cair no meio de `resp.content`, ou o disco encher, o arquivo parcial fica no destino com mtime atual. `zipfile.ZipFile` levanta `BadZipFile`, capturada pelo `except Exception` de `calcular_indicadores:203`, que loga um warning e retorna `{}`. `_buscar_cvm` marca `cvm_disponivel = False` e segue. Nota adicional: `stream=True` seguido de `.content` anula o streaming — o arquivo inteiro carrega em memória de qualquer forma.

**CENÁRIO DE FALHA:** Queda de rede durante o download do DFP 2025 (~200MB). Pelos 7 dias seguintes, **toda** análise de ações perde a fonte primária CVM e cai para brapi/yfinance, com badge mudando de 🟢 para 🟡/🔴 sem explicação. O `sentinela.log` tem um `warning` por chamada, mas a UI não mostra a causa. O usuário conclui que "o mapa CVM não cobre esse ticker".

**SEVERIDADE:** ALTO

**CORREÇÃO:** Baixar para `dest.with_suffix('.tmp')`, validar com `zipfile.ZipFile(tmp).testzip()`, e só então `os.replace(tmp, dest)`. Extrair `_baixar` para um módulo compartilhado (hoje duplicado). Adicionar retry com backoff exponencial (3 tentativas) e registrar `content-length` esperado vs recebido.

**ESFORÇO:** 4 horas.

---

```
[ID: E-8]
[FASE: ENGENHARIA]
[CATEGORIA: 1.5 Dados — seleção não determinística de período]
```
**ACHADO:** `_conta` retorna `rows.iloc[0]` sem ordenar nem validar `DT_REFER`.

**LOCAL:** `cvm_provider.py:162-167`.

**PROBLEMA:** Depois do filtro por `CD_CVM` e `CD_CONTA`, ainda podem restar múltiplas linhas — reapresentações, períodos distintos no mesmo arquivo, ou o mesmo código de conta em contextos diferentes. O filtro `ORDEM_EXERC == "ÚLTIMO"` reduz mas não garante unicidade. `iloc[0]` seleciona pela ordem física das linhas no CSV, que é uma propriedade do arquivo da CVM, não um contrato.

**CENÁRIO DE FALHA:** A CVM republica o DFP de uma empresa (evento rotineiro após ressalva de auditoria). A nova versão entra no CSV em posição diferente. O ROE muda entre duas execuções sem que nada no código tenha mudado, e sem que o usuário perceba — não há hash nem `DT_REFER` no output. Análises salvas em datas diferentes tornam-se incomparáveis.

**SEVERIDADE:** ALTO

**CORREÇÃO:** `rows.sort_values("DT_REFER", ascending=False).iloc[0]`, propagar `DT_REFER` para `dados['cvm_dt_refer']`, exibir na UI e usar como chave de invalidação de cache. Levantar exceção explícita se `len(rows) > 1` após ordenação e as datas forem iguais.

**ESFORÇO:** 3 horas.

---

```
[ID: E-9]
[FASE: ENGENHARIA]
[CATEGORIA: 1.1 Arquitetura — classificação de ativos]
```
**ACHADO:** `AssetClassifier` trata qualquer ticker terminado em "11" como FII. A lista de exceções tem 12 entradas e não inclui dois tickers usados pelo próprio projeto.

**LOCAL:** `sentinela/services/asset_classifier.py:39-40`; `config.py:56-59` (`UNITS_CONHECIDAS`); `peers_engine.py:13` (`BPAC11`) e `:22` (`IGTI11`).

**PROBLEMA:** `BPAC11` (units BTG Pactual) e `IGTI11` (units Iguatemi) estão no `peers_map` do projeto como bancos e shoppings, e **não** estão em `UNITS_CONHECIDAS`. O classificador os retorna como FII. Contradição interna demonstrável. ETFs (`BOVA11`, `SMAL11`, `IVVB11`) e todas as demais units da B3 caem no mesmo buraco.

**CENÁRIO DE FALHA:** Usuário digita `BPAC11` no Terminal. `app.py:207` classifica como FII → `FIIEngine.analisar` → `preco_justo = p × DY / (Selic × 0,85)`, `tipo = "TIPO INDISPONÍVEL"`, sem peers, sem CVM, sem análise de balanço. Um banco de investimento recebe valuation de fundo imobiliário. Em paralelo, `_required_fundamentals_for` passa a exigir apenas `(pvp, dy)`, então `dados_parciais` fica `False` e o sistema declara **"Dados suficientes para análise"**.

**SEVERIDADE:** ALTO

**CORREÇÃO:** Inverter a regra: FII exige evidência positiva (presença em `FII_CNPJ_MAP`, ou `quoteType == MUTUALFUND`, ou CNPJ encontrado no Informe Mensal). Sufixo "11" isolado → `AssetType.UNKNOWN` com aviso na UI, nunca FII por default. Adicionar `AssetType.ETF`. Teste de regressão obrigatório: todo ticker do `peers_map` deve classificar como `STOCK` ou `UNIT`.

**ESFORÇO:** 6 horas.

---

```
[ID: E-10]
[FASE: ENGENHARIA]
[CATEGORIA: 1.1 Arquitetura — integração não conectada]
```
**ACHADO:** `FIIEngine` é instanciada sem provider CVM no app real. Toda a integração CVM para FIIs está inerte em produção.

**LOCAL:** `app.py:158` (`fii = FIIEngine()`); `fii_engine.py:21-23` (`cvm_provider=None` → "CVM desabilitado"); `:26-28` (`_obter_cvm_dados` retorna `None` incondicionalmente).

**PROBLEMA:** O default `None` foi criado para testes ("útil em testes", linha 22) e virou o comportamento de produção. Consequências: o VPA oficial (`valor_cota`) nunca é usado; `pvp` cai para `float(dados.get("pvp", 1.0) or 1.0)` — **default mágico 1,0**, ou seja, um FII sem P/VP conhecido é silenciosamente assumido como negociando exatamente ao valor patrimonial, o que produz score neutro em vez de sinalizar dado ausente.

**CENÁRIO DE FALHA:** FII fora do `FII_CNPJ_MAP` (470 dos ~500 da B3), sem P/VP no yfinance. `pvp = 1.0` → nenhum bônus nem penalidade de P/VP no score → score parece "normal". A UI exibe P/VP 1,00 como se fosse um dado medido. O README anuncia "Dados oficiais da CVM — Informe Mensal para FIIs" e "🏛️ patrimônio líquido e vacância" para uma integração que não roda.

**SEVERIDADE:** ALTO

**CORREÇÃO:** `FIIEngine(CVMFIIProvider())` em `load_engines`. Substituir o default `1.0` por `None` e propagar como campo faltante. Teste de fumaça que verifica que o app instancia todos os engines com suas dependências reais.

**ESFORÇO:** 3 horas.

---

```
[ID: E-11]
[FASE: ENGENHARIA]
[CATEGORIA: 1.7 Dependências]
```
**ACHADO:** `cloudscraper` é o caminho principal do scraper e não está em `requirements.txt`.

**LOCAL:** `fundamentus_scraper.py:13-16, 19-47`; `requirements.txt` (15 linhas, sem cloudscraper).

**PROBLEMA:** Instalação limpa seguindo o README nunca tem cloudscraper. O código cai no `requests.Session`, loga dois warnings e segue. Fundamentus responde 403 a `requests` sem bypass. O fallback documentado como camada 4 da cascata está morto por omissão de dependência.

**CENÁRIO DE FALHA:** Ticker fora do mapa CVM, sem `BRAPI_TOKEN`, com yfinance retornando `pl` mas não `roe`. A cascata deveria completar via Fundamentus; recebe 403 três vezes, `erro_scraper = True`, e o `ValuationEngine` rebaixa a recomendação para `DADOS INSUFICIENTES — AGUARDAR`. O usuário conclui que o ativo não tem dados; na verdade falta um `pip install`.

**SEVERIDADE:** ALTO

**CORREÇÃO:** Decidir explicitamente. Se o scraping continua: declarar a dependência e fixar versão. Se não: remover `fundamentus_scraper.py` e as referências no README (recomendado — ver F-25 sobre ToS).

**ESFORÇO:** 1 hora (declarar) ou 4 horas (remover).

---

```
[ID: E-12]
[FASE: ENGENHARIA]
[CATEGORIA: 1.6 DevOps]
```
**ACHADO:** Não existe CI. Não existe `.github/`. `ruff` é citado em `CLAUDE.md` e liberado em `.claude/settings.json`, mas não está em `requirements.txt` nem tem arquivo de configuração.

**LOCAL:** raiz do repositório (ausência de `.github/workflows/`); `CLAUDE.md:9-10`; `.claude/settings.json` (`"Bash(ruff check *)"`).

**PROBLEMA:** Os 255 testes só rodam se alguém lembrar. Não há gate em PR, apesar do fluxo de trabalho ser baseado em PRs (8 merges no histórico). Sem separação dev/staging/prod: `db_path="sentinela_v6.db"` é literal no construtor, sem variável de ambiente. Logging vai para `sentinela.log` na raiz, em texto não estruturado, sem correlação de execução — é impossível rastrear uma análise completa (`buscar_dados_ticker` → 4 providers → valuation → IA) porque não há request ID. Não há alerta algum para falhas silenciosas.

**CENÁRIO DE FALHA:** Um PR quebra a normalização de DY. Os testes existentes passariam (cobrem `_normalizar_dy` isolado, não a cascata). Nada bloqueia o merge. A regressão só aparece quando o usuário estranhar um número na tela — semanas depois, sem log correlacionado para reconstruir o caminho.

**SEVERIDADE:** ALTO

**CORREÇÃO:** GitHub Actions com `pytest` + `ruff check` + `ruff format --check` + `pip-audit`, obrigatório em PR. `db_path` via env var com default. `structlog` ou `logging` com `extra={"ticker":..., "run_id":...}` e formatter JSON.

**ESFORÇO:** 1 dia.

---

```
[ID: E-13]
[FASE: ENGENHARIA]
[CATEGORIA: 1.2 Qualidade — cobertura de testes]
```
**ACHADO:** A camada de orquestração, a UI e a matemática de carteira têm 0% de cobertura, apesar do badge "255 testes passing".

**LOCAL:** `app.py` (0%, 307 stmts), `auditoria.py` (0%, 578 stmts), `limpar_banco.py` (0%), `database.adicionar_posicao:54-84` (0%), `fundamentus_scraper._limpar_valor:62-85` e `buscar_dados:87-196` (0%).

**PROBLEMA:** Os dois trechos com aritmética financeira direta não testada são justamente os que erram dinheiro: o preço médio ponderado da carteira e o parser de números em formato brasileiro que converte todo fundamento vindo do Fundamentus. `_limpar_valor` tem heurísticas frágeis (`"1.500" → 1500` por contagem de dígitos após o ponto) sem um único caso de teste.

**CENÁRIO DE FALHA:** Fundamentus muda a formatação de "Patrim. Líq" de `35.664.000` para `35.664.000,00`. `_limpar_valor` entra no ramo `',' in v and '.' in v` → remove pontos, troca vírgula → `35664000.00`. Funciona. Mas se mudar para `35,664,000` (formato US), o ramo `',' in v` (sem ponto) troca vírgulas por pontos → `35.664.000` → `float()` levanta `ValueError` → retorna `None` silenciosamente. Campo some da cascata sem erro visível.

**SEVERIDADE:** ALTO

**CORREÇÃO:** Testes parametrizados para `_limpar_valor` (mínimo 15 formatos, incluindo negativos, percentuais, `-`, `N/A`, notação com sufixo B/M). Testes para `adicionar_posicao` cobrindo aporte, aporte adicional, venda parcial e zeragem. Teste de integração de `app.py` via `streamlit.testing.v1.AppTest`.

**ESFORÇO:** 2 dias.

---

```
[ID: E-14]
[FASE: ENGENHARIA]
[CATEGORIA: 1.5 Persistência — modelo de dados]
```
**ACHADO:** A tabela `analises` tem `ticker` como PRIMARY KEY. Só existe uma análise por ativo, sempre sobrescrita. O índice `idx_data` criado para consultas por data é inútil.

**LOCAL:** `database.py:28-34` (schema), `:49-52` (índice), `:113` (`INSERT OR REPLACE`).

**PROBLEMA:** O README anuncia "Persistência SQLite (WAL mode) — Histórico de análises local". Não há histórico. Cada nova análise apaga a anterior. Um índice sobre `data_analise` numa tabela com uma linha por ticker não acelera nada — e o comentário na linha 47 diz "CORRIGIDO: índice idx_data estava ausente desde v10", tratando como bug corrigido algo que é inconsequente dado o schema.

**CENÁRIO DE FALHA:** Sem histórico, é impossível responder "esta recomendação de COMPRA de 3 meses atrás acertou?" — que é exatamente o que `auditar_recomendacoes.py` e o backtest tentam fazer, e por isso precisam recalcular tudo do zero em vez de ler o que já foi produzido.

**SEVERIDADE:** MÉDIO

**CORREÇÃO:** PK composta `(ticker, data_analise)` ou `id AUTOINCREMENT` + índice `(ticker, data_analise DESC)`. Adicionar tabela `schema_version` e migrations — hoje não existe caminho de upgrade e `db_path` está fixo em `sentinela_v6.db` enquanto `APP_VERSION` é `v14`.

**ESFORÇO:** 6 horas.

---

```
[ID: E-15]
[FASE: ENGENHARIA]
[CATEGORIA: 1.4 Resiliência — tratamento de erros]
```
**ACHADO:** 34 blocos `except Exception` fora de `tests/`. Nenhuma falha de integração externa interrompe a análise; todas degradam para um warning em log e um valor de fallback.

**LOCAL:** `market_engine.py` (8), `auditoria.py` (5), `ai_core.py` (5), `config.py` (4), `cvm_provider.py`, `cvm_ticker_map.py`, `fii_engine.py`, `fundamentus_scraper.py`, `portfolio_engine.py`, `auditar_recomendacoes.py`.

**PROBLEMA:** Não há retry, backoff, circuit breaker ou taxonomia de erro. `portfolio_engine:144` captura tudo e devolve `{"erro": f"Erro interno: {e}"}` — a otimização de Markowitz inteira num único `try`. `market_engine:425` engole qualquer falha do yfinance, inclusive `KeyError` por mudança de schema. O resultado é uniforme: o sistema **sempre** produz um número.

**CENÁRIO DE FALHA:** yfinance muda `info['returnOnEquity']` de decimal para percentual (já aconteceu com `dividendYield`). Nenhuma exceção é levantada — o valor simplesmente vira 100x maior. `brapi_provider` tem guard (`roe > 2 → None`), mas o caminho yfinance em `market_engine:409` não tem nenhum. ROE de 21% vira 2100% → `is_growth = True` → Lynch com `g` estourado no cap de 25% → `pl_justo = 35` (cap) → fair value multiplicado. Sem alerta.

**SEVERIDADE:** MÉDIO

**CORREÇÃO:** Substituir por exceções tipadas (`ProviderUnavailable`, `SchemaChanged`, `RateLimited`). Aplicar os mesmos guards de sanidade do `brapi_provider` ao caminho yfinance. Adicionar `tenacity` para retry/backoff nas chamadas HTTP. Circuit breaker por provider com estado exposto na UI.

**ESFORÇO:** 2 dias.

---

```
[ID: E-16]
[FASE: ENGENHARIA]
[CATEGORIA: 1.1 Escalabilidade / 1.4 Concorrência]
```
**ACHADO:** `CVMProvider.calcular_indicadores` reparseia os CSVs completos do ZIP a cada invocação, e `peers_engine` invoca até 8 dessas em paralelo.

**LOCAL:** `cvm_provider.py:145-201` (loop chama `_parsear_com_cvm` 3x por ano), `peers_engine.py:46-48` (`ThreadPoolExecutor(max_workers=MAX_WORKERS)`), `config.py:32` (`MAX_WORKERS = min(8, cpu_count+4)`).

**PROBLEMA:** Cada `_parsear_com_cvm` faz `pd.read_csv(dtype=str, low_memory=False)` sobre BPA/BPP/DRE consolidados de todas as companhias abertas do Brasil — centenas de milhares de linhas — para extrair **8 valores** de uma única empresa. Não há cache do DataFrame parseado, nem filtro na leitura. O `self.cvm` é compartilhado entre threads sem nenhum estado protegido.

**CENÁRIO DE FALHA:** Análise de PETR4 → `peers_engine.comparar` dispara 4 peers em paralelo → 4 threads × 3 parses completos = 12 leituras concorrentes dos mesmos CSVs. Pico de memória de vários GB, dezenas de segundos de CPU. Em 10x o volume (40 peers), o processo morre por OOM.

**SEVERIDADE:** MÉDIO

**CORREÇÃO:** Converter os ZIPs para Parquet particionado por `CD_CVM` na primeira leitura e consultar o Parquet depois. Alternativa mais barata: `@lru_cache` no DataFrame parseado por `(zip_path, tipo)` com `usecols` restrito e `dtype` explícito. Ganho estimado: 2 ordens de grandeza.

**ESFORÇO:** 1,5 dia.

---

```
[ID: E-17]
[FASE: ENGENHARIA]
[CATEGORIA: 1.4 Resiliência — timeouts incompatíveis]
```
**ACHADO:** O timeout global do `peers_engine` (10s) é menor que o tempo mínimo que o rate-limit do scraper impõe para o mesmo conjunto de peers.

**LOCAL:** `peers_engine.py:53` (`as_completed(futures, timeout=10)`), `:55` (`future.result(timeout=2)`); `fundamentus_scraper.py:88-97` (lock global, espera 2,0-2,5s por request).

**PROBLEMA:** O `_lock` serializa todas as threads. Com 4 peers que precisem do Fundamentus, o tempo mínimo é 4 × 2,5s = 10s — só no rate limit, antes de qualquer HTTP, CVM ou yfinance. `future.result(timeout=2)` é ainda mais agressivo: mesmo um future já concluído por `as_completed` pode estourar se houver contenção.

**CENÁRIO DE FALHA:** O painel "Comparação Setorial" exibe "Sem peers" na maioria das execuções que dependam do scraper, e a causa aparece apenas como `logger.warning("Peer X ignorado")`. O usuário conclui que o setor não tem dados.

**SEVERIDADE:** MÉDIO

**CORREÇÃO:** Dimensionar o timeout a partir do rate limit (`n_peers × espera + margem`). Remover `future.result(timeout=2)` — redundante após `as_completed`. Reportar na UI quantos peers foram coletados de quantos tentados.

**ESFORÇO:** 3 horas.

---

```
[ID: E-18]
[FASE: ENGENHARIA]
[CATEGORIA: 1.3 Segurança — input não sanitizado]
```
**ACHADO:** O ticker digitado pelo usuário não passa por nenhuma validação e é interpolado diretamente em URL e em prompt de LLM.

**LOCAL:** `app.py:193` (`st.text_input("Ticker:").upper().strip()`), `fundamentus_scraper.py:99` (`f"...detalhes.php?papel={ticker}"`), `ai_core.py:121` (`f"...ativo {ticker}..."`), `market_engine.py:366` (`yf.Ticker(f"{ticker}.SA")`).

**PROBLEMA:** Sem regex de formato (`^[A-Z]{4}\d{1,2}$`), sem `urllib.parse.quote`, sem limite de comprimento. As queries SQL são parametrizadas corretamente (`database.py` usa `?` em todos os casos — isso está certo), mas a URL e o prompt não têm proteção equivalente. O prompt de `_montar_prompt` também despeja o dicionário `dados` inteiro (`_formatar_dados`, linhas 63-71), que inclui conteúdo derivado de HTML scrapeado.

**CENÁRIO DE FALHA:** Local, o risco é baixo. Com o item "Deploy público (Streamlit Community Cloud)" do roadmap, vira injeção de parâmetro em requisição de saída e prompt injection de terceiros contra a chave Groq/Gemini do dono da aplicação, com custo e rate limit no cartão dele.

**SEVERIDADE:** MÉDIO (ALTO se o deploy público sair)

**CORREÇÃO:** Validar com regex antes de qualquer uso; `urllib.parse.quote` na URL; delimitar os dados no prompt com marcadores e instrução explícita de que o conteúdo é dado, não instrução; limite de 10 caracteres no input.

**ESFORÇO:** 3 horas.

---

```
[ID: E-19]
[FASE: ENGENHARIA]
[CATEGORIA: 1.7 Dependências — semântica variável por versão]
```
**ACHADO:** `auto_adjust` do yfinance não é fixado no app, e o backtest usa o valor oposto ao da produção.

**LOCAL:** `market_engine.py:368` (`tk.history(period="1y", timeout=10)` — sem `auto_adjust`), `backtesting/backtest_engine.py:57` (`auto_adjust=False` explícito); `requirements.txt` (`yfinance>=0.2.50,<0.3.0`).

**PROBLEMA:** O default de `auto_adjust` mudou dentro da faixa de versões permitida. Sem pin, `hist['Close']` significa preço ajustado ou preço bruto conforme o patch resolvido no `pip install` do dia. Isso muda a semântica de: `preco_atual`, todos os indicadores técnicos, as bandas de Bollinger, o ATR e os retornos da otimização Markowitz. O backtest usa a convenção contrária à do app, então backtest e produção não avaliam o mesmo objeto.

**CENÁRIO DE FALHA:** Dois desenvolvedores (ou o mesmo dev antes e depois de um `pip install -U`) obtêm MA200, RSI e Sharpe diferentes para o mesmo ticker no mesmo dia, sem nenhuma mudança de código. Impossível reproduzir um bug relatado.

**SEVERIDADE:** MÉDIO

**CORREÇÃO:** Passar `auto_adjust=True` explicitamente em todos os pontos e alinhar o backtest. Fixar `yfinance==` versão exata. Adicionar `requirements.lock` (hoje inexistente) gerado por `pip-compile`.

**ESFORÇO:** 2 horas.

---

```
[ID: E-20]
[FASE: ENGENHARIA]
[CATEGORIA: 1.2 Código duplicado com divergência semântica]
```
**ACHADO:** Dois parsers CVM quase idênticos, um dos quais **não** aplica a escala monetária. O testado é o que a produção não usa.

**LOCAL:** `cvm_provider.py:89-108` (`parsear_demonstrativo`, público, sem `ESCALA_MOEDA`) e `:110-128` (`_parsear_com_cvm`, privado, com `× 1000` para "MIL").

**PROBLEMA:** Divergem em 4 linhas e em um fator de 1000. `tests/test_cvm_provider.py` testa exclusivamente o método público — que nenhum código de produção chama. O método realmente usado só é exercitado indiretamente.

**CENÁRIO DE FALHA:** Um desenvolvedor futuro usa o método público (é o único com docstring e testes) para uma nova feature. Todo valor monetário sai 1000x menor. O ROE, sendo um quociente, permanece correto — então metade dos números fica certa e metade errada, o que é pior que tudo errado.

**SEVERIDADE:** MÉDIO

**CORREÇÃO:** Eliminar `parsear_demonstrativo`; expor apenas um parser com `include_cd_cvm: bool = True`. Redirecionar os testes.

**ESFORÇO:** 2 horas.

---

```
[ID: E-21]
[FASE: ENGENHARIA]
[CATEGORIA: 1.1 Arquitetura — migração incompleta]
```
**ACHADO:** O pacote `sentinela/` (Clean Architecture) está implementado, testado e desconectado.

**LOCAL:** `sentinela/services/analyze_asset.py`, `sentinela/repositories/analysis_repository.py`; consumidores: apenas `tests/test_analysis_service.py` e `tests/test_analysis_repository.py`.

**PROBLEMA:** `AnalysisService.analyze` (117 linhas, 96% coberto) duplica linha a linha a orquestração de `app.py:200-235` (0% coberto). `AnalysisRepository` (286 linhas, 90% coberto) duplica `DatabaseManager` (58% coberto). Manter os dois é garantia de divergência: qualquer correção precisa ser feita duas vezes, e a versão testada não é a que roda.

**CENÁRIO DE FALHA:** A correção do achado sobre `dados.update(analise)` é aplicada em `AnalysisService` (onde há testes que a validam) e esquecida em `app.py`. A suíte fica verde, o bug continua em produção.

**SEVERIDADE:** MÉDIO

**CORREÇÃO:** Concluir a migração numa única passada: `app.py` passa a chamar `AnalysisService` e a renderizar `AnalysisResult`. Remover `DatabaseManager` em favor de `AnalysisRepository`, ou o contrário — mas escolher um. Não deixar a migração parada por mais um ciclo.

**ESFORÇO:** 2 dias.

---

```
[ID: E-22]
[FASE: ENGENHARIA]
[CATEGORIA: 1.4 Resiliência — concorrência no cliente de IA]
```
**ACHADO:** O executor do Gemini tem 1 worker e `future.cancel()` não interrompe uma chamada já em execução.

**LOCAL:** `ai_core.py:35` (`ThreadPoolExecutor(max_workers=1)`), `:158-168`.

**PROBLEMA:** Após `FuturesTimeout` em 15s, `future.cancel()` retorna `False` para um future em execução — a thread continua ocupada até a requisição HTTP terminar por conta própria (sem timeout no cliente `google-genai`). Como o executor é criado uma vez e cacheado via `@st.cache_resource`, a próxima chamada ao Gemini fica na fila atrás da anterior e estoura o timeout também.

**CENÁRIO DE FALHA:** Groq indisponível, Gemini lento. A primeira análise espera 15s e cai para Ollama. Da segunda em diante, o Gemini "falha" por head-of-line blocking mesmo se voltar a responder rápido. O usuário vê "Ollama Local" ou "IA Indisponível" permanentemente até reiniciar o app.

**SEVERIDADE:** MÉDIO

**CORREÇÃO:** Usar o timeout nativo do SDK em vez de um executor. Se o executor for mantido, dimensionar workers e descartar/recriar após timeout.

**ESFORÇO:** 3 horas.

---

**Achados de menor severidade — Engenharia**

| # | Categoria | Achado | Local | Sev. | Correção | Esforço |
|---|---|---|---|---|---|---|
| E-23 | 1.5 Cache | `_ALIAS` mapeia `fundamentals_cache` → `fundamentus` (confiança 40), tornando a entrada `"cache": 30` inalcançável. Dado em cache é pontuado como coleta fresca. | `data_quality.py:45-58` | BAIXO | Remover o alias; manter `cache` como fonte própria | 1h |
| E-24 | 1.2 Bug lógico | RSI retorna 50 quando não há perdas na janela (`loss=0` → `NaN` → `fillna(50)`). O valor correto é 100. | `technical_engine.py:22-23` | BAIXO | `rsi = 100` quando `loss == 0 and gain > 0` | 1h |
| E-25 | Change Preventer | Vacância duplicada: `FII_MANUAL_FALLBACK` (config) e `VACANCIA_CONHECIDA` (fii_engine), mesmos tickers, mesmos valores, sem sincronização | `config.py:73-77`, `fii_engine.py:10-17` | BAIXO | Fonte única em `config` | 1h |
| E-26 | 1.5 Persistência | `db_path="sentinela_v6.db"` literal vs `APP_VERSION="v14"`; sem migrations nem `schema_version` | `database.py:15`, `config.py:23` | BAIXO | Env var + tabela de versão | 3h |
| E-29 | 1.3 Segurança | Sem autenticação e sem conceito de usuário: `carteira_real` é global. Bloqueia o item "Deploy público" do roadmap | `database.py:35-40`, `app.py:405-470` | BAIXO (hoje) / CRÍTICO (se deploy) | Não publicar sem auth + escopo por usuário | — |
| E-30 | Dispensables | Código morto confirmado: `baixar_itr`, `parsear_demonstrativo`, `cost_of_equity_real`, `ntnb_longa`, `cdi`, `ipca_12m`, `dy_mes_decimal`, `_FONTE_CONFIANCA["cache"]`, filtro `p > 0.01` | vários | BAIXO | Conectar ou remover (ver F-3) | — |
| E-27 | Documentação | `CLAUDE.md` lista como "bugs conhecidos, não corrija sem baseline" quatro itens **já corrigidos**; a seção Arquitetura não menciona `sentinela/`, `cvm_*`, `data_quality`, `backtesting`; diz "tests/ (sendo criada agora)" | `CLAUDE.md:24,29-31,45-49` | COSMÉTICO | Reescrever com o estado real | 1h |
| E-28 | Documentação | README: "brapi — cotação preferencial"; o código só usa preço da brapi se yfinance falhar (`market_engine.py:453`) | `README.md`, `market_engine.py:327-342` | COSMÉTICO | Corrigir o diagrama de cascata | 30min |

---

# FASE 2 — AUDITORIA FINANCEIRA E METODOLÓGICA

## 2.1 Fontes de dados — mapa real

| Fonte | Latência | Oficial? | Risco de vendor único |
|---|---|---|---|
| yfinance `history(period="1y")` | Fechamento D-1 | Não (Yahoo, sem SLA) | **Alto** — é o único caminho efetivo de preço e o único de `sharesOutstanding` |
| brapi | Tempo real | Não (terceiro, BR) | Desabilitado sem token; sem token o README fica falso |
| CVM DFP | Anual, DFP do ano-1 | **Sim** | Cobertura ~50 tickers |
| CVM Informe Mensal FII | Mensal, D+30 | **Sim** | 30 FIIs mapeados; e não é chamado em produção (E-10) |
| BCB SGS 432/12/433 | Diário | **Sim** | Único; fallback hardcoded |
| Tesouro Direto JSON | Diário | **Sim** | Não consumido por nada (F-3) |
| Fundamentus (scraping) | Indefinida | Não | Quebrado por dependência ausente (E-11) |

**Reconciliação entre fontes: inexistente.** Quando CVM, brapi e yfinance fornecem o mesmo campo, o último a escrever vence (`overwrite=True`) e os valores anteriores são descartados sem comparação. A `field_provenance` registra qual fonte venceu, não que houve divergência.

**Latência real do preço:** `preco_atual` vem de `hist['Close'].iloc[-1]` — fechamento do pregão anterior. Todo `upside` é calculado contra um preço D-1 e apresentado como "Preço" sem qualquer carimbo temporal.

---

## ACHADOS — FINANCEIRO

---

```
[ID: F-1]
[FASE: FINANCEIRO]
[CATEGORIA: 2.4 Backtesting — look-ahead bias]
```
**ACHADO:** Os "fundamentos point-in-time" do backtest são 15 linhas inventadas para 3 tickers, retro-estimadas a partir de dados de hoje. O próprio README do backtest afirma as duas coisas contraditórias em linhas consecutivas.

**LOCAL:** `backtesting/fundamentos_point_in_time.csv` (16 linhas incluindo header); `backtesting/README_BACKTEST.md:10-12`.

> "Valores historicos **estimados via comparacao com dados atuais**"
> "**Sem lookahead bias**: fundamentos limitados a data efetiva da analise"

**PROBLEMA:** Estimar valores passados a partir dos atuais **é** look-ahead bias, na sua forma mais direta. O gate de data em `simular_analise_mensal` (que está corretamente implementado, `backtest_engine.py:110-127`) impede o vazamento de **preço**, não de fundamento — e o vazamento está embutido no dado de entrada.

Inspeção dos valores confirma fabricação: PETR4 P/L = 5,20 / 5,40 / 5,60 / 5,70 / 5,77 — monotônico, suavizado, sem um único trimestre atípico em 2,3 anos. ITUB4 traz `divida_liq_ebitda = 1,30`, métrica sem significado para um banco. VALE3 aparece com P/L entre 18,5 e 21,6 no período — a Vale negociou na faixa de 5-8x. Não são observações históricas.

**CENÁRIO DE FALHA:** O backtest é a **única** validação empírica de toda a metodologia do projeto. Ele não valida nada. Pior: produz um artefato commitado (`backtest_results_v1.csv`) e um README com percentuais de acurácia, que dão a aparência de evidência. Ao retomar o projeto, é a primeira coisa que alguém consultaria para decidir o que mudar — e ela aponta na direção errada.

**SEVERIDADE:** CRÍTICO

**CORREÇÃO:** Deletar o CSV sintético do repositório. Construir fundamentos point-in-time reais a partir do que já existe: os ZIPs DFP/ITR da CVM **são** point-in-time por construção (têm `DT_REFER` e data de entrega). Usar `DT_ENTREGA` como data de disponibilidade, nunca `DT_REFER`. Enquanto o dataset real não existir, `README_BACKTEST.md` deve dizer em uma linha que o backtest não está validado.

**ESFORÇO:** 3-4 dias para o pipeline point-in-time via CVM.

---

```
[ID: F-2]
[FASE: FINANCEIRO]
[CATEGORIA: 2.4 Backtesting — resultado ignorado]
```
**ACHADO:** O backtest commitado reporta acurácia geral de 46,7%, COMPRA 25%, VENDA 16,7%, Graham 0%. Nenhuma correção metodológica foi feita em resposta, e o README principal não menciona esses números.

**LOCAL:** `backtesting/README_BACKTEST.md:16-27`; `backtesting/backtest_results_v1.csv`.

**PROBLEMA:** Três defeitos estatísticos além do dado fabricado:

1. **N inútil.** 15 casos avaliados, 72 ignorados. Quatro observações de COMPRA e seis de VENDA. Um intervalo de confiança de 95% sobre 4 tentativas vai de ~1% a ~70%. Nada é distinguível de sorte.
2. **NEUTRO tem 100% por construção.** O critério é `abs(retorno_real) < 0.10` em 90 dias — satisfeito pela maioria dos ativos na maioria das janelas. É o único bucket com teste trivial, e é o único com acurácia alta.
3. **Observações de horizonte zero contam.** `alvo = min(data_preco + 90d, end_date)` (`backtest_engine.py:180-183`). Nas três linhas com `data_analise = 2026-05-04` (= `end_date`), `data_futura == data_analise` e `retorno_real = 0.0`. Essas linhas entram nas estatísticas: PETR4 NEUTRO conta como acerto (|0| < 0,10), ITUB4 COMPRA e VALE3 VENDA contam como erro. Três das quinze observações são vácuo estatístico com sinal determinado pela recomendação, não pelo mercado.

**CENÁRIO DE FALHA:** Adicionalmente, `backtest_results_v1.csv` contém a string de risco `'ALTA DIVERGENCIA 127% entre metodos'`, que **não existe mais no código** (o texto atual é `"Métodos divergentes"`, `valuation_engine.py:148`). O CSV foi gerado por uma versão anterior do engine e está commitado como se descrevesse o comportamento atual. Não é reproduzível a partir do HEAD.

**SEVERIDADE:** CRÍTICO

**CORREÇÃO:** Excluir observações com horizonte < 60 dias. Definir o critério de NEUTRO simetricamente aos demais (ex.: retorno dentro de ±1 desvio-padrão do ativo). Regenerar tudo a partir do HEAD e registrar o commit hash no CSV. Reportar N e intervalo de confiança junto de cada percentual — um número de acurácia sem N é desinformação.

**ESFORÇO:** 1 dia (após o dataset real existir).

---

```
[ID: F-3]
[FASE: FINANCEIRO]
[CATEGORIA: 2.2 Metodologia — camada macro inerte]
```
**ACHADO:** Toda a camada macro dinâmica — NTN-B longa, CDI, IPCA 12m, `cost_of_equity_real()` — tem **zero consumidores em produção**. Grep confirma: as únicas referências fora de `config.py` estão em `tests/test_macro_context.py`.

**LOCAL:** `config.py:212-239, 243-304`; consumidores: `tests/test_macro_context.py` apenas.

**PROBLEMA:** O README dedica uma linha de destaque ("📡 Macro context dinâmico — Selic, CDI, IPCA 12m e yield real NTN-B buscados ao vivo"), uma linha na tabela de stack, um bloco no diagrama de arquitetura e um ✅ no roadmap. Nenhum desses valores toca em um único cálculo. `valuation_engine` usa `get_selic_atual()`. `fii_engine` usa `get_selic_atual()`. `portfolio_engine` usa `get_selic_atual()`. O PR #6 entregou um pipeline de dados sem consumidor — e o PR #8 (marcado 🔄 no roadmap: "NTN-B longa como taxa de desconto no Gordon") é justamente a ligação que nunca foi feita.

**CENÁRIO DE FALHA:** Ao retomar, a leitura do README sugere que os parâmetros macro estão integrados e que falta apenas trocar a taxa do Gordon. A realidade é que 90 linhas de fetchers, cada uma com sua própria chamada HTTP e fallback, existem sem efeito. Qualquer avaliação de "o que o projeto faz hoje" baseada no README superestima a base entregue.

**SEVERIDADE:** CRÍTICO (de honestidade de estado — é a distorção que mais compromete a retomada)

**CORREÇÃO:** Decisão binária, agora: (a) conectar ao Gordon com a correção real/nominal do achado F-6, ou (b) remover os fetchers e o texto do README. Não manter mais um ciclo em estado intermediário. Se (a), 15 dos 255 testes passam a testar código vivo em vez de código morto.

**ESFORÇO:** 2 dias com (a) feito corretamente.

---

```
[ID: F-4]
[FASE: FINANCEIRO]
[CATEGORIA: 2.2 Metodologia — taxa de desconto / duração]
```
**ACHADO:** Gordon desconta uma perpetuidade usando a taxa de política monetária de curtíssimo prazo como livre de risco. Em regime de Selic alta, o modelo só consegue produzir sinal de venda.

**LOCAL:** `valuation_engine.py:120-130`; `config.py:159-163`.

**PROBLEMA:** `k = Selic + 7%`. A Selic é a taxa overnight; o fluxo descontado é perpétuo. Descasamento de duração de manual. Com Selic 14,75%: `k = 21,75%`, `g` limitado a 8%, logo `k − g ≥ 13,75%`.

Álgebra do upside: `FV = DPS × (1+g)/(k−g)` e `DPS = DY × P`, então
`upside = DY × (1+g)/(k−g) − 1`.
Com `g = 8%`: upside > 0 exige **DY > 12,73%**. Com `g = 0` (payout alto): **DY > 21,75%**.

O gate de entrada do método é `DY > 4%`. Ou seja, para toda ação com DY entre 4% e 12,7% — que é praticamente todo o universo pagador da B3 — o Gordon produz, por construção algébrica, um fair value abaixo do preço. Não é uma conclusão sobre o ativo; é uma identidade dos parâmetros.

**CENÁRIO DE FALHA:** No `backtest_results_v1.csv`, PETR4 recebe Gordon de R$ 29,32 / 23,58 / 24,99 / 20,56 / 31,42 contra preços de 38,58 / 34,68 / 38,10 / 32,53 / 49,34. Cinco de cinco abaixo do preço, sem exceção, ao longo de 2,3 anos. Combinado com o Bazin (mesma dinâmica, achado seguinte), a mediana de três métodos é puxada para baixo de forma sistemática — e o sistema emite VENDA e NEUTRO como estado natural, não como leitura do mercado.

**SEVERIDADE:** ALTO

**CORREÇÃO:** Usar taxa longa como livre de risco: `k_nominal = (1 + NTNB_real)(1 + IPCA_esperado) − 1 + prêmio`. `MacroContext` já tem `ntnb_longa` e `ipca_12m` — é exatamente para isso que existem (F-3). Documentar o prêmio de 7% com fonte (hoje é literal sem justificativa). Adicionar teste de sensibilidade: para uma grade Selic × DY, quantos ativos o método consegue classificar como subavaliados? Se a resposta for zero para faixas plausíveis, o modelo está mal parametrizado.

**ESFORÇO:** 1 dia + validação metodológica.

---

```
[ID: F-5]
[FASE: FINANCEIRO]
[CATEGORIA: 2.2 Metodologia — Bazin descaracterizado]
```
**ACHADO:** Bazin foi reformulado como `DY / Selic`, colapsando em uma comparação de renda fixa. O preço cancela e o método perde o teto de preço que o caracteriza.

**LOCAL:** `valuation_engine.py:102-107`.

**PROBLEMA:** `FV = (DY × P) / max(Selic, 5%)`, logo `upside = DY / max(Selic, 5%) − 1`. **O preço cancela.** O resultado não depende de quanto o ativo custa — só da razão entre yield e Selic. Com Selic 14,75%, upside > 0 exige DY > 14,75%, e o gate de entrada exige DY ≥ 5%. Na faixa 5%-14,75%, Bazin **sempre** aponta sobrevalorização.

Metodologicamente: Décio Bazin usava taxa-alvo **fixa** (6%), precisamente para que o preço-teto fosse um ancoradouro estável ao longo dos ciclos. Trocar por Selic transforma o método num comparador de carrego que muda de veredito quando o Copom se mexe, sem que nada tenha mudado na empresa. O `max(Selic, 5%)` protege só o lado de baixo; não há teto.

**CENÁRIO DE FALHA:** Empresa paga DY estável de 8% por três anos. Selic sobe de 10,5% para 14,75%. O "preço justo Bazin" cai 29% sem nenhuma mudança de fundamento, dividendo ou preço. Se a Selic voltar a 9%, a mesma empresa vira COMPRA. O sistema está medindo o Copom e reportando como análise do ativo.

**SEVERIDADE:** ALTO

**CORREÇÃO:** Decidir a intenção. Se é Bazin: taxa-alvo fixa (6-8%), configurável, com justificativa registrada. Se é comparação de carrego: renomear o método na UI (não é Bazin) e **adicionar o prêmio de risco de ações** — comparar dividendo de renda variável com taxa livre de risco sem prêmio já força subavaliação estrutural. Em qualquer caso, documentar que o preço cancela e que a saída em R$ é o preço reescalado, não uma avaliação independente.

**ESFORÇO:** 4 horas de código; a decisão metodológica é o trabalho real.

---

```
[ID: F-6]
[FASE: FINANCEIRO]
[CATEGORIA: 2.2 Metodologia — armadilha na correção planejada]
```
**ACHADO:** A correção do roadmap ("NTN-B longa como taxa de desconto no Gordon") introduz erro de mistura real/nominal se aplicada como está desenhada.

**LOCAL:** `config.py:237-239` (`cost_of_equity_real() = ntnb_longa + GORDON_PREMIO_RISCO`); `valuation_engine.py:127` (`k = selic + PREMIO`), `:123-126` (`g = ROE × retenção`), `:129` (`div_prox = dy × p × (1+g)`).

**PROBLEMA:** O nome do método é honesto: `cost_of_equity_real` retorna uma taxa **real** (NTN-B é yield real + prêmio). Mas `div_prox` é um dividendo **nominal** e `g = ROE × retenção` é crescimento **nominal** (ROE contábil embute inflação). Substituir `k` nominal por `k` real sem converter os demais termos mistura regimes e infla o fair value.

**CENÁRIO DE FALHA:** Com Selic 14,75% e NTN-B real 7%: `k` cai de 21,75% para 14%. Com `g = 8%` nominal, `k − g` cai de 13,75% para 6%. `FV = DPS × 1,08 / 0,06` — o fair value **mais que dobra** (fator 2,29) para todo ativo que passe no gate. O projeto sairia de um viés sistemático de venda para um viés sistemático de compra, e o commit seria descrito como "usar taxa de desconto correta". Erro silencioso de resultado, exatamente a classe de risco de maior prioridade.

**SEVERIDADE:** ALTO

**CORREÇÃO:** Escolher um regime e manter consistência em todos os termos.
- Regime real: `k_real = NTNB + prêmio`; `g_real = (1 + g_nominal)/(1 + IPCA_esperado) − 1`; `DPS_real = DPS`.
- Regime nominal: `k_nom = (1 + NTNB)(1 + IPCA_esperado) − 1 + prêmio`; `g_nom` como está.
O segundo é menos invasivo. Adicionar teste que verifica que ambos os regimes produzem o mesmo FV para o mesmo cenário (dentro de tolerância) — é o único jeito de garantir que a conversão está certa.

**ESFORÇO:** 1 dia + revisão metodológica.

---

```
[ID: F-7]
[FASE: FINANCEIRO]
[CATEGORIA: 2.2 Metodologia — especificidade B3: JCP]
```
**ACHADO:** Juros sobre Capital Próprio não são tratados em lugar nenhum. Para bancos e utilities brasileiras, JCP é o veículo dominante de distribuição, e o `dividendYield` do Yahoo tipicamente o exclui.

**LOCAL:** todo o pipeline de DY (`market_engine.py:377-379`, `brapi_provider.py:151-154`, `valuation_engine.py:45-46, 102, 111-118, 122`).

**PROBLEMA:** DY subestimado propaga em cadeia com sinais opostos:
- **Bazin** (gate DY ≥ 5%): bancos que distribuem 7-8% via JCP+dividendos aparecem com 1-2% e são **excluídos** do método de renda.
- **Perfil**: `is_growth = ROE > 20% and DY < 4%` — DY artificialmente baixo empurra bancos para o perfil CRESCIMENTO.
- **Lynch**: `payout = (DY × P)/LPA` subestimado → `retenção` superestimada → `g = ROE × retenção` inflado → `PL_justo = 1,5 × g × 100` inflado.

**CENÁRIO DE FALHA — com números do próprio backtest commitado:** ITUB4 em 2026-05-04, preço R$ 42,40, P/L 10,81, ROE 21,01%, DY **1,27%**.
`LPA = 42,40/10,81 = 3,92`. `payout = (0,0127 × 42,40)/3,92 = 13,7%`. `retenção = 86,3%`. `g = 0,2101 × 0,863 = 18,1%`. `PL_justo = 1,5 × 18,1 = 27,2`. `Lynch = 3,92 × 27,2 = ` **R$ 106,64** — um banco avaliado a 27x lucro porque o modelo acredita que ele retém 86% do resultado. Com o payout real (~60% incluindo JCP): `retenção = 40%`, `g = 8,4%`, `PL_justo = 12,6`, `Lynch ≈ R$ 49` — um terço do valor.

O CSV commitado mostra COMPRA para ITUB4 em quatro datas consecutivas com upside de +73% a +77%, e três dessas quatro foram classificadas como erro na validação. O sintoma já está documentado no repositório; a causa não foi diagnosticada.

**SEVERIDADE:** ALTO

**CORREÇÃO:** Obter proventos totais (dividendos + JCP) de fonte que os separe — a B3 publica; o campo `dividends` do yfinance para tickers `.SA` frequentemente já inclui JCP líquido, o que **também** precisa ser verificado (JCP bruto vs líquido de 15% IRRF muda o payout em 15%). `REQUER VALIDAÇÃO`: reconciliar DY calculado contra o informe de proventos da B3 para 5 bancos antes de escolher a fonte. Enquanto isso, bloquear Lynch para o setor financeiro.

**ESFORÇO:** 2 dias.

---

```
[ID: F-8]
[FASE: FINANCEIRO]
[CATEGORIA: 2.2 Metodologia — Graham com LPA fabricado]
```
**ACHADO:** O piso de P/L 7 substitui o LPA real por `preço/7` para todo ativo de múltiplo baixo, e nesse regime o fair value passa a depender do preço.

**LOCAL:** `valuation_engine.py:87` (`pl_graham = max(pl, 7.0)`), `:94-95`; `config.py:145`.

**PROBLEMA:** Quando `P/L > 7`: `FV = √(22,5 × LPA × VPA)` — independente de preço, correto. Quando `P/L < 7`: `lpa_adj = P/7` e `FV = √(22,5 × P/7 × VPA)` — o LPA usado não é o da empresa, é uma função do preço de mercado.

O README justifica: "empresas cíclicas frequentemente apresentam P/L muito baixo no pico do ciclo". Mas o piso não distingue cíclicas de nada. P/L abaixo de 7 na B3 é o estado normal de bancos (ITUB4, BBAS3, BBDC4), petróleo (PETR4), siderurgia (GGBR4, CSNA3) e boa parte das elétricas — em qualquer ponto do ciclo. O ajuste desenhado para uma exceção é aplicado à maioria.

**CENÁRIO DE FALHA:** BBAS3 com P/L 4,5 (múltiplo estrutural do setor, não pico de ciclo). O sistema descarta o LPA real e usa `P/7`, reduzindo o LPA em 36%. Graham cai 20% (raiz quadrada). O ativo é sistematicamente subavaliado por pertencer a um setor de múltiplo baixo — um viés setorial embutido apresentado como conservadorismo. Combinado com Bazin e Gordon (que também penalizam), a mediana dos três métodos é estruturalmente baixa para todo o setor bancário.

**SEVERIDADE:** ALTO

**CORREÇÃO:** Substituir o piso global por normalização de LPA por média de 5-7 anos (o `CVMProvider.calcular_indicadores(anos=5)` já suporta — hoje é chamado com `anos=1`, `market_engine.py:488`). Isso é o tratamento correto de ciclicidade e resolve o problema real sem penalizar setores de múltiplo estruturalmente baixo. É o item "5-year CVM data consistency scoring" que já está no backlog.

**ESFORÇO:** 1,5 dia (a infraestrutura existe).

---

```
[ID: F-9]
[FASE: FINANCEIRO]
[CATEGORIA: 2.2 Metodologia — FII sem ancoragem patrimonial]
```
**ACHADO:** O fair value de FII é `preço × DY_efetivo / Selic_líquida`. O preço cancela e o valor patrimonial não entra no cálculo.

**LOCAL:** `fii_engine.py:106-107`.

**PROBLEMA:** `upside = DY_efetivo / (Selic × 0,85) − 1`. O P/VP é calculado (linhas 76-80) e usado **só** no score (116-121), nunca no fair value. Consequências:
- Dois FIIs com o mesmo DY recebem upside idêntico, um negociando a P/VP 0,7 e outro a 1,4.
- Não há distinção entre tijolo, papel, híbrido, desenvolvimento e FOF em nenhum cálculo — apesar do README afirmar que há (os comentários de categoria em `config.py:41-53` estão inclusive **errados**: HGLG11 é logística e está listado sob "Papel (CRI/CRA)"; KNIP11 e HGCR11 são de papel e estão sob "Tijolo"; BCFF11 é FOF).
- Não há qualidade de crédito, prazo, indexador (IPCA+ vs CDI+) ou inadimplência para fundos de papel — nem duração para fundos de desenvolvimento.
- Com Selic 14,75%: `Selic_líquida = 12,54%`; upside > 0 exige DY efetivo > 12,54%. O universo inteiro de FIIs de tijolo (DY 8-10%) recebe VENDA por construção.

**CENÁRIO DE FALHA:** Um FII de papel com DY 13% sustentado por CRIs high yield inadimplentes e um FII de lajes AAA com DY 9% e P/VP 0,75 recebem, respectivamente, COMPRA e VENDA. O primeiro tem risco de crédito não modelado; o segundo tem 25% de margem sobre patrimônio, ignorada.

**SEVERIDADE:** ALTO

**CORREÇÃO:** Fair value de FII precisa de duas pernas: renda (yield vs benchmark ajustado a risco, não Selic pura) **e** patrimônio (VPA oficial da CVM, que já é buscado e descartado — E-10). Segmentar o benchmark por tipo de fundo: papel indexado a CDI+ compara com CDI, tijolo compara com NTN-B + prêmio imobiliário. Corrigir a classificação em `config.py`.

**ESFORÇO:** 3 dias + decisão metodológica prévia.

---

```
[ID: F-10]
[FASE: FINANCEIRO]
[CATEGORIA: 2.2 Metodologia FII — dupla contagem]
```
**ACHADO:** `dy_efetivo = dy × (1 − vacância)` desconta a vacância de um DY que já a reflete. E aplica vacância física a fundos de papel, que não têm imóveis.

**LOCAL:** `fii_engine.py:97-100`; `VACANCIA_CONHECIDA` (linhas 10-17); `config.FII_MANUAL_FALLBACK` (73-77).

**PROBLEMA:** O DY reportado deriva de rendimentos **efetivamente distribuídos**. Se o fundo está 25% vago, os aluguéis já vieram menores e o DY já está deprimido. Multiplicar por `(1 − 0,25)` desconta a mesma vacância uma segunda vez.

Pior: dos cinco tickers em `VACANCIA_CONHECIDA`, **CVBI11 (VBI CRI) e MXRF11 (Maxi Renda) são fundos de papel** — carteiras de CRI, sem vacância física. Atribuir-lhes 25% e 5% de vacância é aplicar um conceito de outra classe de ativo.

**CENÁRIO DE FALHA:** CVBI11 com DY 10% (valor do próprio `FII_MANUAL_FALLBACK`). `dy_efetivo = 0,10 × 0,75 = 7,5%`. `preco_justo = P × 0,075/0,1254 = 0,598 × P` → **upside −40%** → VENDA, e ainda `score −= int(100 × 0,25) = −25` pela regra de vacância > 15%. Um fundo de CRI recebe penalização dupla por uma vacância imobiliária que ele não tem e que, se tivesse, já estaria no DY.

**SEVERIDADE:** ALTO

**CORREÇÃO:** Remover o ajuste multiplicativo. Vacância é sinal **prospectivo** (risco de queda futura do rendimento) e pertence ao score ou a um cenário, nunca ao DY realizado. Aplicar apenas a fundos de tijolo. Remover as entradas de fundos de papel dos dois dicionários. Documentar a data de coleta de cada estimativa manual — hoje o comentário diz "revisar periodicamente" sem data alguma.

**ESFORÇO:** 4 horas.

---

```
[ID: F-11]
[FASE: FINANCEIRO]
[CATEGORIA: 2.3 Modelagem de risco — ausência total]
```
**ACHADO:** Não existe nenhuma medida de risco no valuation. Sem volatilidade, sem VaR/CVaR, sem stress test, sem gate de liquidez, sem correlação com o portfólio existente.

**LOCAL:** ausência em `valuation_engine.py`, `fii_engine.py`, `data_quality.py`. `technical_engine.py:62-73` calcula ATR e ninguém o consome. `portfolio_engine` calcula volatilidade e covariância, mas isoladamente na tela "Gestor".

**PROBLEMA:** O `score_final` mistura upside (sigmoide), dívida, ROE e flags de confiabilidade de dados — mas nunca risco de mercado. Duas ações com o mesmo upside e o mesmo ROE recebem o mesmo score, tendo uma vol anual de 25% e a outra de 70%. `confianca` mede qualidade **de dado**, não incerteza **de estimativa** — dois conceitos distintos apresentados sob o mesmo rótulo na UI ("🎯 Confiança").

Ausência de gate de liquidez é concreta: nada impede analisar um ativo com R$ 50 mil/dia de volume e produzir COMPRA com upside de 40%. Volume nem é coletado.

Ausência de stress test é, dado o resto da auditoria, a omissão mais reveladora: uma única pergunta — "o que acontece com todos os fair values se a Selic subir 3 p.p.?" — expõe imediatamente que três dos quatro métodos são funções da Selic (F-4, F-5, F-9). O teste que revelaria o problema central do projeto é o que não existe.

**SEVERIDADE:** ALTO

**CORREÇÃO:** Ordem de implementação por custo/benefício: (1) gate de liquidez (volume médio 21d do `historico`, que já está em memória) — 2h; (2) volatilidade anualizada exibida ao lado do upside — 3h; (3) **matriz de sensibilidade Selic × fair value** para cada método, como diagnóstico de metodologia antes de qualquer outra coisa — 4h e provavelmente o maior retorno informacional de toda esta lista; (4) VaR histórico da carteira — 1 dia.

**ESFORÇO:** 2,5 dias no total; 4h para o item (3), que deve vir primeiro.

---

```
[ID: F-12]
[FASE: FINANCEIRO]
[CATEGORIA: 2.2 Metodologia — indicador com nome errado]
```
**ACHADO:** `divida_pl = (passivo_total − PL)/PL` é passivo **total** sobre patrimônio, e é mapeado para um campo chamado `div_liq_patrimonio` (dívida líquida/patrimônio).

**LOCAL:** `cvm_provider.py:196`; `market_engine.py:46-49` (`'divida_pl': 'div_liq_patrimonio'`); `fundamentus_scraper.py:132` (o Fundamentus preenche o **mesmo** campo com o valor correto).

**PROBLEMA:** Na BPP da CVM, a conta "2" é Passivo Total (= Ativo Total, inclui o PL). Logo `passivo_total − PL` = passivo exigível total: fornecedores, obrigações fiscais, provisões, impostos diferidos, arrendamentos — tudo, não apenas dívida financeira. Dívida líquida seria `(empréstimos CP + LP) − caixa e equivalentes`, contas 2.01.04 / 2.02.01 e 1.01.01.

Pior que o erro em si: o mesmo campo recebe a métrica correta quando a fonte é Fundamentus e a métrica errada quando é CVM — e CVM sobrescreve Fundamentus (`overwrite=True`). O comentário em `market_engine.py:44-45` reconhece ("proxy de alavancagem total, não dívida líquida financeira; mapeado como melhor aproximação disponível") mas mantém o nome enganoso.

**CENÁRIO DE FALHA:** ITUB4. Passivo total ≈ R$ 2,7tri, PL ≈ R$ 200bi → `div_liq_patrimonio ≈ 12,5`. Bancos são alavancados por natureza; o número não indica risco. Se esse campo entrar em qualquer heurística de qualidade (hoje não entra em `valuation_engine`, que usa `divida_liq_ebitda`, mas está exposto em `auditoria.py:162` e no modelo de domínio), todo banco é classificado como perigosamente endividado. O campo está no dicionário, com nome errado, esperando o primeiro consumidor.

**SEVERIDADE:** ALTO

**CORREÇÃO:** Renomear para `passivo_total_pl` e não mapear para `div_liq_patrimonio`. Implementar dívida líquida real a partir das contas de empréstimos e caixa (é o item "proper net financial debt calculation" do backlog). Nunca deixar duas fontes escreverem métricas diferentes no mesmo nome.

**ESFORÇO:** 1 dia.

---

```
[ID: F-13]
[FASE: FINANCEIRO]
[CATEGORIA: 2.2 Metodologia — plano de contas único para setores incompatíveis]
```
**ACHADO:** O mapeamento de contas CVM é único para todos os setores. Instituições financeiras e seguradoras usam estrutura de DRE/BP diferente.

**LOCAL:** `cvm_provider.py:17-26` (`_CONTAS`); `peers_engine.py:13,20` (ITUB4, BBDC4, BBAS3, SANB11, BPAC11, BBSE3, CXSE3, PSSA3 — 8 dos ~40 peers).

**PROBLEMA:** Para bancos, a conta 3.01 não é "Receita Líquida" comparável — é receita da intermediação financeira, grandeza sem relação com receita industrial. A conta 3.05 ("EBIT") não tem significado num banco. `margem_liquida = lucro/receita` produz um número que não é margem. Além disso, a conta 2.03 (Patrimônio Líquido Consolidado) **inclui participação de não controladores**; para VPA por ação do acionista, o correto é o PL atribuível aos controladores. Para holdings com minoritários relevantes (Itaúsa, Cosan, Ultrapar), VPA e LPA saem superestimados e P/VP e P/L subestimados — na mesma direção do achado E-1, agravando-o.

**CENÁRIO DE FALHA:** ITUB4 analisado com CVM disponível. Recebe badge 🟢 (o mais alto de confiança), `margem_liquida` sem significado, ROE possivelmente contaminado por minoritários, e — pelo achado F-7 — Lynch em R$ 106,64. O README lista "ROE, margens, dívida, receita" como o diferencial de dados auditados. Para o setor mais líquido da B3, esses campos não são comparáveis com os de uma indústria.

**SEVERIDADE:** ALTO

**CORREÇÃO:** `_CONTAS` por setor (industrial, financeiro, seguros, utilities), selecionado por `SETOR_ATIV` do `cad_cia_aberta.csv` que `cvm_ticker_map.py` já baixa. Usar PL atribuível aos controladores para VPA. Enquanto não houver mapa específico: marcar `cvm_disponivel = False` para financeiras e não exibir badge verde — é o item "bank-specific rules" do backlog e é pré-requisito de qualquer análise confiável de banco.

**ESFORÇO:** 3 dias.

---

```
[ID: F-14]
[FASE: FINANCEIRO]
[CATEGORIA: 2.6 Conformidade regulatória]
```
**ACHADO:** O sistema emite "COMPRA", "COMPRA FORTE" e "VENDA" sobre valores mobiliários nominados, em destaque visual, contrariando a regra escrita pelo próprio projeto em dois lugares.

**LOCAL:** `valuation_engine.py:202-213`; `fii_engine.py:130-134`; `app.py:62-77, 263` (renderizado em 2rem, negrito, verde/vermelho); contra: `CLAUDE.md:41` ("Todo output é educacional — NUNCA recomendação de compra/venda") e `ai_core.py:138` (o prompt instrui explicitamente a IA a **não** usar orientação de compra ou venda, preferindo "sinal positivo / neutro / sinal de atenção").

**PROBLEMA:** A camada de IA foi cuidadosamente restringida a vocabulário educacional, enquanto a camada determinística — logo acima dela na mesma tela, em fonte três vezes maior — exibe "🟢 COMPRA FORTE". O disclaimer do README é adequado em texto, mas a hierarquia visual da UI o contradiz. Adicionalmente, `DISTRESSED_TICKERS` (`config.py:63-69`) é uma lista **hardcoded de ativos específicos** que recebem "ALTO RISCO — EVITAR" — um juízo nominal sobre emissores, mantido manualmente e sem data de revisão (MGLU3 aparece na lista sem estar em recuperação judicial; `auditar_recomendacoes.py:30` referencia VIIA3, ticker que deixou de existir em 2023).

**CENÁRIO DE FALHA:** Enquanto local e pessoal, o risco é baixo. O roadmap tem "Deploy público (Streamlit Community Cloud)" como item planejado. Publicar uma ferramenta que gera recomendações nominais de compra e venda de valores mobiliários entra no território das Resoluções CVM 19 e 20 (consultoria e análise de valores mobiliários), independentemente do disclaimer. O `MGLU3` na lista de "evitar" é uma opinião pública sobre um emissor específico.

**SEVERIDADE:** ALTO

**CORREÇÃO:** Alinhar o vocabulário determinístico ao que já foi decidido para a IA: `SINAL POSITIVO / NEUTRO / ATENÇÃO / DADOS INSUFICIENTES`. Substituir `DISTRESSED_TICKERS` por critério derivado de dado (PL negativo, alavancagem, evento de RJ na CVM) em vez de lista de nomes. Não fazer o deploy público sem revisão jurídica **e** sem resolver E-29 (autenticação/isolamento de carteira). O disclaimer deve estar na tela, não só no README.

**ESFORÇO:** 1 dia para o vocabulário; a decisão sobre publicação é anterior ao código.

---

```
[ID: F-15]
[FASE: FINANCEIRO]
[CATEGORIA: 2.3 Modelagem de risco — otimização mal rotulada]
```
**ACHADO:** A tela "Otimizador de Carteira" anuncia "Alocação Sugerida (Máximo Sharpe)", mas para carteiras mistas otimiza dois grupos separadamente e cola os resultados num split fixo 40/60.

**LOCAL:** `portfolio_engine.py:117-127`; `app.py:481, 516`.

**PROBLEMA:** Três defeitos sobrepostos:
1. **Não é máximo Sharpe.** FIIs e ações são otimizados isoladamente e combinados com pesos fixos (`p × 40` e `p × 60`). A correlação cruzada entre os grupos não entra na otimização — só na exibição das métricas, recalculadas depois sobre a carteira colada. O split 40/60 é uma política de alocação hardcoded, sem justificativa em nenhum lugar do código ou da documentação.
2. **Retorno esperado = média histórica de 1 ano.** O erro clássico de Markowitz: a estimativa de médias tem erro de estimação que domina o resultado, e a otimização amplifica exatamente os ativos com maior ruído positivo. Sem shrinkage (Ledoit-Wolf), sem Black-Litterman, sem prior.
3. **Descasamento de composição.** `retornos = np.log(df/df.shift(1))`, `medias = ret.mean() × 252` produz retorno **logarítmico** anualizado, comparado contra a Selic (taxa aritmética efetiva) no cálculo do Sharpe. Para um ativo com 40% de vol, a diferença log-vs-aritmético é da ordem de σ²/2 ≈ 8 p.p. — o Sharpe reportado é sistematicamente subestimado.

**CENÁRIO DE FALHA:** Carteira com 3 ações e 2 FIIs, 250 pregões. O ativo com o melhor ano recente domina a alocação de seu grupo. O usuário vê "Sharpe Otimizado 1,42" (com o help text "Acima de 1.0 é considerado bom"), sem intervalo de confiança, sem indicação de que o número é in-sample. A alocação é a extrapolação do ano passado apresentada como otimização.

**SEVERIDADE:** ALTO

**CORREÇÃO:** Renomear a tela para o que ela faz ("Alocação sugerida — máximo Sharpe por grupo, split 40/60"). Aplicar shrinkage de covariância. Substituir médias históricas por retorno implícito de equilíbrio ou permitir input do usuário. Converter log→aritmético antes do Sharpe. Exibir que o resultado é in-sample.

**ESFORÇO:** 2 dias.

---

**Achados de menor severidade — Financeiro**

| # | Categoria | Achado | Local | Sev. | Correção | Esforço |
|---|---|---|---|---|---|---|
| F-16 | 2.3 Otimização | `bounds (0,05; 0,35)` determinam a solução para N=3 (soma máxima 1,05 — quase nenhum grau de liberdade). Para N>20 é inviável e cai silenciosamente em pesos iguais via `opt.success=False` | `portfolio_engine.py:87-94` | MÉDIO | Bounds em função de N; expor quando o fallback dispara | 3h |
| F-17 | 2.7 Custos e tributos | Custos de transação, corretagem, spread, emolumentos e IR ausentes em **todos** os módulos: backtest, otimizador e carteira. Rebalanceamento sugerido sem custo tributário (15% ações, 20% FII, sem isenção de R$ 20 mil no FII) | `portfolio_engine.py`, `backtest_engine.py`, `app.py:405-470` | MÉDIO | Modelar ao menos IR + 0,03% emolumentos no backtest | 1,5d |
| F-18 | 2.4 Backtest | `auto_adjust=False` exclui dividendos do retorno realizado — justamente para estratégias (Bazin/Gordon) que selecionam por dividendo. Viés contra a própria tese testada | `backtest_engine.py:57` | MÉDIO | Retorno total: `auto_adjust=True` ou somar proventos | 2h |
| F-19 | 2.4 Backtest | Observações de horizonte zero (`data_analise == end_date`) entram nas estatísticas com `retorno_real = 0.0` — 3 das 15 avaliadas | `backtest_engine.py:180-183` | MÉDIO | Excluir horizonte < 60 dias | 1h |
| F-20 | 2.4 Backtest | Sem survivorship: universo = 3 tickers escolhidos hoje entre os sobreviventes. Sem empresas deslistadas, incorporadas ou em RJ | `backtest_engine.py:41` | MÉDIO | Universo histórico do IBrX a partir de composições passadas | 1,5d |
| F-21 | 2.7 Carteira | Rentabilidade = variação de preço apenas. Ignora proventos recebidos, e o `preco_medio` armazenado não é ajustado por split/grupamento/bonificação | `app.py:432-439`, `database.py:54-84` | MÉDIO | Tabela de proventos + ajuste por evento corporativo | 2d |
| F-22 | 2.5 Viés | `DISTRESSED_TICKERS` é lista manual sem data de revisão; MGLU3 marcado como distressed sem RJ; VIIA3 referenciado em `auditar_recomendacoes` não existe desde 2023 | `config.py:63-69`, `auditar_recomendacoes.py:30` | MÉDIO | Critério derivado de dado (ver F-14) | 1d |
| F-23 | 2.1 Peers | Média **aritmética** de P/L entre peers (sensível a outliers; mediana é o padrão), sem excluir valores com `pl_confiavel=False`. MGLU3 é peer de varejo mas é bloqueada como distressed | `peers_engine.py:86-88`, `:16` | MÉDIO | Mediana + filtro por `pl_confiavel` + coerência com distressed | 3h |
| F-24 | 2.2 TTM | `calcular_indicadores(anos=1)` usa só o DFP do ano-1. Entre janeiro e março o DFP do ano anterior ainda não foi publicado → 404 → `cvm_disponivel=False` silencioso. Sem TTM via ITR (`baixar_itr` existe e nunca é chamado) | `market_engine.py:488`, `cvm_provider.py:63,145` | MÉDIO | TTM = soma dos 4 últimos ITRs, com fallback DFP e aviso na UI | 2d |
| F-25 | 2.6 Conformidade | Scraping do Fundamentus com bypass declarado de detecção de bot (`cloudscraper`, comentário "bypassa Cloudflare/bot detection"). Circunvenção explícita de proteção anti-bot é violação de ToS | `fundamentus_scraper.py:10-29` | MÉDIO | Remover o scraper (recomendado) ou obter autorização | 4h |
| F-26 | 2.2 Classificação FII | Comentários de segmento em `FIIS_CONHECIDOS` estão errados (HGLG11 sob "Papel"; KNIP11/HGCR11 sob "Tijolo"; BCFF11 é FOF sob "Tijolo"). Nenhuma distinção de segmento existe no código, apesar do README afirmar que existe | `config.py:41-53` | BAIXO | Corrigir ou remover os comentários; implementar segmento de verdade (ver F-9) | 2h |
| F-27 | Documentação | README e roadmap marcam ✅ "CVMFIIProvider com Informe Mensal e **cálculo de vacância**". O próprio provider documenta que vacância não existe no informe e retorna `None` sempre | `README.md`, `cvm_fii_provider.py:8,144-146` | MÉDIO | Corrigir o roadmap; vacância é item não iniciado | 30min |
| F-28 | 2.5 Overfitting | Score sigmoide com amplitude 48 e inclinação 3 sem justificativa. Upside de 15% → score 60,7, colado no gate `REC_SCORE_COMPRA = 60`. Ruído de 0,2 p.p. no upside inverte a recomendação | `valuation_engine.py:156`, `config.py:169-170` | BAIXO | Documentar a calibração; adicionar histerese ou banda neutra na fronteira | 3h |
| F-29 | 2.4 Reprodutibilidade | `backtest_results_v1.csv` contém a string `'ALTA DIVERGENCIA 127%'`, ausente do código atual — foi gerado por versão anterior e está commitado como resultado corrente | `backtesting/backtest_results_v1.csv` | MÉDIO | Regenerar do HEAD, gravar commit hash no CSV | 1h |
| F-30 | 2.1 Cobertura | ~50 tickers no mapa CVM, 30 FIIs com CNPJ, 10 setores com ~40 peers. Fora disso o "diferencial de dados oficiais" simplesmente não existe, e a UI não distingue "sem cobertura" de "sem dados" | `cvm_ticker_map.py:15`, `cvm_fii_map.py`, `peers_engine.py:12-23` | BAIXO | Mensagem explícita de "ticker fora do mapa CVM"; `refresh()` automático do cadastro | 4h |

---

# MATRIZ DE RISCO CONSOLIDADA

| Severidade | Engenharia | Financeiro | Total |
|------------|------------|------------|-------|
| CRÍTICO    | 3          | 3          | **6**  |
| ALTO       | 10         | 12         | **22** |
| MÉDIO      | 9          | 12         | **21** |
| BAIXO      | 6          | 3          | **9**  |
| COSMÉTICO  | 2          | 0          | **2**  |
| **Total**  | **30**     | **30**     | **60** |

Distribuição por natureza do risco:

| Natureza | Qtd | Comentário |
|---|---|---|
| Produz resultado errado **silenciosamente** | 19 | A categoria dominante e a mais perigosa neste projeto |
| Feature documentada que não existe ou não roda | 6 | README, roadmap e `CLAUDE.md` divergem do código |
| Quebra em produção / degradação silenciosa | 11 | Cache envenenado, timeouts, dependência ausente |
| Debt que impede evolução | 13 | Arquitetura dupla, sem CI, cobertura de orquestração zero |
| Conformidade / legal | 3 | Vocabulário de recomendação, ToS de scraping, deploy sem auth |
| Qualidade de código / cosmético | 8 | — |

---

# TOP 5 — SE EU SÓ CORRIGIR 5 COISAS ANTES DE RETOMAR

Priorizadas por: (1) resultado errado silencioso > (2) quebra em produção > (3) debt bloqueante > (4) qualidade > (5) cosmético.

### 1. Ancoragem de LPA/VPA — `sharesOutstanding` e validação cruzada tautológica
*(E-1 + E-2, ambos CRÍTICO — 3,5 dias)*

Este é o par que produz o maior erro de magnitude com o maior selo de confiança. O `lpa`/`vpa` derivado do `sharesOutstanding` do yfinance pode estar 2x errado para qualquer empresa dual-class, e a única checagem que existiria para pegá-lo é matematicamente incapaz de disparar porque compara um valor com sua própria definição. Corrigir os dois juntos, nessa ordem: primeiro o guard de reconciliação (`shares × preço ≈ market cap`), depois a validação fonte-contra-fonte. Se o guard reprovar mais de ~10% dos tickers do mapa, a resposta certa é parar de derivar múltiplos da CVM até ter a composição de capital por classe.

**Primeiro passo concreto, hoje:** rodar o cálculo para PETR4, ITUB4, BBDC4, ELET6 e GGBR4 comparando `lpa_cvm` com `lpa` do brapi. Se divergirem sistematicamente por um fator próximo da razão entre classes, está confirmado.

### 2. Matriz de sensibilidade Selic × fair value — antes de escrever qualquer código de correção
*(diagnóstico de F-4, F-5, F-9 — 4 horas)*

Três dos quatro métodos de ação e o método de FII colapsam em `DY ÷ Selic` com o preço cancelando. Nenhum deles vai gerar sinal positivo com Selic em 14,75% — não porque o mercado esteja caro, mas por identidade algébrica dos parâmetros.

Uma tabela de 4 horas — para cada método, o DY mínimo que produz upside positivo, numa grade de Selic de 8% a 16% — expõe isso de forma inegociável e informa todas as decisões metodológicas seguintes. É o maior retorno informacional por hora de trabalho em toda esta auditoria, e vem antes de qualquer correção porque define **quais** correções fazem sentido.

Isso também é o que decide o PR #8: sem essa tabela, trocar Selic por NTN-B no Gordon dobra os fair values (F-6) e o commit parecerá uma correção.

### 3. Normalização de DY em ponto único
*(E-4 + E-5, ALTO — 1,5 dia)*

O DY alimenta o gate de perfil, três dos quatro métodos de ação e 100% do valuation de FII. Hoje passa por até três conversores com regras incompatíveis, um deles capaz de reduzir o valor em 100x sem alerta, e o guard de sanidade tem ordem de checagem invertida. Normalizar uma vez, na fronteira do provider, validar como invariante, e cobrir a faixa 0,20–1,20 com teste parametrizado.

### 4. Backtest: deletar o dataset sintético e declarar o estado real
*(F-1 + F-2, CRÍTICO — 1 dia para a limpeza honesta, 3-4 dias para o pipeline real)*

Os 15 fundamentos "point-in-time" são inventados e retro-estimados a partir de dados atuais — o próprio README do backtest afirma isso e nega na linha seguinte. O resultado que ele produz (46,7% geral, Graham 0%) está commitado, não foi respondido, e foi gerado por uma versão anterior do engine.

A parte urgente não é construir o backtest real; é **remover a evidência falsa**, para que a retomada não seja guiada por ela. O `CVMProvider` já baixa ZIPs que são point-in-time por construção — o caminho para o dataset verdadeiro existe, e passa por usar `DT_ENTREGA`, não `DT_REFER`.

### 5. Conectar ou remover a camada macro, e fechar as três integrações inertes
*(F-3 CRÍTICO + E-10 + E-11 + E-30, ALTO — 2 dias)*

Quatro features anunciadas não rodam: NTN-B/CDI/IPCA sem consumidor, `CVMFIIProvider` nunca injetado no app, `cloudscraper` ausente do `requirements.txt`, `baixar_itr` nunca chamado. Cada uma tem seu ✅ no roadmap ou sua linha no README.

Isso importa mais do que a soma das severidades individuais sugere: é o que faz a documentação superestimar a base entregue, e é a causa de uma retomada partir de premissa errada sobre o que está pronto. Duas dessas (o provider de FII e o `cloudscraper`) são correções de uma linha cada.

---

# VEREDITO DE RETOMADA

## O projeto está em estado de ser retomado com confiança?

**CONDICIONAL.**

A base de engenharia é melhor do que a média de projetos pessoais nesta categoria: 255 testes que rodam em 2 segundos sem rede, `sentinela/domain/` com 91-98% de cobertura, SQL parametrizado sem exceção, um modelo de proveniência por campo bem desenhado, e um `BacktestEngine` cujo gate temporal de preço está corretamente implementado. Os guards de `pl_confiavel`, `dy_confiavel` e `erro_scraper` mostram que os modos de falha foram pensados. Isso é fundação real.

O que não está confiável é a **camada de resultado**. O sistema produz um número em toda circunstância — nenhuma falha de fonte, nenhum dado ausente, nenhuma incoerência de unidade interrompe a análise. Somado a 19 achados que produzem erro silencioso e a uma validação cruzada estruturalmente incapaz de disparar no caminho mais crítico, a consequência prática é: **não há como distinguir, olhando a tela, uma análise correta de uma errada por fator 2.** O badge 🟢 "Dados CVM" acompanha as duas.

O que não está validado é a **metodologia**. A única evidência empírica do projeto usa dados fabricados, e o que ela mostra (46,7% de acerto, Graham 0%, COMPRA 25%) não foi respondido. Enquanto isso, três dos quatro métodos são funções da mesma variável e não conseguem gerar sinal positivo no regime de juros vigente.

Nada disso é irreversível. Mas continuar adicionando features sobre essa base multiplica a superfície de erro silencioso.

## Condições mínimas para retomar

Estas são as travas. Nenhuma feature nova antes delas:

1. **Guard de reconciliação em LPA/VPA** — o cálculo derivado da CVM só é usado se `|shares × preço − market_cap| / market_cap ≤ 5%`. Sem isso, o dado com maior selo de confiança é o menos verificado.
2. **Matriz de sensibilidade Selic × fair value publicada** (4h) — a decisão metodológica de Gordon, Bazin e FII depende dela, e o PR #8 é perigoso sem ela.
3. **Normalização de DY em ponto único**, com teste parametrizado cobrindo a zona ambígua.
4. **Backtest sintético removido do repositório**, e `README_BACKTEST.md` declarando em uma linha que a metodologia não está validada.
5. **CI no GitHub Actions** rodando `pytest` + `ruff` em todo PR — o fluxo já é baseado em PRs; falta o gate.
6. **README, roadmap e `CLAUDE.md` sincronizados com o código**, com as quatro integrações inertes marcadas honestamente como 🔄 ou removidas. Retomar a partir de documentação que superestima a base é o erro mais caro disponível.
7. **Decisão explícita sobre o deploy público** — se sair do roadmap, E-29 (banco global sem autenticação) e F-14 (vocabulário de recomendação) viram bloqueadores absolutos.

## Estimativa de esforço até "production-ready"

Para um app local, pessoal, com resultados em que se possa confiar:

| Bloco | Esforço |
|---|---|
| Correções CRÍTICO (6 achados) | 8-10 dias |
| Correções ALTO (22 achados) | 18-22 dias |
| CI, lint, lockfile, migrations | 3 dias |
| Cobertura de orquestração e parsers (E-13) | 2 dias |
| Migração `sentinela/` concluída (E-21) | 2 dias |
| **Total até "local, confiável, documentado com honestidade"** | **7-8 semanas** de trabalho focado |

Para deploy público com múltiplos usuários, somar autenticação, isolamento de dados, rate limiting, revisão do vocabulário regulatório e revisão jurídica: **+4-6 semanas**, e a revisão jurídica deve vir antes do código.

A boa notícia: o **TOP 5 é ~10 dias** e resolve a maior parte do risco de resultado errado. Depois dele, o projeto volta a ser um lugar seguro para adicionar features.

## Reescrever vs. Refatorar vs. Manter

**REESCREVER** — a lógica está errada por dentro, não apenas malfeita:

- `valuation_engine.processar` — a camada de ancoragem dos quatro métodos. O piso de P/L 7, a taxa do Gordon, a taxa do Bazin e o tratamento de JCP são decisões que precisam ser retomadas juntas, não emendadas uma a uma. Manter a assinatura e a estrutura de guards, que são boas.
- `fii_engine.analisar` — sem ancoragem patrimonial, com dupla contagem de vacância e vacância física aplicada a fundos de papel. Precisa das duas pernas (renda + patrimônio) e de segmentação por tipo de fundo.
- `backtesting/fundamentos_point_in_time.csv` — deletar. Reconstruir a partir dos ZIPs da CVM usando `DT_ENTREGA`.
- `portfolio_engine.otimizar` — o split 40/60 hardcoded, a otimização por grupo e as médias históricas como retorno esperado. Ou vira uma otimização de verdade, ou vira uma heurística de alocação honestamente rotulada.

**REFATORAR** — a estrutura serve, os detalhes falham:

- `market_engine` — a cascata está certa; a normalização de unidades, a proveniência e a preservação dos valores brutos precisam de trabalho (E-1, E-2, E-4).
- `cvm_provider` — download atômico, cache de DataFrame, `DT_REFER` determinístico, plano de contas por setor, TTM via ITR. É a peça com maior potencial no projeto; está a poucas correções de ser o diferencial que o README promete.
- `data_quality` — os checks certos, aplicados aos valores certos, antes das mutações.
- `app.py` — delegar para `AnalysisService` e parar de mutar `dados`.
- `AssetClassifier` — inverter a regra do sufixo "11" (evidência positiva para FII).

**MANTER** — está bom, não mexer:

- `sentinela/domain/` — `models.py` (98%), `provenance.py` (91%), `enums.py` (100%). O modelo de proveniência por campo é a melhor peça de design do projeto e está subutilizado.
- `technical_engine` — corrigir apenas o RSI quando não há perdas (E-24); o resto está correto.
- `database.py` — SQL parametrizado, WAL, `closing()` disciplinado. Precisa de PK composta e migrations, não de reescrita.
- `cvm_ticker_map` / `cvm_fii_map` — mapas verificados contra a fonte, com CNPJ conferido e comentado. Expandir cobertura, manter a abordagem.
- `tests/` existentes — 255 testes sintéticos e rápidos são um ativo. Falta cobrir o que importa, não refazer o que existe.

---

## Nota de método

Três achados foram marcados `REQUER VALIDAÇÃO` porque dependem de comportamento de API externa que não pude verificar deste ambiente (sem acesso de rede a Yahoo/brapi):

- **E-1**: escopo real de `sharesOutstanding` do yfinance para tickers dual-class `.SA`. A aritmética do cenário de falha está correta condicionalmente ao escopo ser por classe; confirmar com 5 tickers antes de escolher a correção.
- **F-7**: se `dividendYield` do yfinance para tickers `.SA` inclui JCP, e se bruto ou líquido de IRRF. Reconciliar contra o informe de proventos da B3.
- **E-19**: default efetivo de `auto_adjust` na versão de yfinance que o `requirements.txt` resolve hoje.

Nenhum problema foi inventado. Os que estão listados são verificáveis por leitura do código nos locais indicados, e os cenários de falha usam os números do próprio repositório sempre que disponíveis.

---

# TABELA DE CORRESPONDÊNCIA — ID ANTIGO → ID NOVO

IDs de engenharia (E-1 a E-30) não mudaram; os blocos E-1 a E-22 apenas ganharam o ID explícito no cabeçalho.

| ID antigo | ID novo | Achado |
|---|---|---|
| (bloco sem ID; citado como F1 ou F-1) | F-1 | Fundamentos point-in-time sintéticos |
| (bloco sem ID; citado como F2 ou F-2) | F-2 | Backtest com resultado ignorado |
| (bloco sem ID; citado como F3 ou F-3) | F-3 | Camada macro inerte |
| (bloco sem ID; citado como F4 ou F-4) | F-4 | Gordon: Selic como taxa de desconto |
| (bloco sem ID; citado como F5 ou F-5) | F-5 | Bazin descaracterizado |
| (bloco sem ID; citado como F6 ou F-6) | F-6 | Armadilha real × nominal na correção planejada |
| (bloco sem ID; citado como F7 ou F-7) | F-7 | JCP não tratado |
| (bloco sem ID; citado como F8 ou F-8) | F-8 | Graham com LPA fabricado (piso de P/L 7) |
| (bloco sem ID; citado como F9 ou F-9) | F-9 | FII sem ancoragem patrimonial |
| (bloco sem ID; citado como F10 ou F-10) | F-10 | FII: dupla contagem de vacância |
| (bloco sem ID; citado como F11 ou F-11) | F-11 | Modelagem de risco ausente |
| (bloco sem ID; citado como F12 ou F-12) | F-12 | Indicador `div_liq_patrimonio` com nome errado |
| (bloco sem ID; citado como F13 ou F-13) | F-13 | Plano de contas único para setores incompatíveis |
| F-24 (só no Veredito) | F-14 | Conformidade regulatória (vocabulário de recomendação) |
| (bloco sem ID) | F-15 | Otimizador de carteira mal rotulado (Markowitz) |
| F-15 (tabela) | F-16 | ver tabela de menor severidade |
| F-16 (tabela) | F-17 | ver tabela de menor severidade |
| F-17 (tabela) | F-18 | ver tabela de menor severidade |
| F-18 (tabela) | F-19 | ver tabela de menor severidade |
| F-19 (tabela) | F-20 | ver tabela de menor severidade |
| F-20 (tabela) | F-21 | ver tabela de menor severidade |
| F-21 (tabela) | F-22 | ver tabela de menor severidade |
| F-22 (tabela) | F-23 | ver tabela de menor severidade |
| F-23 (tabela) | F-24 | ver tabela de menor severidade |
| F-25 (tabela) | F-25 | ver tabela de menor severidade |
| F-26 (tabela) | F-26 | ver tabela de menor severidade |
| F-27 (tabela) | F-27 | ver tabela de menor severidade |
| F-28 (tabela) | F-28 | ver tabela de menor severidade |
| F-29 (tabela) | F-29 | ver tabela de menor severidade |
| F-30 (tabela) | F-30 | ver tabela de menor severidade |
