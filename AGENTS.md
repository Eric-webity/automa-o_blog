# Guia para agentes e desenvolvedores

Base estável do **GEO Extractor (Content Studio)**. Siga estas regras antes de adicionar features.

## Entrada e camadas

| Camada | Pasta | Responsabilidade |
|--------|-------|------------------|
| Entrada | `main.py` | NiceGUI + registo da API |
| UI | `ui/` | Páginas, abas, auth, componentes visuais |
| API | `api/` | REST FastAPI (`/api/health`, `/api/v1/*`) |
| Serviços | `services/` | IA, pipelines, fetch, batch, analytics, jobs |
| Motor GEO | `core/` | Esqueleto, índice, insights, FAQ JSON-LD (sem HTTP/DB) |
| Dados | `db/` | Modelos SQLAlchemy, repositórios, migrações SQLite |
| Config | `config/` | Paths, produção, YAML de provedores |

## Regra de dependências (obrigatória)

```
ui   →  services  →  core
api  →  services  →  db
```

- **Não** importar `modules/` nem `pipelines/` em código novo (`ui/`, `api/`, `services/`, `main.py`, `db/`).
- `core/` não importa `services/`, `ui/`, `api/` nem `db/`.
- Persistência de matérias: `ArticleRepository(user_id=…)` via `ui.auth.article_repository()` na UI.

## Onde colocar código novo

| Tarefa | Local |
|--------|--------|
| Nova aba ou rota | `ui/pages/` + `ui/tab_*.py` + `ui/pages/routes.py` |
| Componente reutilizável | `ui/components/` |
| Endpoint REST | `api/routes.py` + `api/schemas.py` |
| Orquestração (gerar, lote, URLs) | `services/*_pipeline.py` ou `services/*.py` |
| Regra GEO pura | `core/` |
| Tabela ou query SQLite | `db/models.py` + `db/repository.py` |
| Variável de ambiente | `.env.example` + `config/production.py` se for produção |
| Prompt editorial | `skills/*.md` |
| Validação / checklist | `services/article_validation.py`, `ui/components/geo_checklist.py`, `brief_preflight.py`, `article_review_panel.py` |

## Pastas legadas (só compatibilidade)

| Pasta | Uso |
|-------|-----|
| `modules/` | Reexportações finas → `core/` / `services/`. **Não editar lógica aqui.** |
| `pipelines/` | Reexportações → `services/*_pipeline.py`. |
| `legacy/` | Streamlit congelado. Sem features novas. |

## Sessão e produção

- Login: `ui/auth.py` (`user_id` na sessão). Várias contas: `docs/CONTAS_E_HISTORICO.md`, `ui/session_scope.py`.
- Produção: `GEO_ENV=production`, `GEO_STORAGE_SECRET` (≥32 chars) — ver `docs/PRODUCAO_SESSOES.md`.
- API: `GEO_API_KEY` + `docs/ORGANIZACAO_E_PROXIMOS_PASSOS.md`.

## Testes e verificação

```powershell
cd automa-o_blog
pytest tests/ -q
```

Teste de fronteira: `tests/test_project_structure.py` (proíbe `modules` em `ui/`, `api/`, `services/`, `main.py`).

## Documentação

| Ficheiro | Conteúdo |
|----------|----------|
| [docs/ORGANIZACAO_E_PROXIMOS_PASSOS.md](docs/ORGANIZACAO_E_PROXIMOS_PASSOS.md) | Roadmap e estado das fases |
| [docs/MANUAL.md](docs/MANUAL.md) | Utilizador final |
| [docs/PRODUCAO_SESSOES.md](docs/PRODUCAO_SESSOES.md) | Segredo de sessão |
| [README.md](README.md) | Instalação e estrutura resumida |
