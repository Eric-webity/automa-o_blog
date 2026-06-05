"""Aba: histórico de matérias do blog local (layout Content Studio)."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime

from nicegui import run, ui

from db.models import ArticleStatus
from db.repository import ArticleRecord
from services.analytics import get_dashboard_stats
from services.article_history import parse_import_payload
from services.blog_publisher import save_post_to_blog
from ui.auth import is_admin, require_session_user_id, session_email
from ui.history_scope import (
    HISTORY_SCOPE_ALL,
    HISTORY_SCOPE_ALL_LABEL,
    build_scope_select_options,
    count_drafts,
    filter_drafts_only,
    history_import_owner_id,
    history_list_records,
    history_list_repository,
    history_mutate_owner_id,
    history_page_caption,
    history_stats_user_id,
    load_user_name_labels,
    record_accessible,
    scope_label_for_id,
    sort_history_records,
)
from ui.session_scope import sync_config_session
from ui.components.article_split_view import ArticleSplitView
from ui.components.cms_publish_button import mount_cms_publish_button
from ui.components.faq_jsonld_export import render_faq_jsonld_export
from ui.constants import article_status_label, history_status_pill_html
from ui.pages.routes import ROUTE_URLS
from ui.widgets import page_header

logger = logging.getLogger(__name__)

_STORAGE_QUOTA_BYTES = 100 * 1024 * 1024


def _format_date(value: datetime) -> str:
    if value.tzinfo:
        value = value.replace(tzinfo=None)
    return value.strftime("%d/%m/%Y %H:%M")


def build_tab_history(config) -> None:
    """Lista matérias salvas com reabrir, atualizar e excluir."""
    stats_container = ui.element("div").classes("geo-history-stats-grid w-full")
    workspace = ui.element("div").classes("geo-history-workspace w-full")
    main_container = ui.element("div").classes("geo-history-main w-full")
    detail_container = ui.column().classes("geo-history-detail-slot w-full")
    active_id: dict[str, int | None] = {"id": None}
    last_records: list[ArticleRecord] = []
    history_filter: dict[str, int | None] = {
        "user_id": HISTORY_SCOPE_ALL if is_admin() else None,
    }
    scope_options: dict[str, int | None] = {}
    user_labels: dict[int, str] = {}
    caption_label: dict[str, object] = {"el": None}
    scope_select_ref: dict[str, object] = {"el": None}
    pending_open: dict[str, int | None] = {"id": None}
    list_filter: dict[str, bool] = {"drafts_only": False}

    search_ref: dict = {"el": None}

    def _scope_user_id() -> int | None:
        if is_admin():
            return history_filter.get("user_id", HISTORY_SCOPE_ALL)
        return None

    def _list_repo():
        return history_list_repository(
            session_user_id=require_session_user_id(),
            is_admin=is_admin(),
            scope_user_id=_scope_user_id(),
        )

    def _mutate_owner(record: ArticleRecord) -> tuple[int | None, str | None]:
        return history_mutate_owner_id(
            record,
            session_user_id=require_session_user_id(),
            is_admin=is_admin(),
            scope_user_id=_scope_user_id(),
        )

    def _show_account_on_items() -> bool:
        return is_admin() and _scope_user_id() is HISTORY_SCOPE_ALL

    def _refresh_caption(filtered_name: str | None = None) -> None:
        label = caption_label.get("el")
        if label is None:
            return
        label.text = history_page_caption(
            is_admin=is_admin(),
            scope_user_id=_scope_user_id(),
            session_email=session_email(),
            filtered_name=filtered_name,
        )

    def _on_scope_change() -> None:
        select = scope_select_ref.get("el")
        if select is not None:
            history_filter["user_id"] = scope_options.get(
                select.value,
                HISTORY_SCOPE_ALL,
            )
        clear_detail()
        asyncio.create_task(refresh_list())

    def _clear_drafts_filter() -> None:
        list_filter["drafts_only"] = False
        asyncio.create_task(refresh_list())

    def _toggle_drafts_filter() -> None:
        list_filter["drafts_only"] = not list_filter["drafts_only"]
        asyncio.create_task(refresh_list())

    def _open_import_dialog() -> None:
        with ui.dialog() as dialog, ui.card().classes("geo-import-dialog p-4 gap-3"):
            ui.label("Importar matéria para o histórico").classes("text-h6")
            ui.label(
                "Cole o Markdown e, se tiver, o JSON de metadados (índice IA, FAQ, SEO). "
                "A matéria entra como rascunho para revisão e aprovação."
                + (
                    " Administrador: indique o nome do utilizador destino."
                    if is_admin()
                    else ""
                )
            ).classes("geo-page-desc !mt-0")
            import_title = (
                ui.input("Título", placeholder="Título da matéria")
                .props("outlined dense")
                .classes("w-full")
            )
            import_md = (
                ui.textarea("Conteúdo (Markdown)", placeholder="# Artigo…")
                .props("outlined rows=12")
                .classes("w-full")
            )
            import_json = (
                ui.textarea(
                    "Metadados JSON (opcional)",
                    placeholder='{"meta_title": "...", "faq": []}',
                )
                .props("outlined rows=6")
                .classes("w-full")
            )
            import_user_name = None
            if is_admin():
                import_user_name = (
                    ui.input(
                        "Nome do utilizador",
                        placeholder="Nome da conta destino (ex.: Maria Silva)",
                    )
                    .props("outlined dense")
                    .classes("w-full")
                )

            async def _do_import() -> None:
                owner_id, owner_err = history_import_owner_id(
                    is_admin=is_admin(),
                    scope_user_id=_scope_user_id(),
                    session_user_id=require_session_user_id(),
                    import_username=(
                        import_user_name.value if import_user_name is not None else ""
                    ),
                )
                if owner_err or owner_id is None:
                    ui.notify(owner_err or "Utilizador inválido.", type="warning")
                    return
                payload, err = parse_import_payload(
                    title=import_title.value or "",
                    markdown=import_md.value or "",
                    json_raw=import_json.value or "",
                )
                if err or not payload:
                    ui.notify(err or "Dados inválidos.", type="warning")
                    return
                try:
                    result = await save_post_to_blog(
                        title=payload["title"],
                        markdown_content=payload["markdown_content"],
                        json_index=payload.get("json_index"),
                        status=ArticleStatus.DRAFT.value,
                        user_id=owner_id,
                    )
                except Exception as exc:
                    logger.exception("Falha ao importar matéria: %s", exc)
                    ui.notify(f"Erro ao importar: {exc}", type="negative")
                    return
                ui.notify(
                    f"Matéria #{result.article_id} importada para aprovação (rascunho).",
                    type="positive",
                )
                dialog.close()
                record = _list_repo().get_by_id(result.article_id)
                if record:
                    show_article(record)
                await refresh_list()

            with ui.row().classes("w-full justify-end gap-2 mt-2"):
                ui.button("Cancelar", on_click=dialog.close).props("flat no-caps")
                ui.button("Importar", icon="upload", on_click=_do_import).props(
                    "color=primary unelevated no-caps"
                )

        dialog.open()

    def _history_actions() -> None:
        with ui.row().classes(
            "geo-history-header-actions items-center gap-2 flex-wrap"
        ):
            ui.button(
                "Importar matéria",
                icon="upload",
                on_click=_open_import_dialog,
            ).props("outline dense no-caps color=primary")
            with ui.row().classes("geo-history-search items-center flex-grow"):
                ui.icon("search").classes("text-grey-6")
                search_ref["el"] = (
                    ui.input(
                        placeholder=(
                            "Pesquisar por título ou nome de utilizador…"
                            if is_admin()
                            else "Pesquisar histórico…"
                        )
                    )
                    .props("borderless dense")
                    .classes("flex-grow")
                )

    with ui.element("div").classes("geo-history-page w-full"):
        page_header(
            "Histórico do blog",
            None,
            eyebrow="Biblioteca",
            actions=_history_actions,
        )
        caption_label["el"] = ui.label(
            history_page_caption(
                is_admin=is_admin(),
                scope_user_id=_scope_user_id(),
                session_email=session_email(),
            )
        ).classes("geo-page-desc geo-history-scope-caption w-full")
        if is_admin():
            scope_options.update(build_scope_select_options())
            with ui.row().classes(
                "geo-history-scope-filter w-full items-center gap-2 flex-wrap"
            ):
                ui.icon("filter_alt").classes("text-grey-7")
                ui.label("Utilizador").classes("text-caption text-grey-8")
                scope_select_ref["el"] = (
                    ui.select(
                        scope_options,
                        value=scope_label_for_id(
                            history_filter["user_id"], scope_options
                        ),
                        on_change=_on_scope_change,
                    )
                    .props("outlined dense options-dense")
                    .classes("geo-history-scope-select flex-grow")
                )
        search_input = search_ref["el"]

        stats_container

        with workspace:
            main_container
            detail_container

        with ui.element("div").classes("geo-history-tips-grid w-full"):
            if is_admin():
                tip_primary = (
                    "<h3>Filtrar por nome</h3>"
                    "<p>Escolha um utilizador no seletor acima para ver só o histórico "
                    "dessa conta, ou «Todas as contas» para visão global.</p>"
                )
                tip_secondary = (
                    "<h3>Importar pelo nome</h3>"
                    "<p>No diálogo de importação, preencha o nome do utilizador destino "
                    "exactamente como está no Perfil.</p>"
                )
                icon_primary, icon_secondary = "manage_accounts", "person_add"
            else:
                tip_primary = (
                    "<h3>O seu histórico</h3>"
                    "<p>Só vê e edita matérias da sua conta. Outros utilizadores "
                    "têm bibliotecas separadas.</p>"
                )
                tip_secondary = (
                    "<h3>Sem acesso a administradores</h3>"
                    "<p>Matérias guardadas por contas de administrador não aparecem "
                    "no seu histórico.</p>"
                )
                icon_primary, icon_secondary = "lock", "admin_panel_settings"
            with ui.element("div").classes("geo-history-tip-card"):
                with ui.element("div").classes(
                    "geo-history-tip-card__icon geo-history-tip-card__icon--primary"
                ):
                    ui.icon(icon_primary)
                with ui.column().classes("gap-0"):
                    ui.html(tip_primary)
            with ui.element("div").classes("geo-history-tip-card"):
                with ui.element("div").classes(
                    "geo-history-tip-card__icon geo-history-tip-card__icon--secondary"
                ):
                    ui.icon(icon_secondary)
                with ui.column().classes("gap-0"):
                    ui.html(tip_secondary)

    def clear_detail() -> None:
        detail_container.clear()
        active_id["id"] = None
        workspace.classes(remove="geo-history-workspace--with-detail")

    def render_stats(data: dict) -> None:
        total = data.get("total_articles", 0)
        draft_count = count_drafts(data.get("by_status"))
        completed_count = int(
            (data.get("by_status") or {}).get(ArticleStatus.COMPLETED.value, 0)
        )
        storage_bytes = data.get("storage_db_bytes", 0) + data.get(
            "storage_output_bytes", 0
        )
        storage_label = data.get("storage_db_label", "0 B")
        storage_pct = min(100, int(storage_bytes / _STORAGE_QUOTA_BYTES * 100))

        stats_container.clear()
        with stats_container:
            with ui.element("div").classes("geo-history-stat-card"):
                ui.label("Total no histórico").classes("geo-history-stat-card__label")
                with ui.element("div").classes("geo-history-stat-card__row"):
                    ui.label(str(total)).classes(
                        "geo-history-stat-card__value geo-history-stat-card__value--primary"
                    )
                    ui.label("matérias").classes("geo-history-stat-card__suffix")

            with ui.element("div").classes(
                "geo-history-stat-card geo-history-stat-card--draft"
            ):
                ui.label("Em rascunho").classes("geo-history-stat-card__label")
                with ui.element("div").classes("geo-history-stat-card__row"):
                    ui.label(str(draft_count)).classes(
                        "geo-history-stat-card__value geo-history-stat-card__value--secondary"
                    )
                    ui.label("aguardam aprovação").classes(
                        "geo-history-stat-card__suffix"
                    )

            with ui.element("div").classes("geo-history-stat-card"):
                ui.label("Concluídas").classes("geo-history-stat-card__label")
                with ui.element("div").classes("geo-history-stat-card__row"):
                    ui.label(str(completed_count)).classes(
                        "geo-history-stat-card__value geo-history-stat-card__value--tertiary"
                    )
                    ui.label("aprovadas").classes("geo-history-stat-card__suffix")

    def show_article(record: ArticleRecord) -> None:
        active_id["id"] = record.id
        workspace.classes(add="geo-history-workspace--with-detail")
        detail_container.clear()
        with detail_container:
            with ui.element("div").classes("geo-history-detail w-full"):
                with ui.row().classes(
                    "w-full items-start justify-between flex-wrap gap-2 mb-2"
                ):
                    with ui.column().classes("gap-0"):
                        ui.label(record.title).classes("text-h6 font-medium")
                        detail_meta = (
                            f"#{record.id} · {_format_date(record.created_at)}"
                        )
                        if _show_account_on_items() and record.user_id:
                            owner = user_labels.get(
                                record.user_id, f"Conta #{record.user_id}"
                            )
                            detail_meta = f"{detail_meta} · {owner}"
                        ui.label(detail_meta).classes("text-caption text-grey-7")
                    ui.html(history_status_pill_html(record.status))

                with ui.tabs().classes("w-full geo-inner-tabs") as detail_tabs:
                    t_art = ui.tab("Artigo")
                    t_faq_ld = ui.tab("FAQ JSON-LD")
                    t_idx = ui.tab("Índice IA")

                with ui.tab_panels(detail_tabs, value=t_art).classes(
                    "w-full geo-history-tab-panels"
                ):
                    with ui.tab_panel(t_art).classes("geo-history-article-panel"):
                        is_draft = record.status == ArticleStatus.DRAFT.value
                        if is_draft:
                            with ui.row().classes(
                                "geo-history-draft-banner w-full items-center gap-2 mb-2"
                            ):
                                ui.icon("sync", color="warning")
                                ui.label(
                                    "Em rascunho — revise o conteúdo e use «Aprovar matéria» "
                                    "para marcar como concluída (como no Dashboard)."
                                ).classes("text-body2")

                        split_view = ArticleSplitView(
                            record.markdown_content,
                            footer=f"Blog local · matéria #{record.id} · {record.status}",
                            live_preview=True,
                            layout_class="article-split-view--history",
                        )

                        def _merged_index() -> dict:
                            idx = dict(record.json_index or {})
                            idx.setdefault("meta_title", record.title)
                            return idx

                        async def _reload_article(article_id: int) -> None:
                            refreshed = _list_repo().get_by_id(article_id)
                            if refreshed and record_accessible(
                                refreshed,
                                session_user_id=require_session_user_id(),
                                is_admin=is_admin(),
                            ):
                                show_article(refreshed)

                        async def save_draft() -> None:
                            owner_id, owner_err = _mutate_owner(record)
                            if owner_err or owner_id is None:
                                ui.notify(owner_err or "Sem permissão.", type="warning")
                                return
                            try:
                                result = await save_post_to_blog(
                                    title=record.title,
                                    markdown_content=split_view.content,
                                    json_index=_merged_index(),
                                    article_id=record.id,
                                    status=ArticleStatus.DRAFT.value,
                                    user_id=owner_id,
                                )
                                ui.notify(
                                    f"Rascunho #{result.article_id} guardado no histórico.",
                                    type="positive",
                                )
                                await _reload_article(result.article_id)
                                await refresh_list()
                            except Exception as exc:
                                logger.exception("Falha ao guardar rascunho: %s", exc)
                                ui.notify(f"Erro ao guardar: {exc}", type="negative")

                        async def approve_article() -> None:
                            owner_id, owner_err = _mutate_owner(record)
                            if owner_err or owner_id is None:
                                ui.notify(owner_err or "Sem permissão.", type="warning")
                                return
                            try:
                                result = await save_post_to_blog(
                                    title=record.title,
                                    markdown_content=split_view.content,
                                    json_index=_merged_index(),
                                    article_id=record.id,
                                    status=ArticleStatus.COMPLETED.value,
                                    user_id=owner_id,
                                )
                                ui.notify(
                                    f"Matéria #{result.article_id} aprovada — estado: concluída.",
                                    type="positive",
                                )
                                await _reload_article(result.article_id)
                                await refresh_list()
                            except Exception as exc:
                                logger.exception("Falha ao aprovar matéria: %s", exc)
                                ui.notify(f"Erro ao aprovar: {exc}", type="negative")

                        def _record_meta() -> dict:
                            idx = _merged_index()
                            return {
                                "meta_title": idx.get("meta_title") or record.title,
                                "meta_description": idx.get("meta_description", ""),
                                "slug": idx.get("slug", ""),
                                "keywords": idx.get("keywords") or [],
                            }

                        with ui.row().classes(
                            "gap-2 mt-3 flex-wrap geo-history-article-actions"
                        ):
                            ui.button(
                                "Guardar rascunho",
                                on_click=save_draft,
                            ).props(
                                "outline icon=save"
                                if is_draft
                                else "color=primary icon=save"
                            )
                            approve_btn = ui.button(
                                "Aprovar matéria",
                                on_click=approve_article,
                            )
                            if is_draft:
                                approve_btn.props(
                                    "color=positive unelevated icon=check_circle"
                                )
                            else:
                                ui.label(
                                    "Estado: concluída — pode republicar no CMS."
                                ).classes("text-caption text-grey-7 self-center")
                            mount_cms_publish_button(
                                get_title=lambda: record.title,
                                get_markdown=lambda: split_view.content,
                                get_meta=_record_meta,
                            )

                    with ui.tab_panel(t_faq_ld):
                        idx = record.json_index or {}
                        render_faq_jsonld_export(
                            faq_items=idx.get("faq"),
                            markdown=record.markdown_content,
                            page_title=record.title,
                            slug=idx.get("slug", ""),
                        )

                    with ui.tab_panel(t_idx):
                        if record.json_index:
                            ui.code(
                                json.dumps(
                                    record.json_index, indent=2, ensure_ascii=False
                                ),
                                language="json",
                            ).classes("w-full")
                        else:
                            ui.label("Sem índice IA salvo para esta matéria.").classes(
                                "text-caption text-grey-7"
                            )

        if last_records:
            render_article_list(last_records, show_account=_show_account_on_items())

    def render_empty_state() -> None:
        main_container.clear()
        with main_container:
            with ui.element("div").classes(
                "geo-history-panel geo-history-panel--empty"
            ):
                ui.element("div").classes(
                    "geo-history-panel__blob geo-history-panel__blob--tr"
                )
                ui.element("div").classes(
                    "geo-history-panel__blob geo-history-panel__blob--bl"
                )
                with ui.element("div").classes("geo-history-empty"):
                    with ui.element("div").classes("geo-history-empty__icon"):
                        ui.icon("inventory_2", size="xl")
                    ui.label("Nada por aqui ainda").classes("geo-history-empty__title")
                    empty_desc = (
                        "Não há matérias guardadas nesta conta. Outro utilizador na "
                        "mesma instalação tem o histórico separado — faça login com a "
                        "conta correta ou comece a gerar conteúdo."
                    )
                    if is_admin() and _scope_user_id() is HISTORY_SCOPE_ALL:
                        empty_desc = (
                            "Nenhuma matéria em nenhuma conta ainda. Cada utilizador "
                            "acumula o seu histórico ao gerar ou importar conteúdo."
                        )
                    elif is_admin() and isinstance(_scope_user_id(), int):
                        email = user_labels.get(_scope_user_id(), "esta conta")
                        empty_desc = (
                            f"Não há matérias em {email}. Importe ou peça ao "
                            "utilizador para gerar conteúdo."
                        )
                    ui.label(empty_desc).classes("geo-history-empty__desc")
                    with ui.element("div").classes("geo-history-empty__actions"):
                        ui.button(
                            "Atualizar lista",
                            icon="refresh",
                            on_click=refresh_list,
                        ).classes("geo-history-refresh-btn")
                        ui.button(
                            "Ir para URLs",
                            on_click=lambda: ui.navigate.to(ROUTE_URLS),
                        ).classes("geo-history-secondary-btn")

    def render_article_list(
        records: list[ArticleRecord],
        *,
        show_account: bool = False,
    ) -> None:
        main_container.clear()
        with main_container:
            with ui.element("div").classes("geo-history-panel"):
                ui.element("div").classes(
                    "geo-history-panel__blob geo-history-panel__blob--tr"
                )
                with ui.row().classes(
                    "w-full items-center justify-between mb-4 relative z-10 flex-wrap gap-2"
                ):
                    ui.label(f"{len(records)} matéria(s)").classes("geo-section-title")
                    with ui.row().classes("items-center gap-2"):
                        ui.button(
                            "Só rascunhos",
                            icon="filter_list",
                            on_click=_toggle_drafts_filter,
                        ).props(
                            "dense no-caps "
                            + (
                                "color=warning unelevated"
                                if list_filter["drafts_only"]
                                else "outline color=primary"
                            )
                        )

                        ui.button(
                            "Atualizar lista",
                            icon="refresh",
                            on_click=refresh_list,
                        ).props("flat dense color=primary")

                with ui.element("div").classes("geo-history-list"):
                    for record in records:
                        words = len((record.markdown_content or "").split())
                        is_active = active_id["id"] == record.id
                        is_draft_item = record.status == ArticleStatus.DRAFT.value
                        item_cls = "geo-history-item"
                        if is_active:
                            item_cls += " geo-history-item--active"
                        if is_draft_item:
                            item_cls += " geo-history-item--draft"

                        with ui.row().classes(f"{item_cls} w-full items-center"):
                            with ui.column().classes(
                                "gap-0 flex-grow min-w-0 cursor-pointer"
                            ).on("click", lambda _e, r=record: show_article(r)):
                                with ui.row().classes(
                                    "items-center gap-2 w-full min-w-0"
                                ):
                                    ui.label(record.title).classes(
                                        "geo-history-item__title"
                                    )
                                    if is_draft_item:
                                        ui.html(history_status_pill_html(record.status))
                                meta_parts = [
                                    f"#{record.id}",
                                    _format_date(record.created_at),
                                    f"{words} palavras",
                                    article_status_label(record.status),
                                ]
                                if show_account and record.user_id:
                                    meta_parts.insert(
                                        1,
                                        user_labels.get(
                                            record.user_id,
                                            f"conta #{record.user_id}",
                                        ),
                                    )
                                ui.label(" · ".join(meta_parts)).classes(
                                    "geo-history-item__meta"
                                )
                            with ui.row().classes("gap-1 flex-shrink-0"):
                                ui.button(
                                    icon="open_in_new",
                                    on_click=lambda _e, r=record: show_article(r),
                                ).props("flat round dense color=primary")
                                ui.button(
                                    icon="delete",
                                    on_click=lambda _e, r=record: asyncio.create_task(
                                        delete_article(r)
                                    ),
                                ).props("flat round dense color=negative")

    async def refresh_list() -> None:
        try:
            sync_config_session(config)
            session_id = require_session_user_id()
            scope = _scope_user_id()
            stats_uid = history_stats_user_id(
                session_user_id=session_id,
                is_admin=is_admin(),
                scope_user_id=scope,
            )

            def _load():
                labels = load_user_name_labels()
                return (
                    get_dashboard_stats(user_id=stats_uid),
                    history_list_records(
                        session_user_id=session_id,
                        is_admin=is_admin(),
                        scope_user_id=scope,
                    ),
                    labels,
                )

            data, records, labels = await run.io_bound(_load)
        except RuntimeError:
            return
        except Exception as exc:
            logger.exception("Erro ao carregar histórico: %s", exc)
            ui.notify(f"Erro ao carregar histórico: {exc}", type="negative")
            return

        user_labels.clear()
        user_labels.update(labels)
        filtered_name = None
        if isinstance(scope, int):
            filtered_name = user_labels.get(scope)
        _refresh_caption(filtered_name)
        select_el = scope_select_ref.get("el")
        if select_el is not None and is_admin():
            scope_options.clear()
            scope_options.update(build_scope_select_options())
            select_el.set_options(
                scope_options,
                value=scope_label_for_id(history_filter.get("user_id"), scope_options),
            )

        render_stats(data)

        query = (search_input.value or "").strip().lower()
        if query:
            show_acc = _show_account_on_items()

            def _matches(record: ArticleRecord) -> bool:
                if query in (record.title or "").lower():
                    return True
                if record.user_id:
                    owner = user_labels.get(record.user_id, "")
                    if query in owner.lower():
                        return True
                return False

            records = [r for r in records if _matches(r)]

        records = sort_history_records(records)
        records = filter_drafts_only(records, enabled=list_filter["drafts_only"])

        if not records:
            if list_filter["drafts_only"]:
                main_container.clear()
                with main_container:
                    with ui.element("div").classes(
                        "geo-history-panel geo-history-panel--empty"
                    ):
                        with ui.element("div").classes("geo-history-empty"):
                            ui.icon("drafts", size="xl").classes("text-grey-6")
                            ui.label("Nenhum rascunho pendente").classes(
                                "geo-history-empty__title"
                            )
                            ui.label(
                                "Todas as matérias estão concluídas ou arquivadas, "
                                "ou o filtro de pesquisa não encontrou rascunhos."
                            ).classes("geo-history-empty__desc")
                            ui.button(
                                "Ver todas as matérias",
                                icon="list",
                                on_click=_clear_drafts_filter,
                            ).props("color=primary unelevated no-caps")

                clear_detail()
                last_records.clear()
                return
            render_empty_state()
            clear_detail()
            last_records.clear()
            return

        last_records.clear()
        last_records.extend(records)
        render_article_list(records, show_account=_show_account_on_items())

        if pending_open["id"] is not None:
            open_id = pending_open["id"]
            pending_open["id"] = None
            record = _list_repo().get_by_id(open_id)
            if record_accessible(
                record,
                session_user_id=require_session_user_id(),
                is_admin=is_admin(),
            ):
                show_article(record)
            else:
                ui.notify(
                    "Matéria não encontrada ou sem permissão (ex.: histórico de administrador).",
                    type="warning",
                )
        elif active_id["id"] is not None:
            match = next((r for r in records if r.id == active_id["id"]), None)
            if match:
                show_article(match)
            else:
                clear_detail()

    async def delete_article(record: ArticleRecord) -> None:
        if not record_accessible(
            record,
            session_user_id=require_session_user_id(),
            is_admin=is_admin(),
        ):
            ui.notify("Sem permissão para remover esta matéria.", type="warning")
            return
        try:
            deleted = await run.io_bound(_list_repo().delete, record.id)
        except Exception as exc:
            logger.exception("Erro ao excluir artigo id=%s: %s", record.id, exc)
            ui.notify(f"Erro ao excluir: {exc}", type="negative")
            return
        if deleted:
            ui.notify("Matéria removida do histórico.", type="positive")
            if active_id["id"] == record.id:
                clear_detail()
            await refresh_list()
        else:
            ui.notify("Matéria não encontrada.", type="warning")

    def open_article_by_id(article_id: int) -> None:
        """Abre após ``refresh_list`` (ex.: Dashboard «Em rascunho» → ?article=)."""
        pending_open["id"] = article_id
        if last_records:
            record = _list_repo().get_by_id(article_id)
            if record_accessible(
                record,
                session_user_id=require_session_user_id(),
                is_admin=is_admin(),
            ):
                pending_open["id"] = None
                show_article(record)
            else:
                pending_open["id"] = None
                ui.notify(
                    "Matéria não encontrada ou sem permissão (ex.: histórico de administrador).",
                    type="warning",
                )
        else:
            asyncio.create_task(refresh_list())

    config.open_history_article = open_article_by_id
    search_input.on("update:model-value", lambda _: asyncio.create_task(refresh_list()))

    asyncio.create_task(refresh_list())
