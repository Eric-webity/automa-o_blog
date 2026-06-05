"""Tela de cadastro (gate antes do Content Studio)."""

from __future__ import annotations

from nicegui import ui

from ui.auth import register_user


def _signup_field(label: str, icon: str, placeholder: str, **input_kwargs) -> ui.input:
    ui.label(label).classes("geo-signup-field-label")
    with ui.element("div").classes("geo-auth-field geo-signup-field"):
        with ui.element("div").classes("geo-auth-field__icon geo-signup-field__icon"):
            ui.icon(icon)
        field = ui.input(placeholder=placeholder, **input_kwargs).classes("w-full").props(
            "borderless dense"
        )
    return field


def render_signup_gate(config, on_success, on_login) -> None:
    """Formulário de cadastro em ecrã completo."""
    with ui.element("div").classes("geo-auth-shell w-full"):
        with ui.element("main").classes("geo-auth-main"):
            with ui.element("div").classes("geo-auth-card geo-signup-card"):
                with ui.element("section").classes("geo-auth-card__form geo-signup-form"):
                    with ui.element("div").classes("geo-auth-brand geo-login-brand"):
                        with ui.element("div").classes("geo-auth-brand__icon geo-login-brand__icon"):
                            ui.icon("location_on")
                        with ui.column().classes("gap-0"):
                            ui.label("GEO Extractor").classes("geo-auth-brand__title geo-login-brand__title")
                            ui.label("Content Studio").classes("geo-auth-brand__tag geo-login-brand__tag")
                    with ui.element("div").classes("geo-auth-intro geo-signup-header"):
                        ui.label("Crie sua conta").classes("geo-auth-intro__title geo-signup-header__title")
                        ui.label("Comece sua jornada no Content Studio hoje.").classes(
                            "geo-auth-intro__subtitle geo-signup-header__subtitle"
                        )

                    name = _signup_field(
                        "Nome Completo",
                        "person",
                        "Como deseja ser chamado?",
                    )
                    email = _signup_field(
                        "E-mail Profissional",
                        "mail",
                        "exemplo@empresa.com",
                    ).props("type=email")

                    with ui.element("div").classes("geo-signup-password-grid"):
                        password = _signup_field(
                            "Senha",
                            "lock",
                            "••••••••",
                            password=True,
                            password_toggle_button=True,
                        )
                        confirm = _signup_field(
                            "Confirmar",
                            "verified_user",
                            "••••••••",
                            password=True,
                            password_toggle_button=True,
                        )

                    terms = ui.checkbox(
                        "Concordo com os Termos de Serviço e a Política de Privacidade."
                    ).props("dense size=xs color=primary").classes("geo-signup-terms")

                    def submit() -> None:
                        ok, message = register_user(
                            name.value or "",
                            email.value or "",
                            password.value or "",
                            confirm.value or "",
                            accepted_terms=bool(terms.value),
                        )
                        if not ok:
                            ui.notify(message, color="orange")
                            return
                        ui.notify("Conta criada com sucesso!", color="positive")
                        on_success()

                    ui.button("Criar minha conta", icon="arrow_forward", on_click=submit).props(
                        "no-caps unelevated"
                    ).classes("geo-auth-submit-btn geo-signup-submit-btn w-full")

                    with ui.element("div").classes("geo-signup-divider"):
                        ui.label("OU CADASTRE COM").classes("geo-signup-divider__text")

                    with ui.element("div").classes("geo-signup-social-grid"):
                        ui.button("Google", icon="public").props("no-caps outline").classes(
                            "geo-signup-social-btn"
                        ).on(
                            "click",
                            lambda: ui.notify("Cadastro social em breve.", color="info"),
                        )
                        ui.button("GitHub", icon="code").props("no-caps outline").classes(
                            "geo-signup-social-btn"
                        ).on(
                            "click",
                            lambda: ui.notify("Cadastro social em breve.", color="info"),
                        )

                    with ui.row().classes("geo-signup-footer items-center justify-center gap-1"):
                        ui.label("Já tem uma conta?").classes("text-xs text-grey-7")
                        ui.button("Faça login", on_click=on_login).props(
                            "flat no-caps dense color=primary"
                        ).classes("geo-signup-login-link")

                with ui.element("section").classes("geo-auth-card__panel geo-signup-brand"):
                    ui.html('<span class="geo-signup-brand__badge">Content Studio v2.0</span>')
                    ui.label("Construa o futuro da extração GEO.").classes(
                        "geo-signup-brand__title"
                    )
                    ui.label(
                        "Junte-se à nossa comunidade de criadores e transforme dados "
                        "geográficos em experiências visuais impressionantes em segundos."
                    ).classes("geo-signup-brand__text")

                    with ui.column().classes("w-full gap-3 mt-6"):
                        with ui.element("div").classes("geo-signup-feature"):
                            with ui.element("div").classes("geo-signup-feature__icon"):
                                ui.icon("auto_awesome")
                            with ui.column().classes("gap-0"):
                                ui.label("IA Avançada").classes("geo-signup-feature__title")
                                ui.label("Extração inteligente de metadados.").classes(
                                    "geo-signup-feature__desc"
                                )
                        with ui.element("div").classes("geo-signup-feature"):
                            with ui.element("div").classes("geo-signup-feature__icon"):
                                ui.icon("cloud_sync")
                            with ui.column().classes("gap-0"):
                                ui.label("Cloud Native").classes("geo-signup-feature__title")
                                ui.label("Acesse seus projetos em qualquer lugar.").classes(
                                    "geo-signup-feature__desc"
                                )
