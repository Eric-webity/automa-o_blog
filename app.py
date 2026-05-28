"""
GEO Extractor — Streamlit app (legado).

Preferir: python main.py  (NiceGUI)
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from modules import (
    AIManager,
    BlogBrief,
    GeoInputs,
    build_ai_index,
    extract_geo_signals,
    extract_insights,
    extract_insights_from_text,
    fetch_many,
    generate_blog_post,
    generate_full_article,
    generate_geo_skeleton,
    merge_insights,
)
from modules.blog_brief import parse_keywords

load_dotenv()

ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

st.set_page_config(page_title="GEO Extractor", layout="wide", page_icon="🧠")

st.markdown(
    """
    <style>
    .geo-badge { background:#ecfdf5;color:#047857;padding:0.2rem 0.6rem;
                border-radius:4px;font-size:0.85rem; }
    </style>
    """,
    unsafe_allow_html=True,
)
st.title("🧠 GEO Extractor")
st.markdown('<span class="geo-badge">NLP · Multi-IA · GEO</span>', unsafe_allow_html=True)

# --- Sidebar ---
st.sidebar.header("Configuração")
use_advanced = st.sidebar.checkbox("Extração avançada (spaCy / KeyBERT)", value=True)
use_llm = st.sidebar.checkbox("Gerar artigo com IA", value=True)

try:
    ai_mgr = AIManager()
    enabled = ai_mgr.list_enabled_providers()
except Exception:
    ai_mgr = None
    enabled = []

provider_choice = st.sidebar.selectbox(
    "Provedor de IA",
    ["auto"] + enabled if enabled else ["auto"],
    disabled=not use_llm,
)
provider = None if provider_choice == "auto" else provider_choice

if use_llm and not enabled:
    st.sidebar.warning("Nenhum provider habilitado em config/ai_providers.yaml")

tab_blog, tab_urls, tab_text, tab_json = st.tabs(
    ["✍️ Criar matéria para blog", "🔗 URLs", "📝 Texto manual", "📋 JSON ChatGPT"]
)


def _run_pipeline(insights_list: list, merged: dict) -> None:
    geo = GeoInputs(
        tema_central=merged.get("tema_central", ""),
        entidade_intencao=merged.get("entidade_intencao", ""),
        selos_certificacoes=merged.get("selos_certificacoes", ""),
        criterios_comparacao=merged.get("criterios_comparacao", ""),
    )
    ai_index = build_ai_index(insights_list, geo.tema_central)
    skeleton = generate_geo_skeleton(geo)
    article = generate_full_article(
        insights_list,
        geo,
        use_llm=use_llm,
        provider=provider,
        manager=ai_mgr,
    )

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    index_path = OUTPUT_DIR / f"indice_{ts}.json"
    article_path = OUTPUT_DIR / f"artigo_{ts}.md"
    index_path.write_text(json.dumps(ai_index, indent=2, ensure_ascii=False), encoding="utf-8")
    article_path.write_text(article.markdown, encoding="utf-8")

    st.session_state["results"] = {
        "merged": merged,
        "insights": insights_list,
        "ai_index": ai_index,
        "skeleton": skeleton,
        "article": article,
        "index_path": str(index_path),
        "article_path": str(article_path),
    }


with tab_blog:
    st.subheader("Matéria original para blog")
    st.caption(
        "Informe o tema e links de referência. A ferramenta pesquisa as fontes, "
        "aplica SEO + GEO (skills seo-geo, seo-audit, blog-post) e gera a matéria completa."
    )
    col_a, col_b = st.columns(2)
    with col_a:
        blog_topic = st.text_input("Tema / assunto principal", placeholder="Ex: melhor CRM para PMEs")
        blog_keywords = st.text_input(
            "Palavras-chave (vírgula)",
            placeholder="crm pequenas empresas, software vendas",
        )
        blog_angle = st.selectbox(
            "Ângulo editorial",
            ["guia completo", "comparativo", "como fazer", "lista", "análise de mercado", "outro"],
        )
        blog_angle_custom = ""
        if blog_angle == "outro":
            blog_angle_custom = st.text_input("Descreva o ângulo")
    with col_b:
        blog_audience = st.text_input("Público-alvo", value="Leitores interessados no tema")
        blog_tone = st.selectbox("Tom", ["informativo", "conversacional", "técnico", "jornalístico"])
        blog_words = st.select_slider(
            "Extensão (palavras)",
            options=[1500, 2000, 2500, 3000, 4000, 5000, 6000],
            value=2500,
        )
        if blog_words >= 2600:
            st.caption("Modo artigo longo: mais secções H2 e geração em 2 passagens (com IA).")
        blog_brand = st.text_input("Marca / site (opcional)", placeholder="Nome do blog")
        blog_cta = st.text_input("CTA (opcional)", placeholder="Ex: Agende uma demonstração")

    blog_refs = st.text_area(
        "Links de referência (um por linha — artigos, estudos, concorrentes)",
        height=100,
        placeholder="https://...\nhttps://...",
    )
    blog_faq = st.checkbox("Incluir secção FAQ (recomendado para GEO)", value=True)

    if st.button("Gerar matéria para blog", type="primary", key="btn_blog"):
        if not blog_topic.strip():
            st.warning("Informe o tema principal.")
        else:
            refs = [u.strip() for u in blog_refs.splitlines() if u.strip()]
            angle = blog_angle_custom if blog_angle == "outro" else blog_angle
            brief = BlogBrief(
                topic=blog_topic.strip(),
                reference_urls=refs,
                target_keywords=parse_keywords(blog_keywords),
                audience=blog_audience.strip() or "Leitores interessados no tema",
                tone=blog_tone,
                word_count=blog_words,
                brand_name=blog_brand.strip(),
                cta=blog_cta.strip(),
                include_faq=blog_faq,
                angle=angle,
            )
            with st.spinner("A pesquisar referências e redigir matéria..."):
                try:
                    package = generate_blog_post(
                        brief,
                        use_advanced=use_advanced,
                        use_llm=use_llm,
                        provider=provider,
                        manager=ai_mgr,
                    )
                except Exception as exc:
                    st.error(f"Erro ao gerar: {exc}")
                    package = None

            if package:
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                slug = package.slug or "artigo"
                md_path = OUTPUT_DIR / f"blog_{slug}_{ts}.md"
                meta_path = OUTPUT_DIR / f"blog_{slug}_{ts}_meta.json"
                meta_payload = {
                    "meta_title": package.meta_title,
                    "meta_description": package.meta_description,
                    "slug": package.slug,
                    "keywords": package.keywords_used,
                    "faq": package.faq_items,
                }
                md_path.write_text(package.markdown, encoding="utf-8")
                meta_path.write_text(
                    json.dumps(meta_payload, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
                st.session_state["blog_results"] = {
                    "package": package,
                    "md_path": str(md_path),
                    "meta_path": str(meta_path),
                    "meta_payload": meta_payload,
                }
                st.success(
                    f"Matéria gerada ({'IA: ' + package.provider_used if package.used_llm else 'modo local'})."
                )

blog_results = st.session_state.get("blog_results")
if blog_results:
    pkg = blog_results["package"]
    meta = blog_results["meta_payload"]
    st.divider()
    st.subheader("Matéria para blog")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Modo", pkg.generation_mode or ("IA" if pkg.used_llm else "local"))
    c2.metric("Palavras", pkg.word_count_actual or "—")
    c3.metric("Meta", pkg.word_count_target or "—")
    c4.metric("Referências", len(pkg.insights))
    if pkg.word_count_target and pkg.word_count_actual:
        pct = int(100 * pkg.word_count_actual / pkg.word_count_target)
        st.caption(f"Extensão: {pct}% da meta ({pkg.word_count_actual}/{pkg.word_count_target} palavras).")

    b1, b2, b3 = st.tabs(["Artigo", "SEO", "Esqueleto GEO"])
    with b1:
        st.markdown(pkg.markdown)
        st.caption(f"Salvo: {blog_results.get('md_path', '')}")
        st.download_button(
            "Download Markdown",
            data=pkg.markdown,
            file_name=f"{pkg.slug}.md",
            mime="text/markdown",
            key="dl_blog_md",
        )
    with b2:
        st.text_input("Meta title", value=meta.get("meta_title", ""), disabled=True)
        st.text_area("Meta description", value=meta.get("meta_description", ""), height=80, disabled=True)
        st.text_input("Slug sugerido", value=meta.get("slug", ""), disabled=True)
        st.write("Keywords:", ", ".join(meta.get("keywords", [])))
        if meta.get("faq"):
            st.json(meta["faq"])
        st.download_button(
            "Download metadados JSON",
            data=json.dumps(meta, indent=2, ensure_ascii=False),
            file_name=f"{pkg.slug}_meta.json",
            mime="application/json",
            key="dl_blog_meta",
        )
    with b3:
        st.markdown(pkg.skeleton.markdown)

with tab_urls:
    urls_text = st.text_area("URLs (uma por linha)", height=120)
    if st.button("Processar URLs", type="primary", key="btn_urls"):
        urls = [u.strip() for u in urls_text.splitlines() if u.strip()]
        if not urls:
            st.warning("Informe pelo menos uma URL.")
        else:
            with st.spinner("A buscar matérias..."):
                fetched = fetch_many(urls)
                for art in fetched:
                    if art.error:
                        st.warning(f"{art.url}: {art.error}")
                insights_list = [
                    extract_insights(a, use_advanced=use_advanced) for a in fetched
                ]
                insights_list = [i for i in insights_list if i]
            if not insights_list:
                st.error("Nenhuma matéria processada.")
            else:
                merged = merge_insights(insights_list)
                with st.spinner("A gerar índice e artigo..."):
                    _run_pipeline(insights_list, merged)
                st.success(f"{len(insights_list)} matéria(s) processada(s).")

with tab_text:
    title = st.text_input("Título", value="Matéria manual")
    body = st.text_area("Cole o texto da matéria", height=200)
    if st.button("Processar texto", type="primary", key="btn_text"):
        if not body.strip():
            st.warning("Cole o texto.")
        else:
            ins = extract_insights_from_text(body, title=title, use_advanced=use_advanced)
            if not ins:
                st.error("Não foi possível extrair insights.")
            else:
                merged = merge_insights([ins])
                _run_pipeline([ins], merged)
                st.success("Texto processado.")

with tab_json:
    raw = st.text_area("JSON do Network (ChatGPT)", height=140)
    if st.button("Validar JSON", key="btn_json"):
        sig = extract_geo_signals(raw)
        if sig["valid_json"]:
            st.success("JSON válido.")
            st.json({k: v for k, v in sig.items() if k != "error"})
        else:
            st.error(sig.get("error"))

# --- Resultados ---
results = st.session_state.get("results")
if results:
    st.divider()
    t1, t2, t3, t4 = st.tabs(["Insights", "Índice IA", "Esqueleto", "Artigo"])

    with t1:
        m = results["merged"]
        st.write("**Tema:**", m.get("tema_central"))
        st.write("**Entidade:**", m.get("entidade_intencao"))
        for ins in results["insights"]:
            with st.expander(f"{ins.title} · {ins.extraction_mode}"):
                st.write("Keywords:", ", ".join(ins.keywords[:12]))
                st.write("Resumo:", ins.summary[:500])
                if ins.entities_ner:
                    st.json(ins.entities_ner)
                if ins.claims:
                    st.write("Claims:", ins.claims)

    with t2:
        st.json(results["ai_index"])
        st.caption(f"Salvo em: {results.get('index_path', '')}")
        st.download_button(
            "Download JSON",
            data=json.dumps(results["ai_index"], indent=2, ensure_ascii=False),
            file_name="geo_index.json",
            mime="application/json",
        )

    with t3:
        sk = results["skeleton"]
        st.markdown(sk.markdown)
        st.code(sk.markdown, language="markdown")

    with t4:
        art = results["article"]
        st.caption(f"Modo: **{art.provider_used or ('IA' if art.used_llm else 'local')}**")
        st.markdown(art.markdown)
        st.caption(f"Salvo em: {results.get('article_path', '')}")
        st.download_button(
            "Download Markdown",
            data=art.markdown,
            file_name="artigo_geo.md",
            mime="text/markdown",
        )

