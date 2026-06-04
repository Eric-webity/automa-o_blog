# GEO Extractor — Manual do Sistema

**Versão:** 0.3  
**Interface:** NiceGUI (`python main.py`)  
**Objetivo:** Criar conteúdo otimizado para **GEO** (Generative Engine Optimization) — matérias citáveis por ChatGPT, Perplexity, Google AI Overviews e similares.

---

## 1. O que é o GEO Extractor?

Ferramenta local que:

1. **Ingere** URLs, texto colado ou JSON do Network do ChatGPT.
2. **Extrai insights** (keywords, entidades, frases-chave, sinais de confiança).
3. **Gera o Índice IA** — mapa estruturado de como uma IA indexaria o tema.
4. **Monta o esqueleto GEO** — H1/H2/H3 alinhados à metodologia SEO Genome.
5. **Redige o artigo** com IA (OpenAI, LM Studio, Ollama…) ou modo local (rascunho).

---

## 2. Instalação rápida

```powershell
cd geo-extractor
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python main.py
```

Abra a URL exibida no terminal (ex.: `http://localhost:8080`).

**Produção (servidor exposto):** defina `GEO_ENV=production` e um `GEO_STORAGE_SECRET` forte (≥32 caracteres). Sem isto, cookies de login podem ser forjados. Guia completo: [PRODUCAO_SESSOES.md](PRODUCAO_SESSOES.md).

**NLP avançado (opcional):** `python -m spacy download pt_core_news_sm`

---

## 3. Interface — visão geral

```
┌─────────────────────────────────────────────────────────┐
│  GEO Extractor · Content Studio                         │
├──────────────┬──────────────────────────────────────────┤
│  Sidebar     │  Área principal (aba selecionada)         │
│              │                                          │
│  · Criar     │  Formulário + resultados (tabs)          │
│    matéria   │                                          │
│  · URLs      │                                          │
│  · Texto     │  Configuração global:                    │
│  · JSON      │  □ Extração avançada                     │
│  · Config IA │  □ Gerar artigo com IA                     │
│              │  Provedor: auto / openai / lmstudio…     │
└──────────────┴──────────────────────────────────────────┘
```

### Sidebar — configuração global

| Opção | Função |
|-------|--------|
| **Extração avançada** | Usa spaCy + KeyBERT (mais lento, mais rico). |
| **Gerar artigo com IA** | Liga/desliga LLM. Desligado = rascunho local. |
| **Provedor de IA** | `auto` tenta na ordem do YAML; ou escolha um específico. |

---

## 4. Abas e fluxos de trabalho

### 4.1 Criar matéria para blog *(fluxo principal)*

**Quando usar:** artigo longo para publicar no seu blog, com tema + links de referência.

**Passos:**

1. Preencha **tema**, **keywords**, **ângulo**, **público**, **tom** e **extensão** (1.500–6.000 palavras).
2. Cole **URLs de referência** (uma por linha).
3. Marque **Gerar artigo com IA** e configure o provedor (aba Configuração IA).
4. Clique **Gerar matéria para blog**.

**Resultado — abas:**

| Aba | Conteúdo |
|-----|----------|
| **Artigo** | Markdown pronto para revisão/publicação |
| **Índice IA** | JSON com sinais GEO (aplicado na redação com IA) |
| **SEO** | meta title, description, slug, FAQ |
| **Esqueleto GEO** | Estrutura H1/H2/H3 usada na geração |

**Ficheiros em `output/`:**

- `blog_{slug}_{timestamp}.md` — artigo
- `blog_{slug}_{timestamp}_meta.json` — metadados SEO
- `blog_{slug}_{timestamp}_indice.json` — índice IA

**Extensão ≥ 2.600 palavras:** esqueleto expandido + geração em 2 passagens LLM.

---

### 4.2 URLs

**Quando usar:** reescrever/estruturar matérias já publicadas na web.

**Passos:**

1. Cole URLs (uma por linha).
2. **Processar URLs**.

**Resultado — abas:** Insights · **Índice IA** · Esqueleto · Artigo

**Ficheiros:** `output/indice_{timestamp}.json` e `output/artigo_{timestamp}.md`

---

### 4.3 Texto manual

Igual ao fluxo URLs, mas cola o texto directamente (sem fetch).

---

### 4.4 JSON ChatGPT

**Quando usar:** validar um JSON capturado da aba Network do ChatGPT.

Extrai queries, domínios e URLs — útil para entender o que o ChatGPT “pesquisou” numa conversa.

---

### 4.5 Configuração IA

Configure chaves API, LM Studio, Ollama, teste e compare configuração vs servidor.

| Provedor | URL típica | Notas |
|----------|------------|-------|
| **OpenAI** | API cloud | Chave `OPENAI_API_KEY` no `.env` |
| **LM Studio** | `http://IP:1234/v1` | Servidor local; modelo = ID carregado |
| **Ollama** | `http://IP:11434` | Porta **11434** (não confundir com LM Studio) |
| **OpenRouter / Anthropic** | Cloud | Chaves respectivas no `.env` |

**Botões:** Testar (usa valores do formulário) · Comparar (diagnóstico) · Salvar e aplicar

---

## 5. Índice IA — o que é e como aplicar

### 5.1 O que contém

O Índice IA simula a estrutura observada no JSON da aba Network do ChatGPT:

```json
{
  "search_model_queries": [ { "q": "melhor CRM para PMEs", "type": "search_model_query" } ],
  "search_result_groups": [ { "domain": "...", "entries": [ { "url", "title", "snippet" } ] } ],
  "semantic_insights": {
    "keywords": ["..."],
    "entities": ["..."],
    "trust_signals": ["..."],
    "comparison_axes": ["..."]
  },
  "metadata": {
    "citations": [ { "url", "title", "domain" } ],
    "content_references": [ { "matched_text", "source_url" } ]
  }
}
```

### 5.2 Como é aplicado *(automático)*

O sistema **já aplica** o índice quando gera com IA:

```
Insights das fontes
       ↓
build_ai_index()  →  JSON (Índice IA)
       ↓
format_ai_index_for_prompt()  →  instruções ao redator
       ↓
Prompt LLM = Esqueleto GEO + Fontes + Índice IA
       ↓
Artigo final (consultas respondidas, keywords distribuídas, fontes citadas)
```

**Com IA activa**, o redator recebe instruções para:

- Responder às **consultas simuladas** no 1.º parágrafo de cada secção
- Distribuir **keywords** e **eixos de comparação** pelos H2
- Incluir **sinais de confiança** no bloco de segurança/garantias
- Listar todas as **citações** em «Fontes consultadas»

**Modo local (sem IA):** o índice é gerado e guardado, mas o rascunho não o interpreta — use IA para aplicar de facto.

### 5.3 Aplicação manual (fora da ferramenta)

Se quiser usar o JSON noutro sítio (Cursor, ChatGPT, CMS):

1. Abra `output/*_indice.json`
2. Use `search_model_queries` como títulos ou FAQ
3. Use `semantic_insights.keywords` em meta tags e subtítulos
4. Use `metadata.citations` como bibliografia obrigatória
5. Cole o JSON na aba **JSON ChatGPT** para validar estrutura

### 5.4 Esqueleto GEO + Índice — relação

| Artefacto | Papel |
|-----------|-------|
| **Esqueleto GEO** | *Como* estruturar (H1 editorial, blocos segurança/ciência/comparativo) |
| **Índice IA** | *O quê* enfatizar (queries, entidades, citações, eixos) |
| **Skills** (`skills/*.md`) | *Regras* de redação (answer-first, FAQ, citabilidade) |

Os três combinam-se no prompt da IA.

---

## 6. Esqueleto GEO (regras)

Gerado automaticamente a partir do tema e insights:

| Bloco H2 | Conteúdo esperado |
|----------|-------------------|
| Segurança e garantias | Selos, normas, certificações (H3 por selo) |
| Ciência / evidências | Dados, métricas, limitações |
| Melhores práticas | Resultados esperados, prazos |
| Comparativo | Alternativas, prós/contras, critérios |

**H1:** editorial, sem siglas técnicas no título.

---

## 7. Ficheiros de saída

| Ficheiro | Origem |
|----------|--------|
| `artigo_*.md` | URLs / Texto manual |
| `indice_*.json` | URLs / Texto manual |
| `blog_*_*.md` | Criar matéria |
| `blog_*_*_meta.json` | Metadados SEO do blog |
| `blog_*_*_indice.json` | Índice IA do blog |

Pasta: `output/` (não versionada no Git).

---

## 8. Configuração avançada

### `config/ai_providers.yaml`

Lista provedores, modelos por tarefa (`rewrite`, `blog_long`) e URLs locais.

### `.env`

```
OPENAI_API_KEY=sk-...
LMSTUDIO_API_KEY=lm-studio
```

### Skills editoriais

Edite `skills/seo_geo.md`, `seo_audit.md`, `blog_post.md` para ajustar tom e regras — são injectadas nos prompts de blog.

---

## 9. Resolução de problemas

| Sintoma | Causa provável | Solução |
|---------|----------------|---------|
| Banner laranja «IA indisponível» | Chave ausente ou LM Studio offline | Configuração IA → Testar → Salvar |
| Artigo repetitivo | Modo local activo | Activar IA + provedor válido |
| «Nenhum provedor respondeu» | Provedor desmarcado ou URL errada | Marcar LM Studio, URL com `/v1`, Salvar |
| Ollama falha na porta 1234 | Porta do LM Studio | Ollama usa **11434** |
| Palavras abaixo da meta | Limite do modelo local | Modelo maior ou OpenAI cloud |
| URL não processada | Paywall / anti-bot | Colar texto na aba Texto manual |

---

## 10. Fluxo recomendado (produção editorial)

```
1. Configurar IA (LM Studio ou OpenAI)
2. Recolher 3–5 URLs de referência fiáveis
3. Criar matéria para blog (tema + URLs + 2500–4000 palavras)
4. Rever aba Índice IA — queries e citações fazem sentido?
5. Rever aba Artigo — fact-check, tom, extensão
6. Copiar meta SEO da aba SEO
7. Publicar no CMS + secção Fontes consultadas intacta
```

---

## 11. Documentação complementar

- [RESUMO_TECNICO.md](RESUMO_TECNICO.md) — arquitectura, roadmap, limitações
- [README.md](../README.md) — instalação e estrutura do projecto

---

*Manual actualizado com aplicação automática do Índice IA nos prompts de geração (v0.3).*
