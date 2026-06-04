"""Validação editorial de matérias (extensão, H1, FAQ, URLs)."""

from __future__ import annotations

import re
from dataclasses import dataclass

from services.url_cache import count_cached_urls, is_cache_enabled
from services.url_security import URLValidationError, validate_reference_urls

# Alinhado com services.blog.brief.LONG_FORM_THRESHOLD
LONG_FORM_THRESHOLD = 2600
from services.word_count import WORD_COUNT_WARNING_RATIO, is_below_word_count_target

_CERT_IN_H1 = re.compile(
    r"\b(ISO\s*\d+|OMS|ANVISA|FDA|CE\b|certificad[oa])\b",
    re.I,
)

PRIMARY_CHECK_IDS: tuple[str, ...] = (
    "h1_editorial",
    "faq",
    "word_count",
    "originality",
)


@dataclass
class ValidationItem:
    """Um critério de validação (automático ou pré-voo)."""

    item_id: str
    label: str
    passed: bool
    hint: str = ""
    detail: str = ""
    blocking: bool = False


def count_words(text: str) -> int:
    return len((text or "").split())


def validate_article_markdown(
    markdown: str,
    *,
    target_words: int | None = None,
    include_faq: bool = True,
    meta_description: str = "",
    faq_items: list | None = None,
    similarity_warning: str | None = None,
    fallback_reason: str | None = None,
) -> list[ValidationItem]:
    """Checklist automática sobre o Markdown gerado."""
    md = markdown or ""
    items: list[ValidationItem] = []
    actual = count_words(md)

    if target_words and target_words > 0:
        ratio = actual / target_words
        ratio_ok = not is_below_word_count_target(actual, target_words)
        items.append(
            ValidationItem(
                item_id="word_count",
                label="Tamanho do texto",
                passed=ratio_ok,
                hint="Abaixo de 85% da meta — expanda secções ou regenere com IA.",
                detail=(
                    f"{actual:,} / {target_words:,} palavras "
                    f"({int(ratio * 100)}% da meta)"
                ),
            )
        )
    else:
        items.append(
            ValidationItem(
                item_id="word_count",
                label="Extensão do artigo",
                passed=actual >= 200,
                hint="Texto muito curto — expanda ou regenere com IA.",
                detail=f"{actual:,} palavras (sem meta definida neste fluxo)",
            )
        )

    has_faq_section = bool(
        re.search(r"^##\s+.*perguntas?\s+frequentes", md, re.I | re.M) or faq_items
    )
    if include_faq:
        faq_count = len(faq_items) if faq_items else 0
        items.append(
            ValidationItem(
                item_id="faq",
                label="Secção FAQ",
                passed=has_faq_section,
                hint="Inclua «## Perguntas frequentes» com 5–8 perguntas e respostas.",
                detail=(
                    f"{faq_count} itens no metadado"
                    if faq_count
                    else "Não detetada no Markdown"
                ),
            )
        )

    h1_match = re.search(r"^#\s+(.+)$", md, re.M)
    h1_text = h1_match.group(1).strip() if h1_match else ""
    h1_ok = bool(h1_text) and not _CERT_IN_H1.search(h1_text)
    items.append(
        ValidationItem(
            item_id="h1_editorial",
            label="H1 editorial",
            passed=h1_ok,
            hint="Título sem siglas (ISO, OMS…) — use blocos de confiança em H3.",
            detail=(
                (h1_text[:80] + "...") if len(h1_text) > 80 else h1_text
            )
            if h1_text
            else "H1 em falta",
        )
    )

    desc = meta_description or ""
    items.append(
        ValidationItem(
            item_id="meta_description",
            label="Meta description (50–160 caracteres)",
            passed=50 <= len(desc) <= 160,
            detail=f"{len(desc)} caracteres" if desc else "Não definida",
        )
    )

    items.append(
        ValidationItem(
            item_id="h2_structure",
            label="Secções H2",
            passed=bool(re.search(r"^##\s+", md, re.M)),
            detail="Estrutura citável por IAs",
        )
    )

    items.append(
        ValidationItem(
            item_id="originality",
            label="Originalidade vs. fontes",
            passed=not similarity_warning,
            hint=similarity_warning or "Nenhuma proximidade excessiva detectada.",
            detail="Revise se usou URLs de referência",
        )
    )

    if fallback_reason:
        items.append(
            ValidationItem(
                item_id="llm_mode",
                label="Geração com IA",
                passed=False,
                hint=fallback_reason,
            )
        )

    return items


def primary_checks(
    items: list[ValidationItem],
    *,
    include_faq: bool = True,
) -> list[ValidationItem]:
    out: list[ValidationItem] = []
    for item_id in PRIMARY_CHECK_IDS:
        if item_id == "faq" and not include_faq:
            continue
        for item in items:
            if item.item_id == item_id:
                out.append(item)
                break
    return out


def secondary_checks(
    items: list[ValidationItem],
    *,
    include_faq: bool = True,
) -> list[ValidationItem]:
    primary_ids = set(PRIMARY_CHECK_IDS)
    if not include_faq:
        primary_ids.discard("faq")
    return [i for i in items if i.item_id not in primary_ids]


def evaluate_brief_preflight(
    *,
    topic: str,
    keywords: list[str],
    reference_urls: list[str],
    word_count: int,
    use_llm: bool,
) -> list[ValidationItem]:
    """Validação do formulário antes de gerar (aba Criar matéria)."""
    items: list[ValidationItem] = []

    topic_ok = bool((topic or "").strip())
    items.append(
        ValidationItem(
            item_id="topic",
            label="Tema principal",
            passed=topic_ok,
            hint="Informe o tema para orientar a geração.",
            blocking=True,
        )
    )

    kw_count = len(keywords)
    items.append(
        ValidationItem(
            item_id="keywords",
            label="Palavras-chave",
            passed=kw_count >= 2,
            hint="Recomendado: pelo menos 2 keywords para SEO e GEO.",
            detail=f"{kw_count} keyword(s)" if kw_count else "Nenhuma",
        )
    )

    raw_urls = [u.strip() for u in reference_urls if (u or "").strip()]
    if not raw_urls:
        items.append(
            ValidationItem(
                item_id="reference_urls",
                label="URLs de referência",
                passed=True,
                detail="Opcional — sem links",
            )
        )
    else:
        try:
            valid, errors = validate_reference_urls(raw_urls, resolve_dns=False)
            url_ok = len(errors) == 0 and len(valid) > 0
            detail = f"{len(valid)} URL(s) válida(s)"
            if errors:
                detail = errors[0][:100]
            items.append(
                ValidationItem(
                    item_id="reference_urls",
                    label="URLs de referência",
                    passed=url_ok,
                    hint="Corrija links inválidos ou bloqueados antes de gerar.",
                    detail=detail,
                    blocking=bool(errors),
                )
            )
            if url_ok and valid and is_cache_enabled():
                cached_n = count_cached_urls(valid)
                items.append(
                    ValidationItem(
                        item_id="reference_cache",
                        label="Cache de referências",
                        passed=True,
                        detail=(
                            f"{cached_n} de {len(valid)} URL(s) já em cache "
                            "(busca mais rápida)"
                            if cached_n
                            else (
                                f"{len(valid)} URL(s) — primeira busca "
                                "(ainda sem cache)"
                            )
                        ),
                    )
                )
        except URLValidationError as exc:
            items.append(
                ValidationItem(
                    item_id="reference_urls",
                    label="URLs de referência",
                    passed=False,
                    hint=str(exc),
                    blocking=True,
                )
            )

    if word_count >= LONG_FORM_THRESHOLD:
        items.append(
            ValidationItem(
                item_id="long_form_llm",
                label="Artigo longo (2.600+ palavras)",
                passed=use_llm,
                hint="Ative «Gerar artigo com IA» na sidebar para este tamanho.",
                detail=f"Meta: {word_count:,} palavras",
            )
        )

    return items


def has_blocking_issues(items: list[ValidationItem]) -> bool:
    return any(i.blocking and not i.passed for i in items)
