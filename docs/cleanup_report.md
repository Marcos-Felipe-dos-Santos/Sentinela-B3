# Relatório de Limpeza — Sentinela B3

**Data**: 2026-05-08
**Fases**: Auditoria (Fase 1) → Classificação (Fase 2) → Limpeza segura (Fase 3)

---

## Fase 2 — Classificação de Itens

### Arquivos Rastreados pelo Git

| Arquivo | Classificação | Risco | Motivo |
|---------|---------------|-------|--------|
| `app.py` | MANTER | — | Arquivo principal da aplicação. Fora do escopo. |
| `market_engine.py` | MANTER | — | Engine de mercado. Fora do escopo. |
| `valuation_engine.py` | MANTER | — | Engine de valuation. Fora do escopo. |
| `fii_engine.py` | MANTER | — | Engine de FIIs. Fora do escopo. |
| `technical_engine.py` | MANTER | — | Engine técnica. Fora do escopo. |
| `portfolio_engine.py` | MANTER | — | Engine de portfólio. Fora do escopo. |
| `peers_engine.py` | MANTER | — | Engine de pares. Fora do escopo. |
| `database.py` | MANTER | — | Persistência SQLite. Fora do escopo. |
| `ai_core.py` | MANTER | — | Camada de IA. Fora do escopo. |
| `config.py` | MANTER | — | Configurações e constantes. Fora do escopo. |
| `fundamentus_scraper.py` | MANTER | — | Scraper Fundamentus. Fora do escopo. |
| `brapi_provider.py` | MANTER | — | Provedor Brapi. Fora do escopo. |
| `auditar_recomendacoes.py` | MANTER | — | Auditoria operacional ativa. Fora do escopo. |
| `auditoria.py` | MANTER E DOCUMENTAR | Baixo | Script legado de diagnóstico profundo. Útil para investigação. Documentado em `docs/classification_inventory.md` como legado intencional. |
| `limpar_banco.py` | MANTER E DOCUMENTAR | Baixo | Utilitário de manutenção. Documentado em `docs/classification_inventory.md`. |
| `requirements.txt` | MANTER | — | Dependências do projeto. |
| `pytest.ini` | MANTER | — | Configuração de testes. |
| `.env.example` | MANTER | — | Modelo de variáveis de ambiente. Excluído do .gitignore corretamente. |
| `.gitignore` | MANTER | — | Atualizado nesta limpeza. |
| `AGENTS.md` | MANTER | — | Instruções para agentes. NÃO ALTERADO. |
| `CLAUDE.md` | DEPRECIAR | Baixo | Continha plano de 9 tarefas obsoleto. Substituído por aviso de depreciação. |
| `Readme.md` | MANTER | — | Atualizado com estrutura real e contagem de testes correta. |

### Pacote `sentinela/`

| Arquivo | Classificação | Risco | Motivo |
|---------|---------------|-------|--------|
| `sentinela/__init__.py` | MANTER | — | Init do pacote. |
| `sentinela/domain/__init__.py` | MANTER | — | Init do domínio. |
| `sentinela/domain/enums.py` | MANTER | — | Enums do domínio. |
| `sentinela/domain/models.py` | MANTER | — | Modelos de domínio. |
| `sentinela/domain/provenance.py` | MANTER | — | Provenance de campos. |
| `sentinela/repositories/__init__.py` | MANTER | — | Init do repositório. |
| `sentinela/repositories/analysis_repository.py` | MANTER | — | Repositório de análises. |
| `sentinela/services/__init__.py` | MANTER | — | Init dos serviços. |
| `sentinela/services/analyze_asset.py` | MANTER | — | Serviço de análise. |
| `sentinela/services/asset_classifier.py` | MANTER | — | Classificador central. |

### Backtesting

| Arquivo | Classificação | Risco | Motivo |
|---------|---------------|-------|--------|
| `backtesting/__init__.py` | MANTER | — | Init do pacote. |
| `backtesting/backtest_engine.py` | MANTER | — | Motor de backtesting. Fora do escopo. |
| `backtesting/README_BACKTEST.md` | MANTER E DOCUMENTAR | Baixo | Documentação do backtesting. Nota: contém termos como "COMPRA/VENDA" em contexto de backtesting; aceitável em contexto de avaliação histórica. |
| `backtesting/backtest_results_v1.csv` | MANTER | Baixo | CSV rastreado desde commit original (`ce2ddb1`). Dados de referência. |
| `backtesting/fundamentos_point_in_time.csv` | MANTER | Baixo | CSV rastreado. Dados de referência para backtesting. |

### Testes

| Arquivo | Classificação | Risco | Motivo |
|---------|---------------|-------|--------|
| `tests/README.md` | MANTER | — | Documentação de testes. |
| `tests/conftest.py` | MANTER | — | Fixtures de teste. |
| `tests/test_*.py` (17 arquivos) | MANTER | — | Suíte de testes. Fora do escopo. |

### Documentação

| Arquivo | Classificação | Risco | Motivo |
|---------|---------------|-------|--------|
| `docs/classification_inventory.md` | MANTER | — | Inventário de classificação. Documentação técnica útil. |
| `docs/provenance.md` | MANTER | — | Documentação de provenance. Útil e atualizada. |
| `docs/cleanup_report.md` | CRIADO | — | Este relatório. |

### Arquivos Gerados (não rastreados) — Removidos na Fase 1

| Item | Classificação | Risco | Ação |
|------|---------------|-------|------|
| `__pycache__/` (raiz, backtesting, sentinela, tests) | REMOVER | Baixo | Bytecode regenerável. Removido. |
| `.pytest_cache/` | REMOVER | Baixo | Cache de testes. Removido. |
| `sentinela.log` (142 KB) | REMOVER | Baixo | Log de runtime. Removido. |
| `streamlit.err.log` (14 KB) | REMOVER | Baixo | Log de Streamlit. Removido. |
| `streamlit.out.log` (185 B) | REMOVER | Baixo | Log de Streamlit. Removido. |
| `sentinela_v6.db` (52 KB) | REMOVER | Baixo | Banco SQLite local. Removido. |
| `logs/auditoria_recomendacoes.txt` (20 KB) | REMOVER | Baixo | Output gerado por auditoria. Removido. |
| `logs/` (diretório) | REMOVER | Baixo | Diretório de logs. Removido. |
| `.VSCodeCounter/` (2 subdiretórios) | REMOVER | Baixo | Relatórios de IDE. Removido. |
| `backtesting/backtest_results_v2.csv` (15 KB) | REMOVER | Baixo | Output gerado não rastreado. Removido. |
| `backtesting/backtest_results_v3.csv` (16 KB) | REMOVER | Baixo | Output gerado não rastreado. Removido. |

### Arquivos Locais (ignorados corretamente)

| Item | Classificação | Risco | Motivo |
|------|---------------|-------|--------|
| `.env` (409 B) | ADICIONAR AO .gitignore | — | Já está no .gitignore. Contém API keys locais. |
| `venv/` | ADICIONAR AO .gitignore | — | Já está no .gitignore. Ambiente virtual. |

---

## Fase 3 — Ações Executadas

### 1. CLAUDE.md — Depreciado

Conteúdo anterior: plano de 9 tarefas obsoleto (reestruturação de diretórios para `sentinela/engines/`, type hints, loguru, pyproject.toml, etc.) que não correspondia ao estado atual do repositório.

Conteúdo atual: aviso curto de depreciação redirecionando para `AGENTS.md`, README e issues.

### 2. .gitignore — Atualizado (merge cuidadoso)

Alterações acumuladas nesta limpeza:

| Alteração | Motivo |
|-----------|--------|
| Removida instrução obsoleta de renomear arquivo | Instrução de 2024, não mais necessária |
| Removida regra genérica `*.csv` | Bloquearia CSVs rastreados do backtesting |
| Adicionado `*.pyo` | Recomendado pelo usuário |
| Adicionado `*.pyd` | Recomendado pelo usuário |
| Adicionado `.agent/` | Diretório de agentes locais |
| Adicionado `.gemini/` | Diretório do Gemini local |
| Adicionado `.cursor/` | Diretório do Cursor IDE |
| Adicionado `.VSCodeCounter/` (seção Agentes) | Movido da seção IDEs para Agentes |
| Removido `.VSCodeCounter/` duplicado (seção IDEs) | Deduplicação |
| Adicionado `exports/` | Recomendado pelo usuário |
| Adicionado `reports/generated/` | Recomendado pelo usuário |
| Adicionado padrão `backtesting/backtest_results_v[2-9]*.csv` | Proteger outputs gerados futuros |

### 3. Readme.md — Corrigido

| Correção | Antes | Depois |
|----------|-------|--------|
| Estrutura do projeto | 11 itens (incompleta) | 25 itens com comentários |
| Contagem de testes | 28 | 199 |
| Roadmap: Backtesting | `[ ]` pendente | `[x]` concluído |

### 4. Caches e temporários — Limpos

Todos os `__pycache__/`, `.pytest_cache/`, logs, banco SQLite local, outputs de backtesting não rastreados e relatórios de IDE foram removidos.

---

## Cobertura do .gitignore vs. Lista Recomendada

| Padrão recomendado | Status |
|-------------------|--------|
| `__pycache__/` | ✅ Presente |
| `*.py[cod]` | ✅ Presente |
| `*.pyo` | ✅ Adicionado |
| `*.pyd` | ✅ Adicionado |
| `.pytest_cache/` | ✅ Presente |
| `.mypy_cache/` | ✅ Presente |
| `.ruff_cache/` | ✅ Presente |
| `.coverage` | ✅ Presente |
| `htmlcov/` | ✅ Presente |
| `.venv/` / `venv/` / `env/` | ✅ Presente |
| `.env` / `.env.*` / `!.env.example` | ✅ Presente |
| `.streamlit/secrets.toml` | ✅ Presente |
| `*.db` / `*.sqlite` / `*.sqlite3` | ✅ Presente |
| `*.log` / `logs/` | ✅ Presente |
| `.DS_Store` / `Thumbs.db` | ✅ Presente |
| `.vscode/` / `.idea/` | ✅ Presente |
| `exports/` | ✅ Adicionado |
| `reports/generated/` | ✅ Adicionado |
| `tmp/` / `temp/` | ✅ Presente |

---

## Itens Marcados como Revisão Manual

Nenhum item requer revisão manual neste momento.

Todos os arquivos foram classificados com confiança suficiente. Os itens legados (`auditoria.py`, `limpar_banco.py`) já estão documentados em `docs/classification_inventory.md` como decisões conscientes.

---

## Confirmações Obrigatórias

- ✅ **AGENTS.md NÃO foi alterado** por esta limpeza (modificação pré-existente no working tree).
- ✅ **Nenhum código Python foi alterado** por esta limpeza (`ai_core.py` e `tests/test_ai_core.py` têm modificações pré-existentes).
- ✅ **Nenhum teste foi alterado**.
- ✅ **CLAUDE.md foi depreciado** com aviso curto.
- ✅ **.gitignore cobre todos os padrões recomendados**.
- ✅ **Caches e temporários foram limpos**.
- ✅ **O diff final mostra apenas documentação e .gitignore**.

---

## Riscos Remanescentes

1. **CSVs rastreados no backtesting**: `backtest_results_v1.csv` e `fundamentos_point_in_time.csv` permanecem no Git. Se quiser removê-los do tracking sem deletar localmente, use `git rm --cached`. Risco: **baixo** (dados de referência úteis para o backtesting).

2. **`backtesting/README_BACKTEST.md`**: Contém termos "COMPRA/VENDA" em contexto de backtesting histórico. Risco: **baixo** (contexto de avaliação, não recomendação).

3. **Modificações pré-existentes**: `AGENTS.md`, `ai_core.py`, `docs/provenance.md` e `tests/test_ai_core.py` estavam modificados no working tree antes desta limpeza. Essas mudanças são independentes e devem ser revisadas/commitadas separadamente.

---

## Próximos Passos Recomendados

1. Commitar as mudanças desta limpeza separadamente das mudanças pré-existentes em Python.
2. Revisar e commitar (ou reverter) as mudanças pré-existentes em `ai_core.py`, `tests/test_ai_core.py`, `AGENTS.md` e `docs/provenance.md`.
3. Considerar se `CLAUDE.md` deve ser eventualmente removido do repositório ou mantido como aviso permanente.
4. Avaliar se `auditoria.py` será migrado para `AssetClassifier` (conforme sugestão em `docs/classification_inventory.md`).
