"""Tela inicial de login (gate antes do Content Studio)."""

from __future__ import annotations

from datetime import datetime

from nicegui import ui

from ui.auth import authenticate


def render_login_gate(config, on_success, on_signup=None) -> None:
    """Formulário de login em ecrã completo (layout split + painel de marca)."""
    year = datetime.now().year

    with ui.element("div").classes("geo-auth-shell w-full"):
        with ui.element("main").classes("geo-auth-main"):
            with ui.element("div").classes("geo-auth-card"):
                with ui.element("div").classes("geo-auth-card__form"):
                    with ui.element("div").classes("geo-auth-brand"):
                        with ui.element("div").classes("geo-auth-brand__icon"):
                            ui.icon("location_on")
                        with ui.column().classes("gap-0"):
                            ui.label("GEO Extractor").classes("geo-auth-brand__title")
                            ui.label("Content Studio").classes("geo-auth-brand__tag")

                    with ui.element("div").classes("geo-auth-intro"):
                        ui.label("Olá!").classes("geo-auth-intro__title")
                        ui.label("Entre na sua conta").classes("geo-auth-intro__subtitle")

                    with ui.element("div").classes("geo-auth-fields"):
                        with ui.element("div").classes("geo-auth-field"):
                            with ui.element("div").classes("geo-auth-field__icon"):
                                ui.icon("mail", size="sm")
                            email = (
                                ui.input(placeholder="E-mail")
                                .classes("w-full geo-auth-input")
                                .props("borderless dense type=email autofocus")
                            )

                        with ui.element("div").classes("geo-auth-field"):
                            with ui.element("div").classes("geo-auth-field__icon"):
                                ui.icon("lock", size="sm")
                            password = (
                                ui.input(
                                    placeholder="Senha",
                                    password=True,
                                    password_toggle_button=True,
                                )
                                .classes("w-full geo-auth-input")
                                .props("borderless dense")
                            )

                    with ui.element("div").classes("geo-auth-options"):
                        ui.checkbox("Lembrar-me").props("dense size=sm color=primary").classes(
                            "geo-auth-checkbox"
                        )
                        ui.link("Esqueceu a senha?", "#").classes("geo-auth-link")

                    submit_btn = ui.button("Entrar").classes("geo-auth-submit-btn w-full")

                    def login() -> None:
                        submit_btn.disable()
                        try:
                            ok, message = authenticate(
                                email.value or "", password.value or ""
                            )
                        finally:
                            submit_btn.enable()
                        if not ok:
                            ui.notify(message, color="orange")
                            return
                        ui.notify("Login realizado com sucesso.", color="positive")
                        on_success()

                    submit_btn.on("click", login)
                    email.on("keydown.enter", login)
                    password.on("keydown.enter", login)

                    if on_signup:
                        with ui.row().classes("geo-auth-switch items-center justify-center gap-1"):
                            ui.label("Não tem conta?").classes("geo-auth-switch__text")
                            ui.button("Criar conta", on_click=on_signup).props(
                                "flat no-caps dense color=primary"
                            ).classes("geo-auth-switch__btn")

                with ui.element("div").classes("geo-auth-card__panel"):
                    with ui.element("div").classes("geo-auth-panel__content"):
                        ui.label("Bem-vindo de volta!").classes("geo-auth-panel__title")
                        ui.label(
                            "Aceda ao GEO Extractor Content Studio para gerar matérias, "
                            "processar URLs e publicar no seu blog local."
                        ).classes("geo-auth-panel__text")

        with ui.element("footer").classes("geo-auth-footer"):
            ui.label(f"© {year} GEO Extractor Content Studio").classes("geo-auth-footer__copy")
            with ui.row().classes("geo-auth-footer__links gap-4"):
                ui.link("Termos", "#").classes("geo-auth-footer__link")
                ui.link("Privacidade", "#").classes("geo-auth-footer__link")
                ui.link("Suporte", "#").classes("geo-auth-footer__link")
