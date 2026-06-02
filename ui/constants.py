"""Constantes e rótulos partilhados da UI Content Studio."""

from __future__ import annotations

from services.blog.brief import LONG_FORM_THRESHOLD

# --- Provedores de IA ---

PROVIDER_LABELS: dict[str, str] = {
    "openai": "OpenAI",
    "anthropic": "Anthropic",
    "openrouter": "OpenRouter",
    "ollama": "Ollama",
    "lmstudio": "LM Studio",
}

PROVIDER_SETTINGS_LABELS: dict[str, str] = {
    "openai": "OpenAI GPT-4o",
    "anthropic": "Anthropic Claude",
    "openrouter": "OpenRouter",
    "ollama": "Ollama (local)",
    "lmstudio": "LM Studio (local)",
}

PROVIDER_DESCRIPTIONS: dict[str, str] = {
    "openai": "Melhor para raciocínio complexo e formatação.",
    "anthropic": "Excelente para documentos longos.",
    "openrouter": "Acesso a vários modelos com uma chave.",
    "ollama": "Processamento privado via Ollama.",
    "lmstudio": "Servidor local via LM Studio.",
}

PROVIDER_ICONS: dict[str, str] = {
    "openai": "smart_toy",
    "anthropic": "psychology",
    "openrouter": "hub",
    "ollama": "bolt",
    "lmstudio": "memory",
}

PROVIDER_ORDER: tuple[str, ...] = (
    "openai",
    "anthropic",
    "openrouter",
    "ollama",
    "lmstudio",
)

# --- Estado de matérias ---

# (rótulo, classe dashboard, ícone Material)
ARTICLE_STATUS_PILL: dict[str, tuple[str, str, str]] = {
    "completed": ("Concluída", "geo-dash-status-pill--completed", "check_circle"),
    "draft": ("Em rascunho", "geo-dash-status-pill--processing", "sync"),
    "archived": ("Arquivada", "geo-dash-status-pill--paused", "pause_circle"),
}

ARTICLE_STATUS_HISTORY_CSS: dict[str, str] = {
    "completed": "geo-status-pill geo-status-pill--ok",
    "draft": "geo-status-pill geo-status-pill--warn",
    "archived": "geo-status-pill geo-status-pill--off",
}

# --- Blog (aba Criar matéria) ---

BLOG_TONE_OPTIONS: dict[str, str] = {
    "Profissional e técnico": "técnico",
    "Descontraído e amigável": "conversacional",
    "Informativo": "informativo",
    "Jornalístico": "jornalístico",
}

BLOG_WORD_COUNT_OPTIONS: dict[str, int] = {
    "Curto (~1 500 palavras)": 1500,
    "Médio (~2 000 palavras)": 2000,
    "Longo (~2 500 palavras)": 2500,
    "Artigo longo (~4 000 palavras)": 4000,
    "Deep dive (~6 000 palavras)": 6000,
}

BLOG_WORD_COUNT_DEFAULT = 2500

# --- API (dashboard) ---

API_ROUTES: tuple[tuple[str, str, str], ...] = (
    ("GET", "/api/health", "Público"),
    ("GET", "/api/v1/stats", "Métricas"),
    ("GET", "/api/v1/articles", "Listar"),
    ("GET", "/api/v1/articles/{id}", "Detalhe"),
    ("POST", "/api/v1/articles/generate", "Gerar"),
    ("POST", "/api/v1/articles/publish", "CMS externo"),
    ("DELETE", "/api/v1/articles/{id}", "Excluir"),
)

# --- Classes CSS reutilizáveis ---

ALERT_BASE = "geo-alert"
ALERT_SUCCESS = f"{ALERT_BASE} {ALERT_BASE}--success"
ALERT_WARNING = f"{ALERT_BASE} {ALERT_BASE}--warning"
ALERT_ERROR = f"{ALERT_BASE} {ALERT_BASE}--error"


def provider_label(name: str) -> str:
    """Nome legível do provedor de IA."""
    if not name or name in ("IA", "local"):
        return name or "—"
    return PROVIDER_LABELS.get(name, name)


def provider_select_options(ready_providers: list[str]) -> list[str]:
    """Opções do select de provedor na sidebar e no blog."""
    return ["auto"] + ready_providers if ready_providers else ["auto"]


def article_status_label(status: str) -> str:
    """Rótulo legível do estado da matéria."""
    if status in ARTICLE_STATUS_PILL:
        return ARTICLE_STATUS_PILL[status][0]
    return "Em progresso"


def article_status_meta(status: str) -> tuple[str, str, str]:
    """Texto, classe e ícone para o estado no dashboard."""
    return ARTICLE_STATUS_PILL.get(
        status,
        ("Em progresso", "geo-dash-status-pill--processing", "sync"),
    )


def history_status_pill_html(status: str) -> str:
    """HTML do pill de estado na aba Histórico."""
    label = article_status_label(status)
    css = ARTICLE_STATUS_HISTORY_CSS.get(status, "geo-status-pill geo-status-pill--warn")
    return f'<span class="{css}">{label}</span>'


def blog_tone_value(ui_label: str | None) -> str:
    """Valor de tom enviado ao pipeline a partir do rótulo da UI."""
    if not ui_label:
        return "informativo"
    return BLOG_TONE_OPTIONS.get(ui_label, "informativo")


def blog_word_count(ui_label: str | None, *, default: int = BLOG_WORD_COUNT_DEFAULT) -> int:
    """Palavras-alvo a partir do rótulo do select."""
    if not ui_label:
        return default
    return BLOG_WORD_COUNT_OPTIONS.get(ui_label, default)


def blog_complexity_for_words(word_count: int) -> tuple[str, int, str]:
    """Rótulo de complexidade, percentagem da barra e tempo estimado."""
    if word_count >= 4000:
        return "Avançada", 90, "~90 s"
    if word_count >= LONG_FORM_THRESHOLD:
        return "Intermediária", 66, "~60 s"
    if word_count >= 2000:
        return "Intermediária", 50, "~45 s"
    return "Básica", 33, "~30 s"
