# GEO Extractor — Visão do sistema e plano de organização

**Atualizado:** 4 jun/2026  
**Público:** quem desenvolve ou mantém o projeto  
**Relacionados:** [AGENTS.md](../AGENTS.md) · [Manual de uso](MANUAL.md) · [Resumo técnico](RESUMO_TECNICO.md)

Este documento descreve **o que o software faz**, **como o código está organizado hoje**, **o que pode melhorar** e **os próximos passos** para deixar a base mais limpa e fácil de evoluir.

---

## 1. O que é o GEO Extractor?

É uma ferramenta que roda no seu computador (ou em um servidor seu) para **criar textos pensados para serem citados por IAs** — ChatGPT, Perplexity, resumos do Google com IA, etc.

Além do SEO tradicional (aparecer no Google), o foco é **GEO (Generative Engine Optimization)**: estruturar o conteúdo com títulos claros, blocos de confiança, evidências, comparativos e perguntas frequentes, no estilo que motores generativos costumam preferir ao citar uma fonte.

### O que o usuário faz na prática

1. Informa **tema**, **links de referência**, palavras-chave e preferências (tom, tamanho do texto).
2. O sistema **lê as páginas**, extrai ideias principais e monta um **esqueleto** do artigo.
3. Com IA (ou em modo rascunho, sem IA), **gera a matéria** em Markdown, com metadados para SEO.
4. Pode **salvar no histórico**, exportar arquivos e, em produção, chamar a **API** ou publicar em um CMS externo.

### Como abrir o programa

```powershell
python main.py
```

Abre o **Content Studio** no navegador (por exemplo `http://localhost:8080`).  
Há login local; as matérias ficam no banco SQLite em `data/`.

> A interface antiga em Streamlit está em [`legacy/app.py`](../legacy/app.py) (congelada). O desenvolvimento deve priorizar `main.py` (NiceGUI).

---

## 2. Partes principais do sistema

```
┌─────────────────────────────────────────────────────────────┐
│  Navegador — Content Studio (NiceGUI)                        │
│  Login · abas · formulários · histórico · configurações        │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│  API REST (/api/...) — mesmo processo que a interface        │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│  Pipelines — orquestram “gerar matéria” e “processar URLs”   │
└───────────────────────────┬─────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
   services/            core/              db/ + output/
   (IA, blog, fetch)    (regras GEO)       (SQLite, .md/.json)
```

| Pasta | Papel em linguagem simples |
|-------|----------------------------|
| `main.py` | Ponto de entrada: sobe a interface e registra a API |
| `ui/` | Telas: `pages/` (rotas), `tab_*.py` (conteúdo), `components/`, `design_tokens.css` — ver `ui/README.md` |
| `api/` | Endpoints para integrar com outros sistemas |
| `services/` | Regras de negócio: chamar IA, buscar URLs, gerar blog, estatísticas |
| `core/` | Motor GEO: esqueleto, índice IA, insights, nichos, FAQ JSON-LD |
| `db/` | Guardar usuários, perfil do blog e matérias no histórico |
| `config/` | Provedores de IA (`ai_providers.yaml`) e ajustes de produção |
| `skills/` | Textos de orientação para a IA (prompts em Markdown) |
| `data/` | Banco SQLite (não vai para o Git) |
| `output/` | Arquivos exportados após cada geração |
| `tests/` | Testes automatizados |

### Abas da interface

Rotas definidas em `ui/pages/routes.py`.

| Aba | Rota | Para que serve |
|-----|------|----------------|
| Dashboard | `/dashboard` | Uso de IA (tokens/custo), saúde da API, webhooks, CMS |
| Criar matéria | `/criar-materia` | Fluxo principal do blog (tema + referências + nicho GEO) |
| URLs | `/urls` | Artigo a partir de links |
| Texto manual | `/texto` | Artigo a partir de texto colado |
| JSON ChatGPT | `/json` | Analisar JSON da aba Network do ChatGPT |
| Lote CSV | `/lote` | Várias matérias a partir de planilha CSV |
| Histórico | `/historico` | Matérias já geradas; export FAQ JSON-LD; publicar CMS |
| Perfil | `/perfil` | Dados do autor/blog |
| Administração | `/admin` | Só utilizadores admin (gestão de contas) |
| Settings | `/configuracoes` | Chaves de API, provedores de IA, cache de URLs |

Na barra lateral (blog, URLs, texto): **extração avançada** (NLP), **gerar com IA**, **provedor** (OpenAI, Anthropic, Ollama, etc.) e **nicho GEO** (genérico, saúde, finanças, SaaS).

---

## 3. Como o código está hoje (e o que confunde)

### O que já funciona bem

- Geração de matérias longas (1.500 a 6.000 palavras), inclusive modo “artigo longo” em duas etapas com IA.
- Vários provedores de IA configuráveis; painel de tokens/custo no Dashboard.
- Histórico local por utilizador, API REST, Docker e webhooks para produção.
- Interface moderna com login, papéis (utilizador/admin) e fila em segundo plano para tarefas longas.
- Prompts versionados em `skills/`.
- Nichos GEO (`core/geo_niches.py`) nas abas blog, URLs, texto e lote.
- Fetch headless para páginas em JavaScript (`GEO_BROWSER_FETCH`, Playwright).
- Export de FAQ em JSON-LD (`core/faq_jsonld.py`, componente na UI).
- Validação anti-SSRF de URLs na API e nos pipelines (`services/url_security.py`).

### Pontos de atenção na organização

**1. Pastas que se sobrepõem**

Existem três “lugares” com lógica parecida:

- `services/` — **caminho preferido** para código novo (interface e API usam isto).
- `core/` — regras centrais de GEO e insights.
- `modules/` — mistura de **atalhos** (reexporta `core` e `services`) com **arquivos antigos** ainda duplicados.

Risco: corrigir um bug em `services/` e o Streamlit ou um teste ainda usar cópia em `modules/`.

**2. Duas interfaces**

- **NiceGUI** (`main.py`) — oficial.
- **Streamlit** (`legacy/app.py`) — legado; não recebe features novas.

**3. Pasta `pipelines/`**

Só redireciona para `services/`. Fluxos reais: `services/blog_pipeline.py`, `services/url_pipeline.py`, `services/batch_csv.py`. Ver `pipelines/README.md`.

**4. Autenticação em dois modos**

- Na interface: login com e-mail e senha (sessão no navegador).
- Na API: chave `GEO_API_KEY`.

Ainda não há vínculo claro “cada usuário da interface tem sua chave de API”.

**5. Matérias e usuários** — **resolvido (D3)**

Cada matéria tem `user_id`; histórico, dashboard e API filtram por conta. Ver `db/repository.py` e `ui/auth.py`.

---

## 4. Organização desejada (alvo)

Objetivo: **uma estrutura fácil de entender** e com dependências em uma só direção.

```
projeto/
├── main.py              ← única entrada da interface
├── api/                 ← API REST
├── ui/                  ← telas
├── core/                ← GEO puro (sem chamar rede nem banco)
├── services/            ← IA, blog, busca de URLs, CMS, métricas
├── db/                  ← modelos e acesso ao SQLite
├── config/
├── skills/
├── data/
├── output/
├── tests/
├── docs/
└── legacy/              ← opcional: app.py Streamlit, congelado
```

**Regra de dependência**

```
ui  →  services  →  core
api →  services  →  db
```

A interface e a API **não** devem importar código legado de `modules/` diretamente.

---

## 5. Próximos passos — plano por fases

### Fase A — Organização do código — **concluída (base estável)**

| # | Tarefa | Estado |
|---|--------|--------|
| A1 | Mapear imports `modules.*` | Feito — só `legacy/` (congelado); `ui/`, `api/`, `services/` limpos |
| A2 | Testes e entrada em `services` / `core` | Feito — `pytest`; `main.py` sem `modules` |
| A3 | `modules/` só reexportações | Feito — ver `modules/README.md` |
| A4 | `app.py` descontinuado | Feito — aviso + `legacy/app.py` |
| A5 | Rótulos UI centralizados | Feito — `ui/constants.py` |
| A6 | README + guia de estrutura | Feito — README, este doc, **`AGENTS.md`** na raiz |

**Critério de “feito”:** `pytest tests/ -q` verde; teste `tests/test_project_structure.py` impede `modules` em código ativo.

**Antes de features novas:** ler [AGENTS.md](../AGENTS.md) (camadas e dependências).

---

### Fase B — Qualidade do conteúdo gerado

| # | Tarefa | Estado |
|---|--------|--------|
| B1 | Aviso se o texto ficou com menos de 85% das palavras pedidas | Feito — banner + toast + `services/word_count.py` |
| B2 | Checklist na aba “Criar matéria” (H1, FAQ, tamanho) | Feito — `geo_checklist` + revisão humana; pré-voo em `brief_preflight` |
| B2b | Checklist em URLs / Texto manual | Feito — `article_review_panel` |
| B3 | Cache de URLs já buscadas | Feito — `services/url_cache.py`, pré-voo, abas URLs/blog, Definições |
| B4 | Alerta de texto muito parecido com a fonte | Feito — `similarity_check`, banners em blog/URLs/texto, checklist |
| B5 | Busca com navegador headless (sites em JavaScript) | Feito — `services/browser_fetcher.py`, `GEO_BROWSER_FETCH` (`auto` / `always` / `never`); ver README e `.env.example` |

---

### Fase C — Produto e uso diário

| # | Tarefa | Estado |
|---|--------|--------|
| C1 | Modelos por área (saúde, finanças, SaaS) | Feito (base) — `core/geo_niches.py`, `ui/components/geo_niche_panel.py`; **pendente:** mais verticais e ajuste fino de blocos/prompts por nicho |
| C2 | Exportar FAQ em JSON-LD | Feito — `core/faq_jsonld.py`, `ui/components/faq_jsonld_export.py` (histórico, URLs, texto) |
| C3 | Lote: planilha CSV → vários `.md` em `output/` | Feito — aba Lote (`/lote`), fila, histórico opcional, webhook `batch.completed`, coluna `nicho` no CSV |
| C4 | Log de tokens/custo no Dashboard | Feito — `services/ai_usage.py`, painel no Dashboard |

---

### Fase D — Plataforma e segurança

| # | Tarefa | Estado |
|---|--------|--------|
| D1 | Validar URLs na API (anti-SSRF) | Feito — `api/url_validation.py`, `services/url_security.py`, testes em `tests/test_api_url_validation.py` |
| D2 | Fila em segundo plano para textos muito longos | Feito — blog, texto, URLs, lote (`GEO_QUEUE_*`, `services/background_jobs.py`) |
| D3 | `user_id` em cada matéria do histórico | Feito — ver `docs/CONTAS_E_HISTORICO.md` |
| D4 | Documentar `GEO_STORAGE_SECRET` para produção | Feito — ver `docs/PRODUCAO_SESSOES.md` |
| D5 | Chave de API por utilizador (multi-tenant) | Pendente — hoje `GEO_API_KEY` é global; login da UI é por conta |

---

## 6. Ordem sugerida de trabalho

1. **Fase A** — concluída; manter `pytest tests/ -q` e `test_project_structure.py` verdes em cada alteração.
2. **Fases B, C, D (núcleo)** — concluídas na base atual (checklist, cache, similaridade, lote, nichos, JSON-LD, headless, validação de URLs, fila, `user_id`, sessão em produção).
3. **Próximo foco sugerido:**
   - **C1 (expandir):** novos nichos GEO e prompts/blocos específicos por vertical.
   - **D5:** API com chave por utilizador ou escopo por `user_id` na geração via REST.
   - **Integrações:** polish de CMS/webhook (Dashboard, histórico, `POST /api/v1/articles/publish`).
   - **Docs:** alinhar [RESUMO_TECNICO.md](RESUMO_TECNICO.md) com este plano (vários itens lá ainda constam como futuros).
4. Código novo sempre em `services/` + `ui/` / `api/`; não reabrir lógica em `modules/`.

---

## 7. Glossário rápido

| Termo | Significado |
|-------|-------------|
| **GEO** | Otimização para ser citado por IAs generativas, não só ranquear no Google. |
| **Esqueleto GEO** | Estrutura de títulos e blocos (confiança, ciência, comparativo) antes da redação final. |
| **Índice IA** | Representação de como o tema poderia ser “indexado” por uma IA; é inferido localmente, não é dado real do ChatGPT. |
| **Pipeline** | Sequência automática: buscar fontes → extrair ideias → montar esqueleto → gerar texto → salvar. |
| **Provedor** | Serviço de IA (OpenAI, Anthropic, Ollama, etc.). |
| **Modo local** | Gera rascunho sem chamar IA (texto genérico; serve para testes ou offline). |
| **Nicho GEO** | Modelo de esqueleto/blocos por área (ex.: saúde, finanças, SaaS); id em `core/geo_niches.py`. |
| **JSON-LD FAQ** | Script `FAQPage` para colar no HTML a partir do bloco de perguntas do artigo. |

---

## 8. Documentos do projeto

| Documento | Conteúdo |
|-----------|----------|
| [AGENTS.md](../AGENTS.md) | Regras de camadas para devs e agentes (ler primeiro) |
| [MANUAL.md](MANUAL.md) | Como usar cada aba e fluxo |
| [PRODUCAO_SESSOES.md](PRODUCAO_SESSOES.md) | `GEO_STORAGE_SECRET` em produção |
| [CONTAS_E_HISTORICO.md](CONTAS_E_HISTORICO.md) | Várias contas na mesma máquina |
| [RESUMO_TECNICO.md](RESUMO_TECNICO.md) | Detalhes técnicos (revisar alinhamento com este plano) |
| [EXECUTABLE.md](EXECUTABLE.md) | Gerar executável Windows |
| [services/README.md](../services/README.md) | Pipelines e módulos de negócio |
| [core/README.md](../core/README.md) | Motor GEO sem efeitos externos |
| [modules/README.md](../modules/README.md) · [pipelines/README.md](../pipelines/README.md) | Pastas legadas — só reexportações |
| **Este arquivo** | Visão geral, organização e estado das fases |

---

*Documento vivo: atualizar quando mudar o estado de uma fase (tabela na secção 5) ou abas/rotas da UI.*
