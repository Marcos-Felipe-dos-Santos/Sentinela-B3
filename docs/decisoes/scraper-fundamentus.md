# Decisão pendente: o que fazer com o scraper do Fundamentus

**Status:** levantamento (F0-4). Nada foi decidido e nenhum código mudou.
**Quem decide:** Marcos, no checkpoint da Fase 0.
**Conflito:** E-11 (declarar `cloudscraper` e manter o scraper) × F-25 (remover o scraper por ToS), ambos em `docs/auditoria/2026-09-red-team.md`.

> Método: leitura estática do código e dos testes em 1/10/2026. Não houve acesso de rede, então nenhum número abaixo mede cobertura real do Fundamentus, da brapi ou do yfinance. Onde o número depende de rede, o texto diz como medir (F0-6 e F2A).

## 1. O que o scraper entrega

`fundamentus_scraper.py` lê `detalhes.php?papel=<ticker>` (linha 99) e extrai 14 campos mais o preço:

`pl`, `pvp`, `dy`, `roe`, `roic`, `div_liq_patrimonio`, `divida_liq_ebitda`, `margem_liquida`, `margem_bruta`, `patrimonio_liquido`, `receita_liquida`, `lucro_liquido`, `ativo_total`, `ativo_circulante`, `preco_atual`.

O Fundamentus só entra na cascata como último recurso (`market_engine.py:337-342`): é chamado quando a brapi falhou ou quando ainda faltam campos obrigatórios depois de yfinance, brapi e CVM, e `merge_if_valid` só preenche lacunas.

## 2. Quantos campos dependem só do Fundamentus

Fornecedores alternativos, pelo código:

| Fonte | Campos que entrega | Cobertura de tickers |
|---|---|---|
| yfinance | `preco_atual`, histórico, `pl`, `pvp`, `dy`, `roe`, `quote_type` | qualquer ticker `.SA` |
| brapi | `preco_atual`, `pl`, `pvp`, `roe`, `dy`, `divida_liq_ebitda`, `lpa`, `vpa`, `quote_type` | qualquer ticker, **só com `BRAPI_TOKEN`** (sem ele o provider fica desligado, `brapi_provider.py:72-76`) |
| CVM | `roe`, `margem_liquida`, `div_liq_patrimonio` (proxy), `patrimonio_liquido`, `lucro_liquido`, `receita_liquida`, `ativo_total`, `ativo_circulante`, e `lpa`/`vpa`/`pl`/`pvp` derivados | **50 ações** do mapa manual (`cvm_ticker_map.py`) |

Cruzando com os 14 campos do Fundamentus:

| Campo | Outra fonte? | Consumidor no código |
|---|---|---|
| `roic`, `margem_bruta` | **Nenhuma.** Só o Fundamentus | Nenhum cálculo os lê. Aparecem em `auditoria.py` (exibição) e no modelo de domínio `sentinela/domain/models.py`. |
| `divida_liq_ebitda` | brapi (com token). A CVM não fornece | **Sim:** `valuation_engine.py` penaliza score e confiança acima de 3×; `data_quality.py` o lista entre os campos esperados |
| `div_liq_patrimonio` | CVM, só para os 50 mapeados, e como proxy de endividamento total (F-12) | Indicador exibido; não entra no valuation |
| `margem_liquida`, `receita_liquida`, `lucro_liquido`, `patrimonio_liquido`, `ativo_total`, `ativo_circulante` | CVM, só para os 50 mapeados | `margem_liquida` e `receita_liquida` estão em `_CAMPOS_ESPERADOS` do `data_quality.py`; `lucro_liquido` e `patrimonio_liquido` alimentam LPA/VPA derivados da CVM, não do Fundamentus |
| `pl`, `pvp`, `dy`, `roe`, `preco_atual` | yfinance, brapi | Núcleo do valuation. O Fundamentus só repete o que as outras fontes já dão |

**Resumo:**
- Campos **exclusivos** do Fundamentus: 2 (`roic`, `margem_bruta`), e nenhum motor os usa.
- Campo **relevante** que depende do Fundamentus quando não há brapi: 1 (`divida_liq_ebitda`).
- Campos que dependem dele **para tickers fora do mapa CVM**: `div_liq_patrimonio`, `margem_liquida`, `receita_liquida`, `lucro_liquido`, `patrimonio_liquido`, `ativo_total`, `ativo_circulante`. São 7, dos quais só `margem_liquida` e `receita_liquida` entram na completude de dados.
- O Fundamentus **não** fornece `lpa` nem `vpa`; o valuation os deriva de `preço ÷ pl` e `preço ÷ pvp`.

### Para quantos tickers

- **Dentro do mapa CVM (50 ações):** só `roic`, `margem_bruta` e, sem brapi, `divida_liq_ebitda`.
- **Fora do mapa (todo o resto da B3, algumas centenas de companhias):** os 7 campos acima e, sem brapi, `divida_liq_ebitda`.
- **FIIs:** o parser usa os rótulos de ação (`detalhes.php`, não `fii_detalhes.php`); o que ele extrai de um FII não foi verificado sem rede. Os FIIs têm `FII_MANUAL_FALLBACK` (`config.py:73`) e o provider da CVM, que hoje não é injetado no `FIIEngine` (`app.py:158`).
- Dá para medir o número exato para a amostra do F0-6: contar, ticker a ticker, os campos que só o Fundamentus preencheria (`field_provenance` registra a fonte vencedora de `preco_atual`, `dy`, `pl`, `pvp` e `roe`, mas **não** dos demais campos).

## 3. O que quebra se o módulo sair

**Código de produção**
- `market_engine.py`: importa `FundamentusScraper` (linha 13), instancia em `__init__` (196) e chama em `_buscar_fundamentus` (542-579). A cascata perde o passo 4.
- Flag `erro_scraper`, hoje com três consumidores de produção (`valuation_engine`, `app` e `market_engine`, que a lê para emitir `scraper_error`):
  - `valuation_engine.py:63` (confiança −30) e `:220` (rebaixa COMPRA para "DADOS INSUFICIENTES — AGUARDAR");
  - `app.py:239, 305, 316` (indicador "Erro Scraper" e mensagem);
  - `auditar_recomendacoes.py` (4 ocorrências); `sentinela/domain/models.py` só declara o campo.
  Sem o scraper, a flag ou some (e com ela o guard de segurança) ou fica sempre `False`/`True`. Isso é uma decisão de comportamento, não de limpeza.
- `market_engine.py:280` emite o aviso `scraper_error`; `data_quality.py` tem a fonte `fundamentus` (linhas 47 e 56, peso de confiança 40).
- `README.md` descreve o Fundamentus como camada 4 da cascata (linhas 27, 48, 71, 94). `auditoria.py` cita o scraper em 7 pontos.

**Testes**
- `tests/test_fundamentus_scraper.py` (2 testes) sairia por inteiro.
- Referências a `fundamentus` ou `erro_scraper` em outros testes: `test_market_engine.py` (14), `test_peers_engine.py` (9), `test_data_quality.py` (6), `test_valuation_engine.py` (3), `test_auditar_recomendacoes.py` (2), `test_analysis_repository.py` (1), `test_domain_models.py` (1). Vários testes da cascata (por exemplo `test_fundamentus_fills_only_missing_fields`, `test_scraper_failure_does_not_make_data_partial_when_brapi_complete`) precisariam ser reescritos, e a regra do projeto proíbe enfraquecer teste para passar.
- A remoção mudaria a cobertura e o gabarito de mutação do `fundamentus_scraper._limpar_valor`, que é um dos tickets do Jules previstos no F0-5.

**Cascata**
- Ticker fora do mapa CVM, sem `BRAPI_TOKEN`: perde `divida_liq_ebitda` e os 7 campos listados na seção 2, ficando só com o que o yfinance dá (`pl`, `pvp`, `dy`, `roe`). A penalidade de alavancagem do valuation deixa de existir para esse ticker: `valuation_engine.py` trata o campo ausente como `0.0`, isto é, como empresa sem alavancagem. A falta do dado vira um dado favorável em silêncio, o contrário do contrato de método da V2 (sem insumo, abstém-se). Isso pesa na escolha entre B e D.
- Hoje, em instalação limpa, isso já acontece de fato: sem `cloudscraper` instalado (E-11) o scraper tende a receber 403 e o fallback está, na prática, morto. O comportamento "sem scraper" é, portanto, o que um usuário comum já vê.

## 4. Brapi + CVM cobrem esses campos no universo mapeado?

- **Nos 50 tickers mapeados:** sim, para tudo o que o valuation lê. CVM cobre os campos patrimoniais e de resultado; brapi (com token) cobre `divida_liq_ebitda`. Sobram só `roic` e `margem_bruta`, sem consumidor.
- **Sem `BRAPI_TOKEN`, mesmo nos mapeados:** `divida_liq_ebitda` fica sem fonte. A CVM entrega apenas o endividamento contábil total, que não é dívida líquida sobre EBITDA (F-12). Seria preciso calcular dívida líquida e EBITDA a partir da CVM (item da Fase 2A, "dívida líquida").
- **Fora dos 50:** brapi + yfinance cobrem o núcleo do valuation (`pl`, `pvp`, `dy`, `roe`, `preço`). Os campos patrimoniais ficam vazios até o mapa automático ticker ↔ CNPJ (F2A-1). Nesse trecho o Fundamentus é hoje a única fonte, em teoria, dos 7 campos.
- Não verificado sem rede: a cobertura real da brapi no plano gratuito para esses campos e o formato atual da página do Fundamentus.

## 5. Opções, com custo e consequência

Sem recomendar. As duas primeiras vêm da própria auditoria.

| Opção | O que é | Custo | Risco / consequência |
|---|---|---|---|
| **A. Manter e declarar** (E-11) | Adicionar `cloudscraper` ao `requirements.txt`, fixar versão, documentar | ~1 h | Mantém o bypass de detecção de bot que o F-25 aponta como violação de ToS. O contorno existe em código público |
| **B. Remover** (F-25) | `git rm` do módulo, do teste e do import; decidir o destino de `erro_scraper` | ~4 h, mais reescrita dos testes da cascata (14 linhas de `test_market_engine.py` citam o scraper; o número de testes é menor) | Perde `roic`, `margem_bruta` (sem consumidor) e a fonte de 8 campos fora do mapa CVM (os 7 da seção 2 mais `divida_liq_ebitda` quando não há brapi) até o F2A-1 |
| **C. Manter só sem bypass** | Tirar o `cloudscraper` e o comentário de bypass, deixar `requests` simples com respeito ao `robots.txt` e limite de taxa | ~2 h | O site responde 403 a `requests` puro (afirmado pela auditoria, não verificado aqui), então o scraper provavelmente continua inútil |
| **D. Congelar e aposentar depois** | Manter como está até o F2A-1 (mapa automático) e a dívida líquida da CVM, e remover na limpeza da Fase 2A | 0 agora | Segue em produção local com o risco de ToS; `PLANO.md` já lista o scraper como candidato a remoção quando o mapa cobrir o universo |

## 6. Perguntas para o Marcos

1. O uso é pessoal e local. Isso muda a sua tolerância ao risco de ToS do F-25, ou o repositório ser público basta para tirar o bypass?
2. Você tem `BRAPI_TOKEN` ativo no dia a dia? Se sim, o único campo relevante que sobra só para o Fundamentus nos tickers mapeados desaparece.
3. `roic` e `margem_bruta` fazem falta como informação de tela, mesmo sem entrar no valuation?
4. A flag `erro_scraper` deve continuar como guard de "dados insuficientes" (renomeada para algo sem referência ao scraper) ou o guard passa a olhar os campos obrigatórios faltantes?
5. A remoção, se escolhida, entra na Fase 1 (limpeza), na 2A (junto do mapa automático) ou só depois que o mapa cobrir o universo?
