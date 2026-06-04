"""Lote: planilha CSV → vários ficheiros Markdown em ``output/``."""

from __future__ import annotations

import csv
import io
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from config.paths import OUTPUT_DIR
from core.faq_jsonld import build_faq_jsonld, collect_faq_items, serialize_faq_jsonld
from core.geo_niches import normalize_niche_id
from db.models import ArticleStatus
from db.repository import ArticleRepository
from services.ai_manager import AIManager
from services.blog import BlogBrief, generate_blog_post, parse_keywords
from services.blog.local_writer import slugify

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[int, int, str], None]

# Cabeçalhos aceites (normalizados: minúsculas, underscores).
COLUMN_ALIASES: dict[str, tuple[str, ...]] = {
    "tema": ("tema", "topic", "topico", "titulo", "title", "assunto", "subject"),
    "urls": (
        "urls",
        "url",
        "url_referencia",
        "url_referencias",
        "reference_urls",
        "links",
        "referencias",
    ),
    "palavras_chave": ("palavras_chave", "keywords", "keyword", "palavras", "tags"),
    "publico": ("publico", "público", "audience", "audiencia", "leitores"),
    "tom": ("tom", "tone", "estilo"),
    "palavras": ("palavras", "word_count", "extensao", "extensão", "words", "wc"),
    "marca": ("marca", "brand", "brand_name", "empresa"),
    "cta": ("cta", "call_to_action", "chamada"),
    "faq": ("faq", "include_faq", "incluir_faq"),
    "angulo": ("angulo", "ângulo", "angle", "enfoque"),
    "nicho": ("nicho", "geo_niche", "area", "modelo_geo", "vertical"),
    "slug": ("slug", "arquivo", "filename", "ficheiro"),
}

CSV_TEMPLATE = """tema,urls,palavras_chave,publico,tom,palavras,marca,cta,faq,angulo,nicho,slug
"Energia solar residencial","https://exemplo.com/guia-1|https://exemplo.com/guia-2","energia solar; painéis fotovoltaicos","Proprietários de imóveis","informativo e acessível",2500,"Marca Exemplo","Solicite orçamento",sim,"Guia prático para decisão",generic,energia-solar-residencial
"Investimentos conservadores","","renda fixa; CDB; Tesouro","Investidores iniciantes","técnico",2000,"","","sim","","finance",
"""


@dataclass(frozen=True)
class BatchDefaults:
    """Valores por omissão quando a coluna CSV está vazia."""

    audience: str = "Leitores interessados no tema"
    tone: str = "informativo e acessível"
    word_count: int = 2500
    include_faq: bool = True
    geo_niche: str = "generic"
    use_advanced: bool = True
    use_llm: bool = True


@dataclass
class BatchRowSpec:
    """Uma linha válida do CSV pronta para geração."""

    row_num: int
    topic: str
    brief: BlogBrief
    file_slug: str


@dataclass
class BatchRowResult:
    """Resultado da geração de uma linha."""

    row_num: int
    topic: str
    file_slug: str
    success: bool
    md_path: str | None = None
    meta_path: str | None = None
    faq_jsonld_path: str | None = None
    error: str | None = None
    word_count: int | None = None
    generation_mode: str | None = None


@dataclass
class BatchRunResult:
    """Resumo de uma execução de lote."""

    output_dir: str
    total: int
    succeeded: int
    failed: int
    rows: list[BatchRowResult] = field(default_factory=list)
    manifest_path: str = ""

    @property
    def ok(self) -> bool:
        return self.failed == 0 and self.succeeded > 0


def normalize_header(name: str) -> str:
    key = (name or "").strip().lower()
    key = key.replace("ã", "a").replace("õ", "o").replace("ç", "c")
    key = key.replace("á", "a").replace("é", "e").replace("í", "i")
    key = key.replace("ó", "o").replace("ú", "u").replace("â", "a").replace("ê", "e")
    key = re.sub(r"[^\w]+", "_", key).strip("_")
    return key


def map_headers(fieldnames: list[str] | None) -> dict[str, str]:
    """Mapeia cabeçalhos do CSV para chaves canónicas."""
    mapping: dict[str, str] = {}
    if not fieldnames:
        return mapping
    for raw in fieldnames:
        norm = normalize_header(raw)
        for canonical, aliases in COLUMN_ALIASES.items():
            if norm in aliases and canonical not in mapping:
                mapping[canonical] = raw
                break
    return mapping


def _detect_dialect(sample: str) -> csv.Dialect:
    try:
        return csv.Sniffer().sniff(sample[:4096], delimiters=",;\t")
    except csv.Error:
        return csv.excel


def _parse_bool(value: str | None, default: bool) -> bool:
    if value is None or not str(value).strip():
        return default
    v = str(value).strip().lower()
    if v in ("1", "true", "yes", "sim", "s", "y", "on"):
        return True
    if v in ("0", "false", "no", "nao", "não", "n", "off"):
        return False
    return default


def _parse_int(value: str | None, default: int) -> int:
    if value is None or not str(value).strip():
        return default
    digits = re.sub(r"[^\d]", "", str(value))
    if not digits:
        return default
    try:
        n = int(digits)
        return max(500, min(6000, n))
    except ValueError:
        return default


def _split_urls(value: str | None) -> list[str]:
    from services.url_security import URLValidationError, validate_url

    if not value or not str(value).strip():
        return []
    parts = re.split(r"[|\n;]+", str(value))
    out: list[str] = []
    for part in parts:
        raw = part.strip()
        if not raw:
            continue
        try:
            out.append(validate_url(raw))
        except URLValidationError:
            continue
    return out


def _cell(row: dict[str, str], header_map: dict[str, str], key: str) -> str:
    col = header_map.get(key)
    if not col:
        return ""
    return (row.get(col) or "").strip()


def parse_csv_text(
    text: str,
    *,
    defaults: BatchDefaults | None = None,
) -> tuple[list[BatchRowSpec], list[str]]:
    """
    Interpreta CSV (UTF-8) e devolve linhas válidas + avisos.

    Raises:
        ValueError: se faltar coluna ``tema`` ou não houver linhas válidas.
    """
    defaults = defaults or BatchDefaults()
    raw = (text or "").strip()
    if not raw:
        raise ValueError("O ficheiro CSV está vazio.")

    if raw.startswith("\ufeff"):
        raw = raw.lstrip("\ufeff")

    dialect = _detect_dialect(raw)
    reader = csv.DictReader(io.StringIO(raw), dialect=dialect)
    header_map = map_headers(reader.fieldnames)
    if "tema" not in header_map:
        raise ValueError(
            "Coluna obrigatória «tema» (ou topic/título) não encontrada no CSV."
        )

    specs: list[BatchRowSpec] = []
    warnings: list[str] = []
    used_slugs: set[str] = set()

    for line_no, row in enumerate(reader, start=2):
        topic = _cell(row, header_map, "tema")
        if not topic:
            warnings.append(f"Linha {line_no}: tema vazio — ignorada.")
            continue

        urls = _split_urls(_cell(row, header_map, "urls"))
        kw_raw = _cell(row, header_map, "palavras_chave")
        audience = _cell(row, header_map, "publico") or defaults.audience
        tone = _cell(row, header_map, "tom") or defaults.tone
        word_count = _parse_int(_cell(row, header_map, "palavras"), defaults.word_count)
        brand = _cell(row, header_map, "marca")
        cta = _cell(row, header_map, "cta")
        include_faq = _parse_bool(_cell(row, header_map, "faq"), defaults.include_faq)
        angle = _cell(row, header_map, "angulo")
        niche_raw = _cell(row, header_map, "nicho") or defaults.geo_niche
        geo_niche = normalize_niche_id(niche_raw)

        slug_cell = _cell(row, header_map, "slug")
        base_slug = slugify(slug_cell or topic)
        file_slug = base_slug
        suffix = 1
        while file_slug in used_slugs:
            suffix += 1
            file_slug = f"{base_slug}-{suffix}"
        used_slugs.add(file_slug)

        brief = BlogBrief(
            topic=topic,
            reference_urls=urls,
            target_keywords=parse_keywords(kw_raw),
            audience=audience,
            tone=tone,
            word_count=word_count,
            brand_name=brand,
            cta=cta,
            include_faq=include_faq,
            angle=angle,
            geo_niche=geo_niche,
        )
        specs.append(
            BatchRowSpec(row_num=line_no, topic=topic, brief=brief, file_slug=file_slug)
        )

    if not specs:
        raise ValueError("Nenhuma linha válida com tema preenchido.")
    return specs, warnings


def parse_csv_file(
    path: str | Path,
    *,
    defaults: BatchDefaults | None = None,
) -> tuple[list[BatchRowSpec], list[str]]:
    """Lê CSV do disco."""
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"CSV não encontrado: {p}")
    text = p.read_text(encoding="utf-8-sig")
    return parse_csv_text(text, defaults=defaults)


def _write_row_artifacts(
    out_dir: Path,
    spec: BatchRowSpec,
    package,
) -> tuple[str, str | None, str | None]:
    prefix = f"{spec.row_num:03d}_{spec.file_slug}"
    md_path = out_dir / f"{prefix}.md"
    md_path.write_text(package.markdown, encoding="utf-8")

    meta_payload = {
        "row_num": spec.row_num,
        "topic": spec.topic,
        "slug": spec.file_slug,
        "meta_title": package.meta_title,
        "meta_description": package.meta_description,
        "keywords": package.keywords_used,
        "faq": package.faq_items,
        "word_count_target": package.word_count_target,
        "word_count_actual": package.word_count_actual,
        "generation_mode": package.generation_mode,
        "geo_niche": spec.brief.geo_niche,
    }
    meta_path = out_dir / f"{prefix}_meta.json"
    meta_path.write_text(
        json.dumps(meta_payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    faq_path: str | None = None
    faq_items = collect_faq_items(package.faq_items, package.markdown)
    if faq_items:
        jsonld = build_faq_jsonld(
            faq_items,
            page_url=f"https://example.com/{spec.file_slug}",
            page_name=package.meta_title,
        )
        faq_file = out_dir / f"{prefix}_faq.jsonld.json"
        faq_file.write_text(serialize_faq_jsonld(jsonld), encoding="utf-8")
        faq_path = str(faq_file)
        meta_payload["faq_jsonld"] = jsonld
        meta_path.write_text(
            json.dumps(meta_payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    return str(md_path), str(meta_path), faq_path


def _persist_batch_row_history(
    *,
    user_id: int,
    spec: BatchRowSpec,
    package,
    meta_payload: dict,
) -> None:
    repo = ArticleRepository(user_id=user_id)
    repo.create(
        title=(package.meta_title or spec.topic).strip() or spec.topic,
        markdown_content=package.markdown,
        json_index=meta_payload,
        status=ArticleStatus.DRAFT.value,
        user_id=user_id,
    )


def run_batch(
    specs: list[BatchRowSpec],
    *,
    use_advanced: bool = True,
    use_llm: bool = True,
    provider: str | None = None,
    manager: AIManager | None = None,
    output_dir: Path | str | None = None,
    on_progress: ProgressCallback | None = None,
    user_id: int | None = None,
    save_to_history: bool = False,
) -> BatchRunResult:
    """Gera um ``.md`` (e metadados) por linha do CSV."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = Path(output_dir) if output_dir else OUTPUT_DIR / f"batch_{ts}"
    out_dir.mkdir(parents=True, exist_ok=True)

    total = len(specs)
    results: list[BatchRowResult] = []
    mgr = manager if use_llm else None

    for index, spec in enumerate(specs, start=1):
        if on_progress:
            on_progress(index, total, spec.topic)
        try:
            package = generate_blog_post(
                spec.brief,
                use_advanced=use_advanced,
                use_llm=use_llm,
                provider=provider,
                manager=mgr,
            )
            md_path, meta_path, faq_path = _write_row_artifacts(out_dir, spec, package)
            if save_to_history and user_id is not None:
                meta_payload = json.loads(Path(meta_path).read_text(encoding="utf-8"))
                _persist_batch_row_history(
                    user_id=user_id,
                    spec=spec,
                    package=package,
                    meta_payload=meta_payload,
                )
            results.append(
                BatchRowResult(
                    row_num=spec.row_num,
                    topic=spec.topic,
                    file_slug=spec.file_slug,
                    success=True,
                    md_path=md_path,
                    meta_path=meta_path,
                    faq_jsonld_path=faq_path,
                    word_count=package.word_count_actual,
                    generation_mode=package.generation_mode,
                )
            )
        except Exception as exc:
            logger.exception("Lote linha %s falhou: %s", spec.row_num, exc)
            results.append(
                BatchRowResult(
                    row_num=spec.row_num,
                    topic=spec.topic,
                    file_slug=spec.file_slug,
                    success=False,
                    error=str(exc),
                )
            )

    succeeded = sum(1 for r in results if r.success)
    failed = total - succeeded
    manifest = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "output_dir": str(out_dir),
        "total": total,
        "succeeded": succeeded,
        "failed": failed,
        "use_llm": use_llm,
        "provider": provider,
        "rows": [
            {
                "row_num": r.row_num,
                "topic": r.topic,
                "file_slug": r.file_slug,
                "success": r.success,
                "md_path": r.md_path,
                "meta_path": r.meta_path,
                "faq_jsonld_path": r.faq_jsonld_path,
                "error": r.error,
                "word_count": r.word_count,
                "generation_mode": r.generation_mode,
            }
            for r in results
        ],
    }
    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return BatchRunResult(
        output_dir=str(out_dir),
        total=total,
        succeeded=succeeded,
        failed=failed,
        rows=results,
        manifest_path=str(manifest_path),
    )
