# Fase 1 — Fundação: tipos, contratos e extração

Branch `v2/fase-1` · um commit por item, mais o de ativação da fila, sobre a tag `v2-fase-0` · Fila e diário: `docs/loop/historico/fase-1/`.
Plano: `docs/PLANO.md` (seção 6, "Fase 1"). **Não é consultoria financeira.**

A fase tira a fórmula dos quatro métodos de ação e dos dois do FII de dentro dos motores V1, para `sentinela/methods/`, com contrato, versão e tipos de unidade, **sem mudar o número que o app mostra**. Três mudanças de comportamento: duas num commit `fix:` próprio (F1-15 e F1-11) e a dos valores não finitos, que entrou com a extração (F1-3 a F1-8). O juiz da extração é o golden (2.247 casos, comparação exata).

## Itens e commits

| Item | Commit | Título |
|---|---|---|
| F1-15 | `8e71882` | fix: regenerate CVM ticker map from official registry |
| F1-11 | `1bcb275` | fix: stop valuation engine from reading technical signal |
| F1-16 | `d30df47` | test: pin valuation engine outputs on a boundary grid |
| F1-1 | `9420ebb` | feat: add unit types for money, ratios, rates and share counts |
| F1-2 | `e57d1ad` | feat: add valuation method contract with frozen inputs |
| F1-10 | `884e746` | test: enforce purity contract on valuation methods |
| F1-3 | `34068fc` | refactor: extract Graham method |
| F1-4 | `aadd2b0` | refactor: extract Bazin method |
| F1-5 | `e6ce15d` | refactor: extract Lynch method |
| F1-6 | `167b45b` | refactor: extract Gordon method |
| F1-7 | `c18340c` | refactor: extract FII yield method |
| F1-8 | `5e7bc97` | refactor: extract FII price-to-book lens |
| F1-9 | `86d54fa` | feat: add method registry pinned to V1 behavior |
| F1-17 | `4a023c9` | test: raise mutation score of valuation methods to 80% |
| F1-12 | `a28164c` | feat: add static traceability report v0 |
| F1-18 | `07d6760` | docs: sync agent instructions with extracted methods |
| F1-19 | `af89a57` | docs: propose phase 2A queue |
| F1-13 | `7238b37` | chore: clean up phase 1 residue |
| F1-14 | (este commit) | docs: add phase 1 summary and archive loop files |

## Testes, antes → depois

- **283 passed + 1 xfailed** (início da fase) → **653 passed + 1 skipped + 1 xfailed** (655 coletados, 44 módulos de teste). O skip é o gerador do golden (`GERAR_GOLDEN=1`). Nenhum teste existente foi removido ou enfraquecido; os que mudaram estão listados nos diários dos itens (F1-15: dois asserts da VALE3; F1-11: a chave `tecnico_negativo` e um comentário; F1-13: só imports, linhas em branco e um `removesuffix`).
- As seções A, B e C de `tests/test_financeiro_pre_refactor.py` ficaram iguais (`git diff --exit-code v2-fase-0`), e `tests/fixtures/golden_motores.jsonl` tem um único commit (`d30df47`).

## Mutation por módulo (config do `[tool.mutmut]`)

Nos motores, o par entre parênteses é mortos/sobreviventes; nos módulos novos, mortos/total (sem sobreviventes).

| Módulo | Linha de base (F0-3) | Depois do golden (F1-16) | Final |
|---|---|---|---|
| `valuation_engine` | 60,2% (377/249) | 86,1% (526/85) | **88,0%** (608/83) |
| `fii_engine` | não medido | 88,7% | **89,2%** (281/34) |
| `sentinela.domain.units` | — | — | **100%** (68/68) |
| `sentinela.methods.base` | — | — | **100%** (183/183) |
| `sentinela.methods.graham` / `bazin` / `lynch` / `gordon` | — | — | **100%** (81 / 61 / 109 / 111) |
| `sentinela.methods.fii_yield` / `fii_nav` | — | — | **100%** (51 / 16) |
| `sentinela.methods.registry` | — | — | **100%** (34/34) |
| **`sentinela.methods*` (pacote)** | — | — | **646/646 = 100%** (meta: 80%) |

Os sobreviventes dos dois motores são equivalentes ou só mudam log, e estão listados no diário do F1-16 (por exemplo, `QUALIDADE — AGUARDAR` é inalcançável: com upside ≤ 0 o score máximo é 60, abaixo de 75). O `[tool.mutmut]` ganhou `scripts/` em `also_copy` e passou a deselecionar o teste de import isolado do F1-10 só na mutação (o código instrumentado do mutmut importa `pathlib`/`urllib`).

## As três mudanças de comportamento

1. **F1-15 — mapa ticker → CD_CVM.** O mapa manual apontava, para a maioria dos tickers, para outra empresa (os fundamentos da CVM de uma empresa iam para o ticker de outra, com cara de dado oficial). O mapa agora é gerado do caminho oficial (FCA 2026 e 2025 → CNPJ → cadastro da CVM) por `scripts/gerar_mapa_cvm.py`, com a fixture `tests/fixtures/cvm_codigos_oficiais.csv`. **Efeito medido:** dos 50 tickers antigos, **43 mudam de código** (VALE3 passou de 19348, que é o Itaú, para 4170), **2 ficam** (PETR4 e o GOLL4, código da própria empresa), **5 saem** do mapa e voltam ao fallback (CSNA3, BRFS3, EMBR3, CPLE6, SOMA3); o mapa fica com 45. Único leitor em produção: `market_engine.py:481`.
2. **F1-11 — `tecnico_negativo`.** O `valuation_engine` lia essa chave, que nenhum código de produção escrevia: no app nada muda. **Efeito medido (no contrato de `processar`):** antes, com a chave, `riscos` ganhava "Técnico negativo" e a confiança caía 10; agora o resultado é idêntico ao de quem não a passa (`test_sinal_tecnico_nao_altera_resultado`). O golden não tem caso com a chave.
3. **F1-3 a F1-8 — valores não finitos.** NaN, infinito e Selic zero no FII agora levam à abstenção do método. Os `units.py` rejeitam valor não finito, que vira `None` antes de montar `MethodInputs`. **Efeito:** onde a V1 propagava um número (DY, ROE, LPA ou preço infinito davam `inf`; Selic zero no FII dava `ZeroDivisionError`), o método se abstém e, no FII, o motor segue o caminho "método não calculado" (NaN). Com NaN em P/L, P/VP, ROE ou DY, a V1 já não calculava, e o resultado é o mesmo. Não entrou num commit `fix:` próprio, e sim junto com os `refactor:` da extração; o golden não cobre esses casos. Detalhes na seção seguinte e nos diários F1-3 a F1-8.

## Divergências conhecidas da extração (fora do golden)

Os `units.py` rejeitam NaN e infinito, e o rito da fila manda converter valor não finito em `None` antes de montar `MethodInputs`. Onde a V1 já não calculava (NaN em P/L, P/VP, ROE, DY: comparações falsas), o resultado é o mesmo. Onde a V1 propagava um número (DY, ROE, LPA ou preço infinito dava `inf`; Selic zero no FII dava `ZeroDivisionError`), o método agora se abstém e, no FII, o motor segue o caminho "método não calculado" (NaN, como a V1 já exibia com DY NaN). Nada disso está no golden de propósito. Detalhes por método nos diários F1-3 a F1-8.

## Decisões pendentes

1. **Aprovar a fila da 2A** (`docs/loop/fila-fase2a-proposta.md`, 28 itens: o PLANO tinha 14, a proposta acrescenta F2A-15 a F2A-28). Responder: a **regra do golden** (a Fase 1 exigia um único commit no fixture; a proposta regenera só as linhas afetadas, com ferramenta de diff; opções a/b/c na seção final), a **[LIQUIDEZ]** e a tabela de **[CORREÇÕES]** (inclui a CSNA3).
2. **Pontos da revisão da proposta (F1-19)**, para ajustar antes de ativar: o F2A-8 soma depreciação da DVA (que inclui arrendamento depois do IFRS 16) mas a dívida líquida deixa o arrendamento de fora: declarar o regime; o F2A-8 não trata PL ≤ 0; o alerta de LPA de 10% do F2A-5 compara lucro consolidado e ações do fim do período com o LPA divulgado (lucro dos controladores, média ponderada, por classe) e pode disparar por definição, não por erro; o F2A-11 também tira o bônus de P/VP negativo (hoje só P/VP ausente ou zero vira 1,0); os proventos da DVA (F2A-7) são de competência, não data-ex.
3. **`.gitignore`:** resolvido em `05bb38f`. A linha 172, `data/`, também ignorava `sentinela/data/`, onde a 2A põe código; virou `/data/`.
4. **Vulture:** resolvido em `05bb38f`. O `--exclude venv,mutants,outputs,data` (`CLAUDE.md` e CI) virava `*data*` e pulava também `database.py`, `data_quality.py`, os testes deles e `sentinela/data/`; virou `"venv,mutants,outputs,$PWD/data/*"`. O `./data/*` não serve: o vulture compara o padrão com o caminho absoluto, e ele não casa com nada.
5. **Ruff:** o `pyproject.toml` lista as 413 regras do ruff 0.16.9; o CI instala `ruff>=0.16.9,<0.17`. Quem subir o ruff refaz a lista. Os três passos novos do CI (ruff completo, vulture, deptry) estão em modo relatório.
6. **Jules:** B4.1, B4.2, B4.3 e C-D precisam estar na `main` antes de ativar a 2A; o B4.2 só abre com o critério do E-8. O C-E só tinha janela nesta fase. A citação `tests/test_fundamentus_scraper.py:22` do `docs/jules-backlog.md:94` agora é `:24`.
7. **Decisões D5, D9 e D11 do ADR-0002** (efeito de cada recusa na fila da fase): D5 (`as_of` em `MethodInputs`, F1-2), D9 (relatório de rastreabilidade, F1-12), D11 (contrato de pureza, F1-10).
8. **`AGENTS.md`:** a "Fase atual" (arquivos travados) é do Marcos; a proposta da 2A traz o texto novo.

## Resíduos que ficaram para o Marcos

- **Cache de fundamentos do banco local** (o loop nunca roda o script contra o banco). Rodar no checkpoint, e sem `--aplicar` só lista:
  `python scripts/invalidar_cache_cvm.py --aplicar VALE3 ITUB4 BBDC4 ABEV3 B3SA3 WEGE3 RENT3 BBAS3 SUZB3 RADL3 LREN3 RAIL3 HAPV3 GGBR4 JBSS3 EQTL3 VIVT3 TOTS3 MGLU3 CMIG4 ELET3 CSAN3 HYPE3 KLBN11 ASAI3 SBSP3 TIMS3 ENEV3 NTCO3 LWSA3 RECV3 USIM5 AZUL4 COGN3 CYRE3 MRVE3 GOAU4 SLCE3 BRML3 BEEF3 PETZ3 DESK3 QUAL3 BRFS3 CSNA3 EMBR3 CPLE6 SOMA3`
- `outputs/dossie_cache/` (inclui o FCA de 2025 baixado no F1-15), `data/cvm/` (ZIPs do DFP, ~60 MB) e `mutants/`: arquivos não rastreados, ignorados pelo git.
- Branches remotos já integrados à `main` (lista no inventário, seção 9) e a decisão do destino do golden a partir da 2A.
- Removidos com `git rm` (recuperáveis pelo histórico): `reportlab` e `openpyxl` do `requirements.txt`, `docs/cleanup_report.md`.

## O que revisar primeiro

1. **O F1-15** (mapa) e o **F1-11**: são as duas mudanças de comportamento. Conferir principalmente os `fca_2025` (JBSS3, ELET3, NTCO3, AZUL4, PETZ3) e o GOLL4 mantido.
2. **A grade do golden** (`tests/golden_motores.py`, F1-16) e a mutação, da linha de base ao valor final (tabela acima).
3. **Gerar um relatório real** com `python -m sentinela.reports.rastreabilidade <TICKER>` e conferir a proveniência (sai em `outputs/rastreabilidade/`, fora do git).
4. **A proposta da 2A** e as decisões acima.
5. As divergências por valor não finito (seção acima) e o contrato do `sentinela/methods/base.py`.
