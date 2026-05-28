"""Editor Markdown com pré-visualização lado a lado."""

from __future__ import annotations

from nicegui import ui


def normalize_preview_markdown(text: str) -> str:
    """Prepara texto para o componente ui.markdown."""
    stripped = (text or "").strip()
    return stripped if stripped else "*Sem conteúdo para pré-visualizar.*"


class ArticleSplitView:
    """Split view: textarea editável + renderização Markdown."""

    def __init__(
        self,
        markdown: str,
        *,
        footer: str = "",
        live_preview: bool = True,
        debounce_seconds: float = 0.35,
    ) -> None:
        self._debounce_seconds = debounce_seconds
        self._preview: ui.markdown
        self._editor: ui.textarea
        self._live_switch: ui.switch
        self._debounce_timer: ui.timer

        with ui.column().classes("article-split-view w-full gap-2"):
            with ui.row().classes("w-full items-center justify-between flex-wrap gap-2"):
                ui.label("Edite o Markdown à esquerda; a pré-visualização atualiza à direita.").classes(
                    "geo-meta-caption"
                )
                with ui.row().classes("items-center gap-2"):
                    self._live_switch = ui.switch("Preview em tempo real", value=live_preview).props(
                        "dense color=primary"
                    )
                    ui.button("Atualizar preview", on_click=self._refresh_preview).props(
                        "flat dense no-caps"
                    ).classes("geo-btn-outline").style(
                        "padding: 0.25rem 0.75rem !important; min-height: auto !important;"
                    )

            with ui.element("div").classes("article-split-view__panes"):
                with ui.column().classes(
                    "article-split-view__pane article-split-view__pane--editor"
                ):
                    ui.label("Editor").classes("article-split-view__pane-title")
                    self._editor = (
                        ui.textarea(value=markdown)
                        .classes("w-full geo-field geo-field--textarea article-split-view__textarea")
                        .props("outlined autogrow rows=18")
                    )

                with ui.column().classes(
                    "article-split-view__pane article-split-view__pane--preview"
                ):
                    ui.label("Pré-visualização").classes("article-split-view__pane-title")
                    with ui.element("div").classes("article-split-view__preview-scroll"):
                        self._preview = ui.markdown(
                            normalize_preview_markdown(markdown)
                        ).classes("article-split-view__markdown w-full")

            if footer:
                ui.label(footer).classes("geo-meta-caption mt-1")

        self._editor.on("update:model-value", self._on_editor_change)
        self._live_switch.on("update:model-value", self._on_live_toggle)
        self._debounce_timer = ui.timer(self._debounce_seconds, self._flush_preview, active=False)

    @property
    def content(self) -> str:
        """Conteúdo atual do editor."""
        return self._editor.value or ""

    def _refresh_preview(self) -> None:
        """Atualiza o painel Markdown com o texto do editor."""
        self._preview.set_content(normalize_preview_markdown(self._editor.value or ""))

    def _flush_preview(self) -> None:
        """Aplica preview pendente e desativa o timer."""
        self._debounce_timer.deactivate()
        self._refresh_preview()

    def _schedule_preview(self) -> None:
        """Agenda atualização com debounce."""
        self._debounce_timer.activate()

    def _on_editor_change(self, _event) -> None:
        """Reage a alterações no textarea."""
        if self._live_switch.value:
            self._schedule_preview()

    def _on_live_toggle(self, _event) -> None:
        """Liga ou desliga preview automático."""
        if self._live_switch.value:
            self._refresh_preview()
