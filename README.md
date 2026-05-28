# GEO Extractor

Ferramenta local para **GEO (Generative Engine Optimization)**: pesquisa referências, extrai insights, gera matérias longas para blog e artigos com arquitetura citável por IAs.

## Requisitos

- Python 3.11+
- Chave API (OpenAI, Anthropic, OpenRouter) ou Ollama local

## Instalação

```powershell
cd geo-extractor
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt   # opcional — testes
copy .env.example .env                # configure suas chaves
```

NLP avançado (opcional):

```powershell
python -m spacy download pt_core_news_sm
```

## Execução

**Interface principal (NiceGUI):**

```powershell
python main.py
```

Abre em `http://localhost:8080`.

**Interface legada (Streamlit):**

```powershell
python -m streamlit run app.py
```

## Configuração

Edite `config/ai_providers.yaml` para habilitar provedores e modelos.

Variáveis de ambiente — copie `.env.example` para `.env` e configure chaves de IA, API e integrações.

### Produção

| Variável | Descrição |
|----------|-----------|
| `GEO_ENV` | `development` ou `production` |
| `GEO_API_KEY` | Chave para `X-API-Key` ou `Authorization: Bearer` |
| `GEO_API_ENABLED` | `true` / `false` |
| `GEO_WEBHOOK_URL` | POST após gerar matéria via API |
| `GEO_CMS_PUBLISH_URL` | Endpoint HTTP para publicar no CMS externo |

**Docker:**

```powershell
docker compose up --build
```

**API REST** (mesmo processo que a UI):

| Método | Rota | Auth |
|--------|------|------|
| GET | `/api/health` | Não |
| GET | `/api/v1/stats` | Sim* |
| GET | `/api/v1/articles` | Sim* |
| GET | `/api/v1/articles/{id}` | Sim* |
| POST | `/api/v1/articles/generate` | Sim* |
| POST | `/api/v1/articles/publish` | Sim* |
| DELETE | `/api/v1/articles/{id}` | Sim* |

\* Obrigatória com `GEO_API_KEY` definida ou `GEO_ENV=production`.

## Estrutura

```
main.py              # UI NiceGUI + API REST
api/                 # Rotas FastAPI (/api/v1/*)
ui/                  # Abas (Dashboard, blog, histórico…)
core/                # GEO engine, índice IA
services/            # LLM, pipeline blog, webhooks, CMS
db/                  # SQLite (histórico local)
config/              # Provedores IA e produção
data/                # Base SQLite (gitignored)
output/              # Artefatos exportados
docs/                # Documentação técnica
tests/               # Testes unitários
```

## Testes

```powershell
pytest tests/ -q
```

## Documentação

- **[Manual do sistema](docs/MANUAL.md)** — guia completo de uso, Índice IA e fluxos
- [Resumo técnico](docs/RESUMO_TECNICO.md) — arquitetura, roadmap e limitações
- [Executável Windows](docs/EXECUTABLE.md) — `.\scripts\build_exe.ps1`
