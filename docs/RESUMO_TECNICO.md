# GEO Extractor — Resumo Técnico e Plano de Evolução

**Versão:** 0.2 (MVP+ blog longo)  
**Data:** maio/2026  
**Stack:** Python 3.11+, Streamlit, Requests, BeautifulSoup, spaCy/KeyBERT (opcional), OpenAI/Anthropic/OpenRouter/Ollama  
**Metodologia:** [SEO Genome — DNA do ChatGPT](https://seogenome.com/br/o-dna-do-chatgpt-como-mapear-o-pensamento-da-ia-para-dominar-o-seo-em-2026/)  
**Referência GEO:** [ultimate-seo-geo](https://github.com/mykpono/ultimate-seo-geo)  
**Skills editoriais (adaptadas localmente):** `skills/seo_geo.md`, `skills/seo_audit.md`, `skills/blog_post.md`

---

## 1. Problema e objetivo

Organizações precisam de conteúdo **citável por motores generativos** (ChatGPT, Perplexity, Google AI Overviews), não apenas ranqueável no Google clássico. A metodologia **GEO (Generative Engine Optimization)** estrutura páginas com H1 editoriais, blocos de confiança, evidência e comparativos — alinhados ao padrão observado na engenharia reversa do JSON da aba Network do ChatGPT.

**Objetivo do GEO Extractor:** ferramenta web local que:

1. Ingere **URLs**, **texto manual** ou **JSON do ChatGPT**.
2. Extrai **insights semânticos** (NLP avançado com fallback heurístico).
3. Gera **índice estruturado** inspirado no formato de indexação da API do ChatGPT.
4. Produz **artigos GEO** ou **matérias longas para blog** a partir de **tema + links de referência**.

---

## 2. Escopo atual

| Faz | Não faz (ainda) |
|-----|------------------|
| Fetch HTTP + extração de texto | Crawl de site inteiro (Screaming Frog) |
| NLP: KeyBERT, spaCy NER, sumy, embeddings (lazy) | RAG com base vetorial persistente |
| Índice IA simulado (`search_model_queries` / `search_result_groups`) | Réplica byte-a-byte do protocolo OpenAI |
| Esqueleto H1/H2/H3 (regras SEO Genome) | Publicação automática em CMS |
| **Blog:** tema + URLs → matéria 1.500–6.000 palavras | Fact-checking / plágio automático |
| Artigo longo: esqueleto expandido + 2 passagens LLM (≥2.600 palavras) | Garantia de contagem exata sem revisão |
| Multi-provider (`ai_providers.yaml`) | Auth multi-utilizador |
| Export `.json` + `.md` em `output/` | CI/CD e testes E2E de UI |

---

## 3. Arquitetura

```
geo-extractor/
├── legacy/app.py                   # Streamlit legado (4 abas)
├── config/ai_providers.yaml
├── skills/                         # Prompts SEO-GEO, audit, blog
├── modules/
│   ├── article_fetcher.py
│   ├── advanced_extractor.py
│   ├── insight_extractor.py
│   ├── ai_manager.py
│   ├── ai_index_builder.py
│   ├── geo_engine.py
│   ├── article_writer.py
│   ├── blog_brief.py
│   ├── blog_length.py              # extensão, tokens, esqueleto longo
│   ├── blog_generator.py           # pipeline blog
│   └── json_parser.py
├── tests/
│   ├── test_geo_engine.py
│   └── test_blog_generator.py
└── output/
```

### Fluxo — URLs / texto (legado)

```
URLs → fetch_many → extract_insights → merge_insights
     → build_ai_index + generate_geo_skeleton + generate_full_article
```

### Fluxo — Criar matéria para blog (principal)

```
BlogBrief (tema, keywords, URLs, extensão, tom, FAQ…)
  → collect_reference_insights (fetch + NLP)
  → generate_geo_skeleton + expand_skeleton_for_long (se ≥2600 palavras)
  → generate_blog_post
       ├─ IA + longo: 2 passagens LLM (chunked)
       ├─ IA + padrão: 1 passagem (max_tokens dinâmico)
       └─ local: write_article_local / _write_blog_local_long
  → BlogPostPackage (markdown, meta SEO, word_count_actual)
```

---

## 4. Regras GEO (núcleo)

| Regra | Implementação |
|-------|----------------|
| H1 editorial, sem selos/siglas | `geo_engine.build_h1()` |
| Bloco segurança → selos em H3 | `GeoBlock` nível 3 |
| Bloco ciência → evidências, limitações | Instruções ao redator |
| Bloco comparativo → critérios objetivos | `criterios_comparacao` |
| Answer-first, blocos 134–167 palavras | `skills/seo_geo.md` + prompts |
| FAQ para citabilidade | `blog_generator`, 5–8 perguntas |

**Índice IA:** representação estrutural dos sinais inferidos — não é payload real do ChatGPT.

---

## 5. Modos de extensão do blog

| Faixa (palavras) | Comportamento |
|------------------|---------------|
| 1.500–2.500 | Esqueleto GEO padrão + 5–7 H2; 1 chamada LLM |
| **≥2.600** | `expand_skeleton_for_long`: +H2 editoriais (contexto, prática, erros, casos) |
| **≥2.600 + IA** | `long_chunked`: 2 passagens (~metade cada) + META na 2ª |
| Local (sem IA) | `_write_blog_local_long`: parágrafos extra por H2 (rascunho) |

`max_tokens` ≈ `word_count × 2.4–2.8` (teto 16.000).

---

## 6. Dependências e execução

```txt
streamlit, requests, beautifulsoup4, python-dotenv, pyyaml
openai, anthropic
sentence-transformers, keybert, sumy, spacy, numpy
```

```powershell
cd geo-extractor
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
python -m spacy download pt_core_news_lg   # opcional
python -m streamlit run legacy/app.py
```

`.env`: `OPENAI_API_KEY`, `OPENROUTER_API_KEY`, etc., conforme `config/ai_providers.yaml`.

---

## 7. Limitações conhecidas

1. **Fetch frágil:** paywall, SPA, anti-bot.
2. **Contagem de palavras:** LLM pode ficar abaixo da meta; UI mostra `actual/target` para revisão.
3. **Modo local:** texto genérico de preenchimento — não substitui redação humana.
4. **2 passagens:** possível leve descontinuidade entre metades; revisar junção.
5. **SSRF:** URLs não validadas se app exposta à rede.
6. **Custo/tempo:** 4.000–6.000 palavras = 2× chamadas com alto `max_tokens`.

---

## 8. Perguntas para opinião técnica

1. **Chunked vs. agente:** manter 2 passagens fixas ou orquestrar N secções com estado (LangGraph / deepagents)?
2. **Validação GEO:** checker automático (contagem, H1 sem sigla, FAQ presente, answer-first)?
3. **Índice IA:** artefacto para humanos ou só interno ao pipeline?
4. **CMS:** priorizar export WordPress/MDX ou API REST?
5. **Compliance:** política de atribuição e similaridade vs. fontes?
6. **Stack UI:** Streamlit suficiente ou FastAPI + frontend?

---

## 9. Roadmap (planejamento)

### Fase atual — P0.5 ✅ (em curso)

- [x] Aba **Criar matéria para blog** (tema + referências)
- [x] Skills locais SEO-GEO / audit / blog
- [x] Extensão 1.500–6.000 palavras; modo longo chunked
- [x] Métrica palavras geradas vs. meta na UI
- [ ] Revisão humana documentada no fluxo (checklist na UI)

### P1 — Qualidade e robustez (próximo sprint)

| Item | Descrição | Esforço |
|------|-----------|---------|
| Validação pós-geração | Alertar se `actual < 0.85 × target`; sugerir "expandir secção X" | M |
| Playwright fetch | Páginas JS | G |
| Cache de URLs | Evitar re-fetch | P |
| Similaridade vs. fonte | `difflib` / embeddings — alerta de proximidade | M |
| Testes integração | URL mock → blog ≥ N palavras (com LLM mock) | M |

### P2 — Produção editorial

| Item | Descrição |
|------|-----------|
| Templates por vertical | Saúde, fintech, B2B SaaS (selos e blocos pré-definidos) |
| JSON-LD FAQPage | Export automático do bloco FAQ |
| Batch | CSV de temas + URLs → vários `.md` em `output/` |
| Histórico | SQLite de briefs e versões |

### P3 — Plataforma

| Item | Descrição |
|------|-----------|
| API REST | `POST /blog/generate` com `BlogBrief` JSON |
| Webhook CMS | WordPress, Ghost, Webflow |
| Fila assíncrona | Redis + worker para artigos 6k+ |
| Observabilidade | Log de tokens/custo por provedor |

### P4 — Pesquisa GEO

| Item | Descrição |
|------|-----------|
| A/B de estruturas | Medir citações em Perplexity (manual) |
| Sincronizar skills | `npx skills add` opc-skills / marketingskills no Cursor |
| Calibrar prompts | Com base em estudos Princeton (+40% citações com fontes) |

---

## 10. Decisões de desenho (registro)

| Decisão | Motivo |
|---------|--------|
| Skills em `skills/*.md` | Reprodutibilidade sem depender de `npx` em runtime |
| Threshold 2.600 palavras | Equilíbrio custo LLM vs. necessidade de profundidade |
| Chunked em 2 partes | Contornar limite de saída; mais simples que N agentes |
| GEO skeleton como base | Alinha blog ao DNA ChatGPT, não só SEO clássico |
| IA ligada por defeito na sidebar | Matérias completas exigem LLM |

---

## 11. Conclusão

O **GEO Extractor** evoluiu de protótipo de reescrita para um **estúdio de conteúdo GEO**: pesquisa referências, aplica regras citáveis e gera **matérias longas para blog** com metadados SEO. O modo **≥2.600 palavras** usa esqueleto expandido e geração em duas passagens; a revisão humana e validação automática de extensão/GEO são os próximos passos críticos antes de uso em produção editorial.

---

*Documento vivo — atualizar a cada release. Próxima revisão sugerida após P1 (validação + fetch robusto).*
