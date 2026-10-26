# Fase 2B — Taxa real, bancos e escopo

Branch `v2/fase-2b`, de `895fe0a` (ativação) a `f40c123` (F2B-5), mais o commit deste resumo (`e75ebe7`) e a fila de fechamento da auditoria externa (`4ee5bec` a F2B-69; seção "Fechamento da auditoria externa", abaixo). Fonte: o diário da fase (`docs/loop/historico/fase-2b/diario.md`) e o do fechamento (`docs/loop/historico/fase-2b/diario-fechamento.md`), que trazem o detalhe de cada item; os números abaixo são os de lá. Sem push pelo loop.

## O que revisar primeiro (plano final, §9, nesta ordem)

1. **Spread do FII e efeito no universo.** Agrupado dos 25 FIIs do universo (positivo/neutro/negativo): 5/7/13 antes do F2B-2 → 3/17/5 depois → 3/16/6 com o F2B-55 (VISC11 e XPLG11 voltam à lente; RBRP11 abstém por menos de 12 meses com DY e VP).  Constante datada de **3,5058%** (0,03505842448151178), mediana das 60 medianas mensais de outubro/2021 a setembro/2026, aceita pelo Marcos em 25/10/2026. Recalibrada com a ficha FII 1.2 (cotas fracionárias válidas): **3,5124%** (p25 3,1738%, p75 3,7345%; 30 a 44 fundos por mês; 2.351 fundos-mês válidos, eram 2.162), sem trocar a constante. Registro na ficha FII, §6a. Calibração ligada pelo ISIN do `geral` contra o COTAHIST, não pelo índice (desvio declarado no F2B-2).
2. **Decisões provisórias** (plano final, §1, regra 3), para confirmar ou reverter:
   - **F2B-54:** (1) janela de pareamento da conferência por evento com folga de 7 dias; (2) escala do ITR pelo acumulado do exercício, com o lucro dos controladores; (3) conflito no Informe abstém o mês inteiro; (4) `{}` do yfinance com D > 0 da B3 vira aviso de soma divergente.
   - **F2B-2:** (1) observação mensal da calibração = a da lente num as_of no dia seguinte ao último pregão; (2) ISIN em mais de um ticker fica fora (37); (3) célula vazia do `ativo_passivo` conta zero; (4) resposta genérica ou vazia da B3 é fonte indisponível; (5) **score do FII com a lente abstida = 50, neutro, sem número — aceita pelo Marcos em 25/10/2026 como exceção à decisão de 19/10**; (6) Selic não finita sem a comparação do score; (7) mês sem valor da B3 na conferência gera aviso; (8) `Data_Referencia` ilegível descarta o Informe do P/VP; (9) spread com a precisão da calibração; (10) o portão do DY da cascata antes da lente fica.
   - **F2B-4:** (1) a chave `modelo_bpp_proveniencia` ausente (chamada direta do motor) não é conferida; a cascata sempre a grava; (2) leitura das contas da CVM e seleção do IF.data continuam pelo setor; (3) a regra de seguradora olha a descrição com qualquer valor, inclusive zero; (4) o motor de FII marca a classe FII sem ler `dados['classe_ativo']`.
   - **F2B-32:** (1) banco com a lente abstida sai no formato de abstenção, sem o preço como valor; (2) companhia com mais de uma classe preferencial abstém em todas as classes, inclusive a ON (BRSR3); (3) inadimplência vale com a coleta até o as_of, sem o calendário oficial de publicação do IF.data; (4) seleção do IF.data pelo setor.
3. **Taxa real, antes → depois, com prêmio de 4%, 5% e 7%** (gate do PLANO): `docs/decisoes/f2b1-gordon-real.md`.
   - Exemplo da ficha (ABEV3): R$ 6,755660 / 6,161749 / 5,240356.
   - Gordon no universo (51 ações): elegíveis 17 antes → 12 depois nos três prêmios; mediana de valor/preço − 1 de −0,7185 / −0,7423 / −0,7792 depois.
   - Motor completo no universo (51 ativos por prêmio, 153 linhas), antes / depois:

     | Prêmio | Mediana do preço justo | Mediana do upside | Grupos positivo/neutro/negativo |
     |---|---|---|---|
     | 4% | R$ 15,82 / 11,76 | −14,7 / −2,5 p.p. | 3/22/26 → 7/19/25 |
     | 5% (vigente, D15) | R$ 14,44 / 11,30 | −16,2 / −2,5 p.p. | 3/21/27 → 7/19/25 |
     | 7% | R$ 12,30 / 11,26 | −22,6 / −9,9 p.p. | 3/19/29 → 7/19/25 |
   - Bazin: `docs/decisoes/f2b31-bazin-b3.md` (6% fixos, sem prêmio). Bancos: item 5.
4. **Golden de cada item** (seção "Mudanças de comportamento" abaixo).
5. **Bancos com a lente** (F2B-32). **Medição de diário, não produção:** cascata real de 25/10/2026, mas o Tesouro respondeu 429 por mais de 30 minutos e, com o cache de 20/10, a taxa real da cascata se abstinha (NTN-B a mais de 5 dias úteis). Para a medição, a NTN-B veio do CSV oficial em cache num as_of de 20/10/2026 21h UTC (data-base 15/10/2026, 6,7618%), com o IPCA de 2025 e o teto PIB do dia; o prêmio troca para 4%, 5% e 7%.

   | Banco | P/VP mercado | P/VP justificado (4% / 5% / 7%) | Preço justo (4% / 5% / 7%) | Upside 5% |
   |---|---|---|---|---|
   | BBAS3 | 0,746 | 0,270 / 0,246 / 0,209 | R$ 8,95 / 8,16 / 6,93 | −67,0% |
   | BBDC4 | 1,208 | 0,858 / 0,777 / 0,654 | R$ 14,47 / 13,11 / 11,03 | −35,7% |
   | BEES3 | 1,456 | 0,928 / 0,848 / 0,723 | R$ 6,47 / 5,91 / 5,04 | −41,7% |
   | ITUB4 | 2,604 | 1,565 / 1,420 / 1,198 | R$ 29,03 / 26,34 / 22,22 | −45,5% |

   - Os quatro saem com sinal negativo.
   - Abstêm:
     - BMEB4 e PINE4: base de ações.
     - BMGB4: payout.
     - BRSR3, BRSR5 e BRSR6: classes com direitos distintos.
     - SANB11: estrutura da DVA.
   - ITUB4 com prêmio de 5% reproduz o exemplo independente da ficha (P/VP 1,4206 e R$ 26,35).

## Itens e commits

| Item | Commit | Título |
|---|---|---|
| ativação | `895fe0a` | chore: activate phase 2B queue |
| F2B-35 | `a5321a8` | docs: sync agent instructions after the phase 2A closure |
| F2B-36 | `b82edef` | test: register the IF.data audit bugs and point open bugs to their items |
| F2B-7 | `164dd54` | test: move rate-dependent section A checks to section B |
| F2B-8 | `44d0666` | fix: keep non-positive CVM figures over stale positive values |
| F2B-10 | `2de32a1` | fix: infer share scale from consolidated earnings when controlling earnings abstain |
| F2B-11 | `64f561d` | fix: read the aggregate EPS line as the EPS of a single-class company |
| F2B-12 | `600d07b` | fix: apply one preferred-class rule to units and standalone shares |
| F2B-13 | `006d465` | fix: correct share species through the source corrections table |
| F2B-14 | `ae62790` | fix: cross-check recalculated EPS only against coherent reported EPS |
| F2B-16 | `9be1689` | fix: record FII figures per source for the cross-checks |
| F2B-17 | `98f6943` | fix: stop flagging FIIs as outside CVM company coverage |
| F2B-18 | `a60955a` | fix: discard implausible negative ROE at the provider boundary |
| F2B-20 | `19afb0f` | fix: refuse non-positive prices in both engines |
| F2B-37 | `144f23e` | fix: apply the controlling-interest rule to the trailing twelve months |
| F2B-38 | `773d897` | fix: pick the latest version of a restated FII monthly report |
| F2B-39 | `3b72de6` | fix: keep a valid dividend yield over an out-of-range later source |
| F2B-40 | `67e0116` | fix: treat an empty COTAHIST archive as a failed download |
| F2B-41 | `df95dbf` | fix: abstain the FII book-value lens on non-positive P/VP |
| F2B-42 | `5746843` | fix: abstain Graham on non-positive book value per share |
| F2B-21 | `4881b83` | docs: survey rates, FII yields and bank sources for phase 2B |
| F2B-43 | `60f59f9` | test: register bugs confirmed by the phase 2B survey |
| F2B-22 a F2B-26 | `44ad59e`, `079a45f`, `e42a5f1`, `089b1a0`, `9ef3dbb` | docs: methodology sheets (taxa real, Gordon, Bazin, FII, bancos) |
| F2B-28 | `b5e377f` | feat: add FII trailing distributions from the monthly report |
| marcador | `62c160b`, `19d46ac`, `e9e5534` | docs: revise and approve phase 2B methodology sheets |
| F2B-46 | `163ce93` | fix: enforce CVM input domains and completeness by statement model |
| F2B-27 | `0a9818a` | feat: add Tesouro Nacional bond rates provider |
| F2B-29 | `83711a8` | feat: add real-rate inputs and Fisher conversion to the method contract |
| F2B-47 | `60e61e2` | fix: enforce the approved local cutoff for Tesouro snapshots |
| F2B-48 | `576bc37`, `856c402` | fix: close audited unit dividend and Tesouro data gaps; distinguish valid zero yields |
| F2B-30 | `93b9ac9` | feat: expose the real cost of equity with provenance |
| F2B-49 | `adbd999` | chore: satisfy the macro provider lint gate |
| F2B-1 | `72f37a5`, `e7907fb` | docs: authorize additive Gordon inputs; fix: discount Gordon at the real cost of equity |
| F2B-31 | `73df2aa` | fix: take the Selic out of the Bazin rate |
| F2B-50 | `fbaa80c` | test: register the B3 trading-name search bug |
| F2B-51 | `f0ec966` | fix: keep the real-rate abstention reason in the macro provider |
| F2B-52 | `7fc816d`, `61ee2a3` | docs: stop on the profile source; fix: use one profile per asset from the B3 dividend yield |
| F2B-2 | `7d4f14e`, `f0017dc`, `c64d020`, `7ffe016` | docs: stop and approve the FII sheet 1.1; fix: compare FII yield with NTN-B plus the historical spread |
| F2B-53 | `50bff2a` | fix: count a fully covered B3 series without dividends as zero yield |
| plano final | `5c9ed55` | docs: record the phase 2B final plan and queue the audited fixes as F2B-54 |
| F2B-54 | `7e1dfb4` | fix: close the audited Bazin, FII report and Gordon base gaps |
| F2A-39 | `88596f2` | fix: map BTG Pactual unit through the source corrections table |
| F2B-4 | `c36bb1f`, `6e47344` | test: record pending F2B-4 scope checks; fix: enforce method scope by asset class and statement model |
| F2B-44 | `35e85a0` | fix: record IF.data provenance and the reference instant |
| F2B-3 | `48d01e4`, `ba04b53` | feat: add justified price-to-book lens for banks; chore: fix registry import order |
| F2A-10 | `76ffa31` | fix: abstain below the liquidity threshold |
| F2B-33 | `9490d66` | docs: sync agent instructions with phase 2B rates and scope |
| F2B-34 | `1ef0dc1` | docs: propose phase 2C queue |
| registros | `2d3d1d0`, `78ca067` | docs: record phase 2B blockers; record the decisions of 2026-10-25 |
| F2B-55 | `7ae1950` | fix: accept fractional FII quota counts from the Informe |
| F2B-32 | `e2f33a3` | fix: value banks with the bank lens |
| F2B-45 | `c922e4c` | fix: stop parsing Portuguese debt text in the stock engine |
| F2B-5 | `f40c123` | chore: clean up phase 2B residue |
| F2B-6 | `e75ebe7` | docs: add phase 2B summary and archive loop files |

## Fechamento da auditoria externa (25/10/2026)

Fila de fechamento montada a partir de `docs/loop/historico/fase-2b/auditoria-externa.md`, com as cinco decisões do Marcos de 25/10/2026 (registradas no `docs/decisoes/marcador-2b.md`): (1) decisões provisórias restantes ratificadas: exceções de proveniência nas chamadas diretas, IF.data pelo setor (pelo BPP na 2C, F2C-36), inadimplência sem o calendário oficial (calendário na 2C, F2C-37) e banco abstido sem número; (2) BRSR3 mantido em abstenção da companhia inteira, separação da ON na 2C (F2C-38); (3) célula vazia da composição do Informe vale zero só em registro da mesma versão com ao menos uma posição preenchida; (4) amortização vazia em complemento válido vale zero, `NaN`, texto ou negativo abstêm; (5) contraprova D27 refeita, sem dispensa genérica. Fila e diário em `docs/loop/historico/fase-2b/fila-fechamento.md` e `diario-fechamento.md`.

| Item | Entrega | Commit |
|---|---|---|
| ativação | chore: activate the phase 2B closing queue | `4ee5bec` |
| F2B-56 | docs: approve the FII sheet 1.3 on empty composition and amortization cells | `ed1ebfb`, `178b5fe` (complemento da edição parcial; desvio no diário) |
| F2B-57 | fix: treat any conflicting field of a same-version FII report as a conflict (BUG-2B-37 reaberto) | `e771323` |
| F2B-58 | fix: hold the FII lens to the same time cut as the real rate and the reports (BUG-2B-46) | `8ac69a9` |
| F2B-59 | fix: take the FII composition from the selected report version (BUG-2B-47) | `eadc9c4` |
| F2B-60 | fix: validate every book value in the FII window (BUG-2B-48) | `72d0938` |
| F2B-61 | fix: read empty FII amortization by the sheet 1.3 rule (BUG-2B-49) | `feff0b4` |
| F2B-62 | fix: return no number when the FII lens abstains (BUG-2B-50) | `c26f444` |
| F2B-63 | fix: read the statement model where the cascade writes it in the completeness check (BUG-2B-06 reaberto) | `8a69c3d` |
| F2B-64 | test: redo the D27 counterproof for F2B-54 and F2B-2 | `b548b08` |
| F2B-65 | docs: remeasure the FII spread after the closing fixes | `54ab5d6` |
| F2B-66 | docs: sync CLAUDE.md and the plan with the phase 2B delivery | `5e584ba` |
| F2B-67 | docs: add the phase 2B closing caveats to the phase 2C proposal | `e6d7da3` |
| F2B-68 | docs: record the phase 2B closing and archive the closing queue | `6b6f989` |
| F2B-69 | fix: close the phase 2B quick audit caveats (auditoria rápida do fechamento; BUG-2B-50 reaberto no `app.py`) | commit deste registro |

- **Testes:** 2.517 passed, 1 skipped, 14 xfailed → 2.568 (F2B-68) → **2.575 passed, 1 skipped, 14 xfailed** (F2B-69). Cada `fix:` registrou o bug em `tests/regressao/` com xfail estrito, mostrou o vermelho pelo motivo econômico com `--runxfail`, retirou a marca e atualizou o registro (D27).
- **Golden** (`--onde "caso['motor'] == 'fii'"`): F2B-58, 1 alterado, só o texto do motivo de `fii/sem-taxa-real`; F2B-62, 77 alterados, todos abstenções, só nas chaves `fair_value` e `upside` (saem; eram o preço e 0,0), sem mudança de rótulo ou score; os demais itens, idêntico. Nenhum caso fora do predicado.
- **Mutação:** `sentinela.data.rendimento_fii` 508/558 (91,0%) no F2B-60; `sentinela.data.fii_elegibilidade` 176/205 (85,9%); `cvm_fii_provider` (V1, sem meta) 445/545 (81,7%); `data_quality` (V1, sem meta) 437/531.
- **Ficha FII 1.3** (F2B-56): célula vazia da composição vale zero só em registro da mesma versão com ao menos uma posição preenchida; amortização vazia dentro de complemento válido vale zero, e `NaN` declarado, texto ou negativo abstêm; a leitura do CSV separa o vazio do `NaN` literal (F2B-61).
- **Contraprova D27** (F2B-64, `docs/loop/historico/fase-2b/contraprova-d27/`): a mesma entrada no commit pai e no do item, teste a teste. F2B-54: o pai falha nos 3 cenários da escala pelo valor, o item passa; dispensas escritas só para os dois avisos do perfil (sem número). F2B-2: no pai, todos os cenários dão R$ 97,36 pela Selic; no item, R$ 114,22 pela NTN-B + spread, e cada regra de elegibilidade abstém com o próprio motivo.
- **Spread medido** (F2B-65, só medição): **3,5124%** (p25 3,1738%, p75 3,7345%; 30 a 44 fundos por mês; 2.351 fundos-mês válidos), os mesmos números do F2B-55; a constante datada de 3,5058% fica (decisão de 25/10/2026). Só os motivos das exclusões se redistribuem (VP inválido 0 → 105).
- **Desvios e decisões provisórias para o Marcos:** (1) F2B-56, commit complementar `178b5fe`; (2) F2B-58: registro da taxa do mesmo dia local da análise; sem resposta da B3, a abstenção é a dos eventos indisponíveis; (3) F2B-63: a regressão passa por `_buscar_cvm`, não por `buscar_dados_ticker` inteira: **dispensa explícita do Marcos de 25/10/2026** (F2B-69), com o teste pela cascata inteira no F2C-43; (4) revisões reprovadas e corrigidas antes do commit: F2B-57 (comparação de formas; depois só a contagem de testes), F2B-58 (taxa antes do escopo, validade da taxa, motivos), F2B-59 (import sem uso), F2B-64 (3 rodadas; a 3ª só por texto), F2B-66 (texto), F2B-67 (cobertura e texto) e F2B-68 (texto); as reprovações só por texto foram corrigidas e commitadas sem nova parada (plano final, §1, regra 5).
- **Resíduos:** `app.py:271` mostrava "Valor Justo R$ 0.00" para o FII e o banco abstidos: corrigido no F2B-69 (abaixo); `auditoria.py:868/880` usa o preço como valor justo do FII abstido (F2C-8); demais na proposta da 2C (F2C-33 a F2C-47). Fora do git: `outputs/f2b65_spread*` e as worktrees temporárias da contraprova (removidas).

### Auditoria rápida do fechamento (F2B-69, 25/10/2026)

Codex, modo FASE, `e75ebe7..6b6f989`: **"pode seguir com ressalvas"** (não rodou a suíte: `No usable temporary directory`). As quatro ressalvas, fechadas no F2B-69 pelas decisões do Marcos da mesma data (detalhe no `diario-fechamento.md`):

1. **F2B-63:** dispensa explícita do teste pela cascata inteira; destino F2C-43.
2. **`app.py`:** sem `fair_value` numérico (abstenção), o card "Valor Justo" mostra "—" e o motivo (`metodos_usados` ou `riscos`), nunca R$ 0,00. Rito D27 pela regressão `test_bug_2b_50_reaberto_app_valor_justo_da_abstencao.py` (BUG-2B-50 reaberto): vermelho pelo R$ 0.00 com `--runxfail`, PASS sem a marca. Limitação: a função é lida do código-fonte e testada isolada; a tela desenhada e o resto do `app.py` seguem sem cobertura.
3. **Marcas xfail:** BUG-2B-02/03/05/07/08/09/10/11/21/29 com o item da 2C no `reason` (F2C-13 a F2C-21 e F2C-23), igual ao README e à proposta.
4. **`docs/PLANO.md`:** F2B-67 e F2B-68 entregues, com os commits, e a linha do F2B-69.

Ficam para o Marcos: o xfail de `tests/test_database_posicoes.py` (venda parcial) sem ID nem destino; e o preço como valor justo quando nenhum método de ação devolve número (`valuation_engine.py:466`) e no caminho DISTRESSED (`:252`), que não é ausência e ficou fora da decisão 2.

## Testes antes → depois

- **Início da fase:** 1.362 passed, 1 skipped, 18 xfailed (F2B-35).
- **Fim da fila da fase:** **2.517 passed, 1 skipped, 14 xfailed** (depois da fila de fechamento, 2.568; depois do F2B-69, 2.575), depois do F2B-5, que tirou os testes do que saiu.
- **Gates:** Ruff CI e completo em `sentinela/methods` e `sentinela/data` verdes. O `ruff check .` completo terminou em 169 (era 170 antes do F2B-5).
- **Bugs:** registrados na fase com regressão em `tests/regressao/`, de BUG-2B-01 a BUG-2B-45, e corrigidos conforme o registro; a fase também corrigiu BUG-2A-01 e BUG-2A-10 a BUG-2A-23. Abertos com xfail estrito e destino na proposta da 2C: BUG-2B-02, 03, 05, 07, 08, 09, 10, 11, 21 e 29.

## Mutação (mutmut 3, mortos/total)

- `sentinela.methods*` no fim da fase (F2B-5): 1.183/1.269 (93,2%).
  - base 217/220; Bancos 334/388; Bazin 72/72; P/VP do FII 26/26; Rendimento do FII 84/90; Gordon 216/239; Graham 91/91; Lynch 109/109; registry 34/34.
- Módulos novos ou alterados de `sentinela/data/`, na última medição de cada um:

  | Módulo | Mortos/total | % |
  |---|---|---|
  | `gordon_cvm` | 503/579 | 86,9% |
  | `providers.ifdata` | 307/343 | 89,5% |
  | `liquidez` | 207/222 | 93,2% |
  | `rendimento_fii` | 398/431 | 92,3% |
  | `fii_elegibilidade` | 172/189 | 91,0% |
  | `spread_fii` | 75/78 | 96,2% |
  | `providers.b3_fundos` | 33/38 | 86,8% |
  | `proventos_b3` | 629/662 | 95,0% |
  | `providers.tesouro` | 354/423 | 83,7% |
  | `providers.macro` | 580/713 | 81,4% |
  | `providers.b3_cotahist` | 280/311 | 90,0% |
  | `acoes_cvm` | 494/549 | 90,0% |
  | `series_cvm` | 401/430 | 93,3% |
  | `referencia` (pacote) | 1.340/1.512 | 88,6% |
  | `proveniencia` | 156/188 | 83,0% |
  | `domain.units` | 139/163 | 85,3% |

- Módulos V1 tocados: medidos só onde o diário registra, sem meta.

## Mudanças de comportamento e golden

Para cada item: predicado → alterados / incluídos / removidos / fora do predicado. O detalhe está no diário.

| Item | Mudança | Golden |
|---|---|---|
| F2B-20 | preço negativo não é analisado | `preco_atual < 0` → 2 / 0 / 0 / 0 |
| F2B-1 | Gordon real (DVA dos controladores, Fisher, teto PIB, base acionária) | Gordon nas saídas → 1.221 / 36 / 0 / 0 |
| F2B-31 | Bazin a 6% fixos, pelo DY bruto da relação B3 | Bazin nas saídas → 1.518 / 36 / 0 / 0 |
| F2B-2 | rendimento do FII sobre NTN-B + spread (sai a Selic líquida do preço justo) | motor FII → 182 / 23 / 0 / 0 |
| F2A-10 | abstenção abaixo da liquidez mínima | `False` → 0 / 27 / 0 / 0 |
| F2B-55 | cotas fracionárias válidas | motor FII → 0 / 0 / 0 / 0 |
| F2B-4 | escopo por classe e modelo do BPP; seguradora pelo critério ampliado; banco em abstenção até o F2B-32 | motor ações → 0 / 30 / 0 / 0 |
| F2B-32 | banco pela lente de P/VP justificado; inadimplência do IF.data só para leitura | ações com `modelo_bpp == 'banco'` → 4 / 60 / 0 / 0 |
| F2B-45 | sem conversão de dívida em texto; avisos de alavancagem e de liquidez fora de `riscos`; texto pt-BR da abstenção de liquidez | 1.699 alterados (1.659 só o campo novo; 19 de dívida em texto; 9 de liquidez não medida; 12 de liquidez abaixo do mínimo), 0 fora do predicado ampliado em 25/10 |
| F2B-5 | limpeza (Selic fora do `MethodInputs` e do motor de ações; NTN-B antiga; script de invalidação) | inalterado |

- Itens sem mudança de golden: os demais `fix:` da fase, documentados um a um no diário.
- Bytes do golden: 926.957 (antes do F2B-1) → 1.355.292.
- Efeito do F2B-4 no índice: 455 STOCK/UNIT → 346 empresa, 22 banco, 9 seguradora e 78 sem BPP consolidado.
  - Os 78 sem BPP consolidado publicam só demonstrações individuais (ASAI3 no universo) e se abstêm de todos os métodos.
  - Seguradoras: BBSE3, PEAB3, PEAB4, IRBR3, PSSA3, QUAL3, HAPV3, RDOR3 e SAUD3.

## Fichas aprovadas e auditorias

- **Fichas:** taxa real 1.1 e Gordon 1.1 (20/10/2026), Bazin 1.2 (20/10), FII 1.2 (25/10) e 1.3 (25/10, F2B-56), bancos 1.1 (20/10).
  - As versões 1.0 vieram das auditorias FICHA do Claude sobre as versões 0.2 e 0.3 (D30), com o veredito "pode seguir" na 0.3.
  - O registro está em `docs/decisoes/marcador-2b.md`.
- **Auditorias de item:**
  - Gemini, parecer completo e HEAD `60e61e2`, com os aceites incorporados à fila.
  - Codex, 2ª auditoria FASE (BUG-2B-33 a 37, no F2B-54).
  - Claude, D30 sobre os commits do Codex de 21 e 22/10: "pode seguir com 2 ressalvas", fechadas no F2B-45.
- **Auditoria de fechamento (25/10/2026):** Codex, modo FASE, "não pode seguir"; Gemini, modo FASE, "aprovado com ressalvas"; consolidação do Claude (chat) com as decisões do Marcos da mesma data em `docs/loop/historico/fase-2b/auditoria-externa.md`. Bloqueios corrigidos na fila de fechamento (abaixo).

## Decisões pendentes

- **Desvios declarados para o aceite do Marcos:**
  - rito D27 nos testes da escala do F2B-54 e nos testes do método e da seção B do F2B-2: contraprova refeita no F2B-64 (decisão 5 de 25/10/2026; seção "Fechamento da auditoria externa"); ficam para o aceite do Marcos só as dispensas escritas teste a teste em `contraprova-d27/README.md`;
  - BUG-2B-33 a 38 do F2B-54, fora da regra de 15/10/2026 (registrados no próprio item);
  - F2B-43: dois pontos confirmados sem teste (BTCI11/TRPL11 e proventos com um só componente), a conferir no marcador;
  - F2B-2, diferenças (i) a (vi): ligação pelo ISIN do `geral`, não pelo índice; calibração sem o limite de 5 dias úteis da NTN-B; preço do último pregão em que o fundo negociou; grade do spread fora do golden; `FII_SPREAD_CALIBRACAO` sem as exclusões (estão na ficha); preço justo e score com DYs de fontes diferentes (2C);
  - F2B-3: desvio do safe-commit (I001 oculto, corrigido em `ba04b53`).
- Decisões provisórias da seção "O que revisar primeiro": as restantes foram ratificadas pela decisão 1 de 25/10/2026 (seção "Fechamento da auditoria externa"); ficam abertas só as provisórias da fila de fechamento, listadas lá.
- Escopo de seguradora pelo critério ampliado: HAPV3, RDOR3 e SAUD3 (saúde) e QUAL3 (administradora de benefícios) ficam sem os métodos de empresa.
- Proposta da 2C (`docs/loop/fila-fase2c-proposta.md`), ainda não auditada nem ativada. Os resíduos abaixo e as ressalvas da auditoria de fechamento já têm destino nela (F2B-67: F2C-33 a F2C-47 e aceites adicionais no F2C-8, F2C-10 e F3-6):
  - classe vazia;
  - `as_of` sem fuso no motivo do BPP;
  - `Bancos.requires` com classe e modelo;
  - linha "DFP da lente de bancos" com o fato abstido;
  - motivo da CVM no aviso de alavancagem;
  - `np.int64`;
  - texto de `LIMITES` sobre a Selic no relatório de ação;
  - `caso["selic"]` do golden de ações;
  - `monkeypatch` sem uso no BUG-2B-27;
  - constantes `GORDON_*` sem leitor.
- **Sincronizado no F2B-66:** a `CLAUDE.md`, o `docs/PLANO.md` e o `AGENTS.md` (fora da "Fase atual") descrevem o F2B-4 e o F2B-32 como entregues. A seção "Fase atual" do `AGENTS.md`, que é do Marcos, ainda lista `tests/test_invalidar_cache_cvm.py`.

## Resíduos para o Marcos

- **Caches:**
  - `outputs/levantamento_cache/f2b21/` (565 MB): `scripts/calibrar_spread_fii.py` lê os Informes, o COTAHIST e o Tesouro dali para reproduzir a calibração.
  - `data/macro/` está em uso e não deve sair.
  - `data/tesouro/` não existe.
- **Saídas locais:** `outputs/f2b2_*`, `outputs/f2b55_spread.*`, `outputs/f2b32_bancos*.json`.
- **Cache de fundamentos (SQLite):** limpar inteiro no [DECISÃO], passo 3, porque o script por ticker saiu.
- **Scripts históricos:** `scripts/dossie_fase2.py` e `scripts/levantamento_fase2b.py` não rodam no HEAD; reproduzem-se na tag da Fase 0 e no commit `4881b83`.
