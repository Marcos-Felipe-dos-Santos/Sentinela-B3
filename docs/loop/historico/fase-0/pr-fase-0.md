# Fase 0 — Preparação (resumo para o PR)

Branch `v2/fase-0`. Doze itens (F0-0 a F0-11), doze commits, nenhum push. Fila e diário completos em `docs/loop/historico/fase-0/`.

## O que revisar primeiro

1. **`docs/decisoes/dossie-fase2.md`, seção 0.** O mapa manual `ticker → CD_CVM` (`cvm_ticker_map.py`) está desalinhado: contra o cadastro oficial da CVM, 1 das 50 entradas bate, 38 apontam para outra empresa e 11 têm ticker sem negociação ativa no FCA (VALE3 aponta para o Itaú, ITUB4 para o Banco Alfa). Na V1 isso atribui lucro, PL e ROE da CVM a outro ticker, sem alerta. Não estava na auditoria de 9/9. Está proposto como `F1-15` na fila da Fase 1.
2. **`tests/test_financeiro_pre_refactor.py` (F0-3).** É o gate da Fase 1. Confira as seções A (preservar), B (deve mudar) e C (invariantes).
3. **A quarentena no `app.py` (F0-9).** Conferência visual das quatro telas (`streamlit run app.py`), em especial o Gestor com uma carteira real.
4. **`docs/limpeza/inventario.md`**, seções 10 e 11 (o que saiu) e os itens *investigar*.

## Itens e commits

| Item | Commit | Resumo |
|---|---|---|
| F0-0 | `7fd812f` | Auditoria com IDs normalizados (E-1..E-22, F-1..F-15; tabela F-16..F-30; correspondência antigo → novo) |
| F0-1 | `90a876e` | Instruções e plano sincronizados com o código (linhas citadas, tempo da suíte, `CVMTickerMap`, armadilhas 7, 9 e 15) |
| F0-2 | `6079077` | CI (ruff restrito + pytest), `xfail_strict`, `--strict-markers`, Selic semeada no `conftest.py`, guarda de rede, `requirements-dev.txt`, `[tool.mutmut]` |
| F0-3 | `f269059` | Rede de segurança financeira: 23 testes em três seções com marks próprios |
| F0-4 | `8e96a57` | Brief da decisão do scraper do Fundamentus (E-11 × F-25) |
| F0-5 | `b9bba2f` | Backlog do Jules: revisão de PR, 4 tickets de teste com especificação externa, achados de baixa severidade |
| F0-6 | `d70d959` | Dossiê de decisão da Fase 2 e `scripts/dossie_fase2.py` |
| F0-7 | `8b0b787` | Inventário de resíduos |
| F0-8 | `49605f1` | Limpeza do que era "remover já"; `vulture_whitelist.py` |
| F0-9 | `6a57235` | Quarentena da V1 no `app.py` (aviso fixo; "Alocação Sugerida" fora da tela) |
| F0-10 | `8271947` | Proposta da fila da Fase 1 (`docs/loop/fila-fase1-proposta.md`) |
| F0-11 | (este commit) | Resumo da fase e arquivamento |

## Testes, antes → depois

| | Antes | Depois |
|---|---|---|
| Testes | 255 passam | 283 passam + 1 xfail estrito |
| Gate de CI | não existia | `ruff` restrito (E9, F63, F7, F82) + `pytest`, em push e pull request |
| Rede na suíte | BCB no import, sem guarda | Selic semeada; `socket.connect` bloqueado (derruba o teste e a sessão) |
| `ruff check .` completo | 301 erros | 317 (os novos vêm dos arquivos do loop; 214 com correção automática) |
| Mutation (`valuation_engine`, suíte inteira) | sem medição | 377 mortos, 249 sobreviventes: 60,2% |

Os 29 testes novos (255 → 284 coletados, dos quais 283 passam e 1 é xfail estrito) são: 23 do F0-3 (22 passam e 1 xfail estrito do DY acima de 30%) e 6 do F0-9 (aviso nas quatro telas, URL do PLANO, sem "Alocação Sugerida" e sem gráfico na tela do Gestor).

## Decisões pendentes

- **Scraper do Fundamentus** (`docs/decisoes/scraper-fundamentus.md`): declarar o `cloudscraper`, remover, ou congelar. Cinco perguntas no fim do documento.
- **Itens *investigar* do inventário:** `get_quote`, `buscar_noticias`, `reportlab` e `openpyxl` (sem uso), `cloudscraper` ausente do `requirements.txt`, `docs/cleanup_report.md`.
- **Dossiê da Fase 2:** as oito perguntas da seção 8, a 0 sendo a do mapa desalinhado.
- **ADR-0002:** aceitar ou recusar D5 a D13. A fila da Fase 1 diz o que muda se D5, D9 ou D11 forem recusadas.
- **Critério do E-8** (`VERSAO` × `DT_REFER`): a correção da auditoria não resolve a republicação do DFP; o ticket B4.2 do Jules só abre depois disso.
- **Invariante de DY:** "DY em [0, 0,30]" (F0-3, seção C) não bate com o corte de 0,25 do código; `_normalizar_dy(45.0)` devolve DY de 45% como confiável (xfail estrito).
- **Aprovar a fila da Fase 1** (`docs/loop/fila-fase1-proposta.md`).

## Resíduos que ficaram para o Marcos

O loop não apaga arquivo não rastreado nem branch.

- `data/cvm/` (ZIPs do DFP, ~60 MB), `outputs/dossie_cache/` e `mutants/`: ignorados pelo git; apague à mão se quiser espaço.
- Branches remotos já integrados à `main`: `feat/cvm-fii-provider`, `feat/cvm-provider`, `feat/macro-provider`, `feat/ui-improvements`, `refactor/economic-fixes`, `refactor/macro-context`.
- A carteira local (`sentinela_v6.db`) está vazia; o recorte da carteira (`outputs/dossie-carteira.md`) só sai rodando `python scripts/dossie_fase2.py <banco com a carteira>` onde ela estiver (por exemplo, na cópia do `E:\`).
- Depois do push confirmado no GitHub: arquivar a cópia do `E:\` (zip no Google Drive) e apagar essa cópia, a venv do Windows e os arquivos não rastreados.

## Limites conhecidos

- `config.py` ainda faz rede no import (E-6); a suíte contorna com a semente do `conftest.py`, que é contorno, não correção.
- A guarda de rede só vê `socket.connect` do Python; clientes em C (como o `curl_cffi` de versões recentes do yfinance) não são vistos.
- A nota de mutação de `config.py` fica inflada pela fixture de sessão da Selic.
- O link do aviso do `app.py` aponta para `blob/main/docs/PLANO.md`; só abre depois do merge.
- No Gestor, as métricas (Sharpe, retorno, volatilidade) continuam na tela sem a divisão por ativo, até o F2C-9. Bug antigo: se nenhum ticker tiver histórico, `otimizar` devolve `None` e o `app.py` quebra com `AttributeError`.
- IF.data (Basileia e inadimplência) não respondeu na coleta do dossiê.
