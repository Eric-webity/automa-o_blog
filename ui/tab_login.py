"""Tela inicial de login (gate antes do Content Studio)."""

from __future__ import annotations

from nicegui import ui

from ui.auth import authenticate


def render_login_gate(config, on_success, on_signup=None) -> None:
    """Formulário de login em ecrã completo."""
    with ui.element("div").classes("geo-login-shell w-full"):
        with ui.element("div").classes("geo-login-page w-full"):
            with ui.element("div").classes("geo-login-card"):
                with ui.element("div").classes("geo-login-card__wave"):
                    ui.html(
                        """
<svg viewBox="0 0 1000 648" preserveAspectRatio="none" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="geoLoginGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#8b5cf6"/>
      <stop offset="100%" style="stop-color:#3b82f6"/>
    </linearGradient>
  </defs>
  <path d="M1000,0 L400,0 C550,150 400,300 600,450 C700,550 500,600 300,648 L1000,648 Z" fill="url(#geoLoginGrad)"/>
  <path d="M0,0 L400,0 C550,150 400,300 600,450 C700,550 500,600 300,648 L0,648 Z" fill="#ffffff"/>
</svg>
                        """
                    )

                with ui.element("section").classes("geo-login-form"):
                    with ui.element("div").classes("geo-login-brand"):
                        with ui.element("div").classes("geo-login-brand__icon"):
                            ui.icon("location_on")
                        with ui.column().classes("gap-0"):
                            ui.label("GEO Extractor").classes("geo-login-brand__title")
                            ui.label("Content Studio").classes("geo-login-brand__tag")

                    with ui.element("div").classes("geo-login-header"):
                        ui.label("Olá!").classes("geo-login-header__title")
                        ui.label("Entre na sua conta").classes("geo-login-header__subtitle")

                    with ui.element("div").classes("geo-login-fields"):
                        with ui.element("div").classes("geo-login-neu-field"):
                            with ui.element("div").classes("geo-login-neu-field__icon"):
                                ui.icon("mail", size="sm")
                            email = (
                                ui.input(placeholder="E-mail")
                                .classes("w-full")
                                .props("borderless dense type=email autofocus")
                            )

                        with ui.element("div").classes("geo-login-neu-field"):
                            with ui.element("div").classes("geo-login-neu-field__icon"):
                                ui.icon("lock", size="sm")
                            password = (
                                ui.input(
                                    placeholder="Senha",
                                    password=True,
                                    password_toggle_button=True,
                                )
                                .classes("w-full")
                                .props("borderless dense")
                            )

                    with ui.element("div").classes("geo-login-options"):
                        ui.checkbox("Lembrar-me").props("dense size=xs color=primary")
                        ui.link("Esqueceu a senha?", "#").classes("text-xs")

                    with ui.element("div").classes("geo-login-submit-row"):
                        submit_btn = ui.button("Entrar").classes("geo-login-submit-btn")

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

                    with ui.row().classes("geo-login-footer items-center justify-center gap-1"):
                        ui.label("Não tem conta?").classes("text-xs text-grey-7")
                        if on_signup:
                            ui.button("Criar conta", on_click=on_signup).props(
                                "flat no-caps dense color=primary"
                            ).classes("geo-signup-login-link")
                        else:
                            ui.label("Em breve").classes("text-xs text-grey-6")

                with ui.element("section").classes("geo-login-welcome"):
                    ui.label("Bem-vindo de volta!").classes("geo-login-welcome__title")
                    ui.label(
                        "Aceda ao GEO Extractor Content Studio para gerar matérias, "
                        "processar URLs e publicar no seu blog local."
                    ).classes("geo-login-welcome__text")
