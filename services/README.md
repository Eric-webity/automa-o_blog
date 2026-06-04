# `services/` — regras de negócio

Camada entre a UI/API e o motor GEO (`core/`). Pode usar `db/`, HTTP, IA e ficheiros em `output/`.

## Pipelines principais

| Módulo | Função |
|--------|--------|
| `blog_pipeline.py` | Gerar matéria para blog + persistir histórico |
| `url_pipeline.py` | Processar lista de URLs |
| `batch_csv.py` | Lote CSV → vários `.md` |
| `background_jobs.py` | Fila para tarefas longas (UI não bloqueia) |

## Outros módulos frequentes

| Módulo | Função |
|--------|--------|
| `ai_manager.py` | Provedores de IA |
| `article_fetcher.py` + `url_security.py` | Fetch de URLs (anti-SSRF) |
| `blog_publisher.py` | Salvar/atualizar matéria no SQLite |
| `analytics.py` | Métricas do dashboard |
| `storage.py` | Export `.md` / `.json` em `output/` |

## Subpacote `blog/`

Geração editorial: `brief`, `research`, `generator`, `llm_writer`, `local_writer`, `prompts`.

Não importe `ui/` nem `nicegui` aqui.
