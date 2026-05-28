"""Aba: criar matéria para blog."""

from __future__ import annotations

import json
import logging

from nicegui import run, ui

from services.blog import BlogBrief, parse_keywords
from services.blog.brief import LONG_FORM_THRESHOLD
from db.models import ArticleStatus
from services.blog_pipeline import run_blog_pipeline, run_blog_pipeline_async
from services.blog_publisher import save_post_to_blog
from ui.components.agent_progress import AgentProgressPanel
from ui.components.article_split_view import ArticleSplitView
from ui.widgets import loading_status, page_header, primary_button

logger = logging.getLogger(__name__)


def build_tab_blog(config) -> None:
    page_header(
        "Matéria original para blog",
        "Informe o tema e links de referência. A ferramenta pesquisa as fontes, "
        "aplica SEO + GEO e gera a matéria completa.",
    )

    with ui.row().classes("w-full gap-4"):
        with ui.column().classes("flex-1 gap-2"):
            topic = (
                ui.input("Tema / assunto principal", placeholder="Ex: melhor CRM para PMEs")
                .classes("w-full geo-field")
                .props("outlined dense")
            )
            keywords = ui.input(
                "Palavras-chave (vírgula)",
                placeholder="crm pequenas empresas, software vendas",
            ).classes("w-full")
            angle = ui.select(
                ["guia completo", "comparativo", "como fazer", "lista", "análise de mercado", "outro"],
                label="Ângulo editorial",
                value="guia completo",
            ).classes("w-full")
            angle_custom = ui.input("Descreva o ângulo (se outro)").classes("w-full")
            angle_custom.set_visibility(False)

            def on_angle(e):
                angle_custom.set_visibility(e.value == "outro")

            angle.on("update:model-value", on_angle)

        with ui.column().classes("flex-1 gap-2"):
            audience = ui.input("Público-alvo", value="Leitores interessados no tema").classes("w-full")
            tone = ui.select(
                ["informativo", "conversacional", "técnico", "jornalístico"],
                label="Tom",
                value="informativo",
            ).classes("w-full")
            word_count = ui.select(
                [1500, 2000, 2500, 3000, 4000, 5000, 6000],
                label="Extensão (palavras)",
                value=2500,
            ).classes("w-full")
            long_hint = ui.label("").classes("text-caption text-grey-7")
            brand = ui.input("Marca / site (opcional)").classes("w-full")
            cta = ui.input("CTA (opcional)", placeholder="Ex: Agende uma demonstração").classes("w-full")

            def on_words(e):
                if int(e.value or 0) >= LONG_FORM_THRESHOLD:
                    long_hint.set_text(
                        "Modo artigo longo: pipeline multi-agente em 2 passagens de redação (com IA)."
                    )
                else:
                    long_hint.set_text("")

            word_count.on("update:model-value", on_words)

    ui.label("Links de referência (um por linha)").classes("geo-field-label")
    refs = (
        ui.textarea(placeholder="https://...\nhttps://...")
        .classes("w-full geo-field geo-field--textarea")
        .props("outlined autogrow rows=4")
    )
    include_faq = ui.checkbox("Incluir secção FAQ (recomendado para GEO)", value=True)

    alert_box = ui.column().classes("w-full")
    result_box = ui.column().classes("w-full mt-4")

    async def generate(force_local: bool = False):
        alert_box.clear()
        result_box.clear()

        if not topic.value or not topic.value.strip():
            with alert_box:
                ui.label("Informe o tema principal.").classes("text-orange-600")
            return

        wc = int(word_count.value or 2500)
        use_llm = config.use_llm and not force_local

        if wc >= LONG_FORM_THRESHOLD and not use_llm:
            async def force_local_generate():
                await generate(force_local=True)

            with alert_box:
                ui.label(
                    "Artigos com 2.600+ palavras exigem IA para atingir a extensão. "
                    "Ative 'Gerar artigo com IA' ou continue em modo rascunho local."
                ).classes("text-red-600 font-medium")
                ui.button(
                    "Continuar mesmo assim (rascunho local)",
                    on_click=force_local_generate,
                ).props("outline color=orange")
            return

        selected_angle = angle_custom.value if angle.value == "outro" else angle.value
        brief = BlogBrief(
            topic=topic.value.strip(),
            reference_urls=[u.strip() for u in (refs.value or "").splitlines() if u.strip()],
            target_keywords=parse_keywords(keywords.value or ""),
            audience=(audience.value or "").strip() or "Leitores interessados no tema",
            tone=tone.value or "informativo",
            word_count=wc,
            brand_name=(brand.value or "").strip(),
            cta=(cta.value or "").strip(),
            include_faq=bool(include_faq.value),
            angle=selected_angle or "",
        )

        with result_box:
            progress_panel = AgentProgressPanel()

        try:
            if use_llm:
                result = await run_blog_pipeline_async(
                    brief,
                    use_advanced=config.use_advanced,
                    use_llm=True,
                    provider=config.provider,
                    manager=config.ai_manager,
                    on_progress=progress_panel.build_callback(),
                )
            else:
                result = await run.io_bound(
                    run_blog_pipeline,
                    brief,
                    use_advanced=config.use_advanced,
                    use_llm=False,
                    provider=config.provider,
                    manager=config.ai_manager,
                )
        except Exception as exc:
            logger.exception("Erro ao gerar matéria: %s", exc)
            result_box.clear()
            ui.notify(f"Erro ao gerar matéria: {exc}", type="negative")
            with alert_box:
                ui.label(f"Erro ao gerar: {exc}").classes("text-red-600")
            return

        result_box.clear()
        pkg = result.package
        meta = result.meta_payload

        with result_box:
            if result.article_id:
                ui.label(f"Salvo no histórico (#{result.article_id})").classes("text-caption text-green-8")
            elif config.use_llm or pkg.markdown:
                ui.label("Não foi possível salvar no histórico (ver logs).").classes(
                    "text-caption text-orange-8"
                )
            if result.fallback_reason:
                ui.label(result.fallback_reason).classes(
                    "bg-orange-100 text-orange-900 p-3 rounded w-full"
                )
            if result.warning:
                ui.label(result.warning).classes("bg-yellow-100 text-yellow-900 p-3 rounded w-full")

            with ui.row().classes("w-full gap-4"):
                if pkg.generation_mode.startswith("multi_agent"):
                    ui.label("Pipeline: multi-agente (Pesquisador → Redator → Editor)").classes(
                        "text-caption text-primary"
                    )
                ui.label(f"Modo: {pkg.generation_mode}").classes("text-caption")
                ui.label(f"Palavras: {pkg.word_count_actual}/{pkg.word_count_target}").classes(
                    "text-caption"
                )
                ui.label(f"Referências: {len(pkg.insights)}").classes("text-caption")

            with ui.tabs().classes("w-full") as tabs:
                t_art = ui.tab("Artigo")
                t_idx = ui.tab("Índice IA")
                t_seo = ui.tab("SEO")
                t_skel = ui.tab("Esqueleto GEO")

            with ui.tab_panels(tabs, value=t_art).classes("w-full"):
                with ui.tab_panel(t_art):
                    split_view = ArticleSplitView(
                        pkg.markdown,
                        footer=f"Salvo: {result.md_path}",
                        live_preview=True,
                    )
                    article_state: dict[str, int | None] = {"id": result.article_id}

                    async def save_to_blog() -> None:
                        """Salva ou atualiza a matéria no blog local (Content Studio)."""
                        try:
                            save_result = await save_post_to_blog(
                                title=meta.get("meta_title", "") or pkg.meta_title,
                                markdown_content=split_view.content,
                                json_index=pkg.ai_index or None,
                                article_id=article_state["id"],
                                status=ArticleStatus.DRAFT.value,
                            )
                            article_state["id"] = save_result.article_id
                            ui.notify(
                                f"Matéria salva no blog (#{save_result.article_id}, {save_result.status}).",
                                type="positive",
                            )
                        except Exception as exc:
                            logger.exception("Falha ao salvar no blog local: %s", exc)
                            ui.notify(f"Erro ao salvar no blog: {exc}", type="negative")

                    ui.button(
                        "Salvar no blog",
                        on_click=save_to_blog,
                    ).props("color=secondary icon=save").classes("mt-3")
                    ui.label(
                        "O blog é o histórico local do Content Studio — abra a aba «Histórico» para reeditar."
                    ).classes("text-caption text-grey-7")
                with ui.tab_panel(t_idx):
                    ui.label(
                        "O índice foi aplicado automaticamente na geração com IA "
                        "(consultas, keywords, citações)."
                    ).classes("text-caption text-grey-7 mb-2")
                    ui.code(
                        json.dumps(pkg.ai_index, indent=2, ensure_ascii=False),
                        language="json",
                    ).classes("w-full")
                    if result.index_path:
                        ui.label(f"Salvo: {result.index_path}").classes("text-caption")
                with ui.tab_panel(t_seo):
                    ui.input("Meta title", value=meta.get("meta_title", "")).props("readonly").classes(
                        "w-full"
                    )
                    ui.textarea(
                        "Meta description", value=meta.get("meta_description", "")
                    ).props("readonly").classes("w-full")
                    ui.input("Slug", value=meta.get("slug", "")).props("readonly").classes("w-full")
                    ui.label("Keywords: " + ", ".join(meta.get("keywords", [])))
                    if meta.get("faq"):
                        ui.code(
                            json.dumps(meta["faq"], indent=2, ensure_ascii=False),
                            language="json",
                        ).classes("w-full")
                with ui.tab_panel(t_skel):
                    ui.markdown(pkg.skeleton.markdown).classes("w-full")

    primary_button("Gerar matéria para blog", generate, icon="auto_awesome")
