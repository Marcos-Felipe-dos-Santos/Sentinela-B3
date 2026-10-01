# Diário do loop — Fase 0

## Estado inicial
- Branch `v2/fase-0`, `which python` aponta para `venv/bin/python`.
- Arquivos obrigatórios presentes (CLAUDE.md, AGENTS.md, PLANO, ADR 0001 e 0002, auditoria).
- `python -m pytest -q`: 255 passed em 1,70 s.
- Já existiam alterações não commitadas de bootstrap (CLAUDE.md, AGENTS.md, PLANO.md, adr/) feitas antes do loop. Ficam fora dos commits dos itens, salvo quando o item as altera.

### F0-0 — docs: add red team audit with normalized finding IDs
- **Status:** sucesso
- **O que foi feito:** cada um dos 37 blocos de achado ganhou `[ID: …]` no cabeçalho (E-1 a E-22 e F-1 a F-15); a tabela de menor severidade foi renumerada para F-16 a F-30 e ordenada; referências cruzadas (F12, F25, F3, F4/F5/F9, F-24) apontam para os IDs novos; tabela "ID antigo → ID novo" no fim.
- **Dificuldades:** os blocos não tinham ID; a ordem do documento é a única fonte da numeração. Conferi E-1 a E-22 contra as referências existentes (E-10 provider FII, E-11 cloudscraper, E-12 CI, E-19 auto_adjust, E-21 migração).
- **Como resolvi:** script único que insere os IDs por posição e renumera a tabela. Antigos F-15 a F-23 viram F-16 a F-24; F-25 a F-30 não mudam; o F-24 antigo (só no Veredito) vira F-14.
- **Testes:** 255 → 255 (só documentação).
- **Resíduos:** nenhum.
- **Decisões que ficaram para o Marcos:** nenhuma.
- **Para o Marcos revisar:** `CLAUDE.md`, `AGENTS.md`, `docs/PLANO.md` e os ADRs citam apenas F-25 e F-28 (PLANO), que não mudaram; nenhum deles foi alterado. A linha 18 desta fila ainda diz "o que o Veredito chama de F-24", descrição histórica que fica como está. A auditoria entra no git inteira (estava não rastreada).
  O texto de correção do F-15 sugere o rótulo "Alocação sugerida", hoje proibido pelo `CLAUDE.md`; o documento é histórico e não foi editado, e nenhum item futuro deve usar essa correção como especificação. A reordenação da tabela F-16 a F-30 não alterou o texto das linhas, mas o diff não prova isso (arquivo novo no git).
- **Bloqueio (resolvido):** o `/safe-commit` exigia `ruff check .` completo (301 erros antigos). A skill passou a usar o gate do CI (`--select E9,F63,F7,F82`), verde; o loop foi retomado sem mudar o conteúdo do item.

### F0-1 — docs: sync agent instructions and plan with codebase
- **Status:** sucesso
- **O que foi feito:** conferi contagens de linha dos 14 módulos da tabela (todas batem), as linhas citadas, as regras econômicas (Selic × 0,85 no FII, k = Selic + 7% no Gordon, normalizadores de DY) e os fatos de código (`CVMFIIProvider` não injetado em `app.py:158`, `cloudscraper` fora do `requirements.txt`, `tecnico_negativo` só lido, `dados.update(analise)` em `app.py:227`, `FII_MANUAL_FALLBACK` em `config.py:73` × `VACANCIA_CONHECIDA` em `fii_engine.py`, mapas com 50 ações e 30 FIIs, Markowitz 40/60 em `portfolio_engine.py:121-123`, "Alocação Sugerida" em `app.py:516`).
- **Divergências corrigidas (só nos documentos):**
  1. `market_engine.py:377` → `377-379` (a regra `> 1` está na 378) em `CLAUDE.md` e ADR 0001.
  2. Armadilha 15 / PLANO (F2A-1 e tabela): "classe lê coluna inexistente" não se sustenta. `CVMTickerMap` só é instanciada em testes e `refresh` nunca preenche `ticker`. A leitura de coluna da auditoria não foi verificada (exige rede).
  3. Tempo da suíte: ~1,4 s → ~2 s (medido 1,7–2,1 s) em `CLAUDE.md`, `AGENTS.md` e ADR 0001.
  4. ADR 0001: "sem rede" não vale, o import de `config` chama o BCB (armadilha 8); texto ajustado.
  5. Armadilha 9: `ntnb_longa` é lido por `cost_of_equity_real`; "sem consumidor" vale fora dos testes.
- **Correções da 1ª revisão:** ADR 0001 ("sem rede" em Alternativas e caminho antigo da auditoria nas linhas 5 e 189), ADR 0002 ("Quatro" → "Cinco coisas mudaram"), PLANO F2A-1 ("nunca instanciada fora dos testes"), AGENTS.md (preço: brapi só se o yfinance falhar; BRAPI_TOKEN marcado como não verificado). O BOM UTF-8 saiu do início de `CLAUDE.md` e `AGENTS.md` ainda no bootstrap, sem efeito de conteúdo.
- **Correções da 2ª revisão:** armadilha 7 (`_limpar_valor` tem teste, fraco; só `adicionar_posicao` está sem teste — divergência 6, a frase vinha da auditoria desatualizada); regra de `_normalizar_dy` (`>0.25` devolve `(0.0, False)`, não só "suspeito"); AGENTS.md alinhado ao CLAUDE.md sobre a interface FastAPI.
- **Para o Marcos (extra):** o invariante "DY em [0, 0.30]" do F0-3 não bate com o corte de 0,25 do código; a data da Selic (13,75% em 16/09/2026) do ADR 0002 não foi verificável; o ADR 0001 mantém tabelas de fase históricas (vale a ordem do PLANO).
- **Dificuldades:** `.env.example` não pôde ser lido (permissão negada); a ausência de `BRAPI_TOKEN` nele ficou sem reconferir.
- **Como resolvi:** não li o arquivo, para respeitar a regra de nunca tocar em `.env*`; fica registrado.
- **Testes:** 255 → 255 (só documentação).
- **Resíduos:** nenhum.
- **Decisões que ficaram para o Marcos:** nenhuma.
- **Para o Marcos revisar:** a afirmação sobre `BRAPI_TOKEN` ausente do `.env.example` e a "coluna inexistente" do atualizador, que só se confirma com rede. Este commit também inclui `AGENTS.md`, `CLAUDE.md`, `docs/PLANO.md` e `docs/adr/` inteiros, que estavam não commitados desde o bootstrap.

### F0-2 — chore: add CI gate, strict xfail, hermetic fixtures and dev tooling
- **Status:** sucesso
- **O que foi feito:** (a) `.github/workflows/ci.yml` (push e pull_request, Python 3.13, gate `ruff check --select E9,F63,F7,F82 .` + `pytest tests/`, sem cobertura). (b) `pytest.ini`: `xfail_strict = true`, `--strict-markers` e sete marks (`preservar`, `quebra_esperada`, `invariante` e um por achado da seção B: `f4_gordon_nominal`, `f9_fii_selic`, `f12_alavancagem_total`, `f15_markowitz_um_ano`). (c) Semente da Selic no `tests/conftest.py`. (d) Guarda de rede por `socket.connect`. (e) `requirements-dev.txt`; `pytest-cov` saiu do `requirements.txt`. (f) `[tool.mutmut]` em `pyproject.toml`. (g) `mutants/` no `.gitignore`. (h) Comandos de mutação conferidos e armadilhas 7 e 8 do `CLAUDE.md` atualizadas.
- **Decisão (c):** o `MACRO` nasce no import de `config`, que acontece na coleta, antes de qualquer fixture. Por isso a semente é um `mock.patch("requests.get")` no carregamento do `conftest.py`, que responde só à URL da série 432 do BCB e levanta exceção em qualquer outra, sem mexer em `config.py`. A fixture de sessão `_selic_semeada` confere a semente. O valor semeado (14,75%) é igual ao `SELIC_FALLBACK`, então nenhum resultado muda. Comentário no `conftest.py` aponta para o E-6: é contorno, não correção.
- **Decisão (d):** o código de produção engole exceções genéricas, então bloquear o `connect` não bastava. A guarda registra a tentativa; a fixture `_sem_rede` derruba o teste e `pytest_sessionfinish` derruba a sessão. AF_UNIX fica liberado.
- **Verificações do aceite:** suíte hermética sem aviso do BCB no stderr; um teste descartável que abre conexão falhou com "Teste tentou acessar a rede" e foi removido; mark inexistente vira erro de coleta; um XPASS descartável falha (`xfail_strict`); `python -m mutmut run "technical_engine*"` termina e `export-cicd-stats` gera os números; `git status` limpo depois da mutação (`mutants/` ignorado).
- **Dificuldades:** o mutmut 3.8 avisou que `tests_dir` e `paths_to_mutate` estão obsoletos. **Como resolvi:** usei `source_paths` e `pytest_add_cli_args_test_selection = ["tests/"]`. `mutmut`, `vulture` e `deptry` não estavam na venv; instalei com pip (as versões ficam no `requirements-dev.txt`).
- **Testes:** 255 → 255, 0 falhas. Mutação de `technical_engine*`: ver números abaixo.
- **Resíduos:** nenhum. `mutants/` e `.pytest_cache` ficam ignorados.
- **Decisões que ficaram para o Marcos:** nenhuma.
- **Para o Marcos revisar:** o `AGENTS.md` cita os comandos de mutação, que agora funcionam (o `README` não os cita). Limites conhecidos, apontados na revisão: a guarda de rede só vê `socket.connect` do Python (clientes em C, como o `curl_cffi` do yfinance recente, passam); a fixture `_selic_semeada` faz mutantes de `get_selic_atual` contarem como mortos sem teste real, inflando a nota de `config.py`; e rede tocada na coleta falha a sessão sem imprimir o endereço. O CI instala só `requirements.txt` e `ruff`, não o `requirements-dev.txt`.
- **Mutação (technical_engine\*, antes do F0-3):** 90 mortos, 357 sobreviventes de 6800 mutantes gerados no projeto (só o módulo técnico foi executado). Linha de base, sem meta.
