# GEO Extractor

Ferramenta local para **GEO (Generative Engine Optimization)**: pesquisa referências, extrai insights, gera matérias longas para blog e artigos com arquitetura citável por IAs.

## Comece aqui (onboarding)

| Passo | Ação |
|-------|------|
| 1 | Instale dependências e copie `.env.example` → `.env` (secção abaixo) |
| 2 | Execute `python main.py` e abra o **Content Studio** no navegador |
| 3 | Configure provedores de IA em **Settings** ou em `config/ai_providers.yaml` |
| 4 | Use a aba **Criar matéria** para o fluxo principal (tema + URLs de referência) |

**Mapa do projeto (recomendado para quem vai desenvolver):**  
→ **[Organização e próximos passos](docs/ORGANIZACAO_E_PROXIMOS_PASSOS.md)** — o que cada pasta faz, regras de import, roadmap e estado da refatoração.

**Uso diário (sem código):**  
→ [Manual do sistema](docs/MANUAL.md)

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

**Interface principal — Content Studio (NiceGUI):**

```powershell
python main.py
```

Abre no navegador (porta livre a partir de 8080; ver mensagem no terminal).

**Interface legada (Streamlit, sem manutenção ativa):**

```powershell
python -m streamlit run legacy/app.py
```

Ver [legacy/README.md](legacy/README.md). O ficheiro `app.py` na raiz só exibe um aviso — use `main.py` ou o comando acima.

## Configuração

Edite `config/ai_providers.yaml` para habilitar provedores e modelos.

Variáveis de ambiente — copie `.env.example` para `.env` e configure chaves de IA, API e integrações.

### Produção

| Variável | Descrição |
|----------|-----------|
| `GEO_ENV` | `development` ou `production` |
| `GEO_STORAGE_SECRET` | Segredo que assina cookies de sessão da UI (**obrigatório** em produção, ≥32 caracteres). Ver [docs/PRODUCAO_SESSOES.md](docs/PRODUCAO_SESSOES.md) |
| `GEO_API_KEY` | Chave para `X-API-Key` ou `Authorization: Bearer` |
| `GEO_API_ENABLED` | `true` / `false` |
| `GEO_WEBHOOK_URL` | POST após gerar matéria via API |
| `GEO_CMS_PUBLISH_URL` | Endpoint HTTP para publicar no CMS externo |
| `GEO_BROWSER_FETCH` | `auto` (padrão), `always` ou `never` — fetch headless para páginas em JavaScript |
| `GEO_URL_CACHE_TTL_HOURS` | Cache de URLs já buscadas (horas; `0` desativa) |

**Sites em JavaScript (Playwright):** após `pip install -r requirements.txt`, instale o Chromium:

```powershell
playwright install chromium
```

Com `GEO_BROWSER_FETCH=auto`, o sistema tenta HTTP primeiro e usa o navegador headless se a página vier vazia ou com pouco texto.

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

## Estrutura do projeto (alvo)

```
automa-o_blog/
├── main.py                 # Entrada única: Content Studio (NiceGUI) + API no mesmo processo
├── app.py                  # Aviso de redirecionamento (use main.py)
│
├── ui/                     # Interface: abas, login, estilos
│   ├── constants.py        # Rótulos partilhados (provedores, status, alertas)
│   ├── layout.py           # Shell sidebar + abas
│   └── tab_*.py            # Dashboard, blog, URLs, histórico, settings…
│
├── api/                    # REST FastAPI (/api/health, /api/v1/*)
├── services/               # Regras de negócio: IA, blog, fetch URLs, cache, CMS
├── core/                   # Motor GEO: esqueleto, índice IA, insights (sem HTTP/DB)
├── db/                     # SQLite: utilizadores, matérias, perfil
├── config/                 # ai_providers.yaml, paths, produção
├── skills/                 # Prompts editoriais (Markdown)
│
├── legacy/                 # Streamlit congelado (legacy/app.py)
├── modules/                # Compatibilidade legada — preferir core/ e services/
├── data/                   # BD + cache de URLs (gitignored)
├── output/                 # .md / .json exportados
├── docs/                   # Documentação
└── tests/                  # pytest
```

### Regra de dependências (código novo)

```
ui   →  services  →  core
api  →  services  →  db
```

- Importe de **`core/`** e **`services/`**; evite **`modules/`** (shims antigos).
- Regras para código novo: **[AGENTS.md](AGENTS.md)** (camadas e dependências).
- Roadmap e estado das fases: **[docs/ORGANIZACAO_E_PROXIMOS_PASSOS.md](docs/ORGANIZACAO_E_PROXIMOS_PASSOS.md)**.

## Testes

Na **raiz do projeto** (pasta onde está `main.py`):

```powershell
cd automa-o_blog
.\venv\Scripts\activate          # recomendado
pip install -r requirements.txt
pip install -r requirements-dev.txt
pytest tests/ -q
```

O `pyproject.toml` define `pythonpath = ["."]` para o pytest encontrar `core`, `services`, `api` e `db`.  
Se aparecer `ModuleNotFoundError: No module named 'core'`, confirme que está na raiz do repositório e não dentro de `tests/`.

## Documentação

| Documento | Para quem |
|-----------|-----------|
| **[AGENTS.md](AGENTS.md)** | Desenvolvedores — onde colocar código, o que não importar |
| **[Organização e próximos passos](docs/ORGANIZACAO_E_PROXIMOS_PASSOS.md)** | Roadmap, fases B–D, glossário |
| **[Manual do sistema](docs/MANUAL.md)** | Utilizadores — abas, Índice IA, fluxos de geração |
| [Resumo técnico](docs/RESUMO_TECNICO.md) | Arquitetura detalhada, limitações, decisões |
| [Executável Windows](docs/EXECUTABLE.md) | Build com `.\scripts\build_exe.ps1` |
| [Streamlit legado](legacy/README.md) | Apenas referência histórica |
