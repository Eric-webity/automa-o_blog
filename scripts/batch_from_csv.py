#!/usr/bin/env python3
"""CLI: planilha CSV → vários .md em output/ (lote para produção)."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from services.batch_csv import BatchDefaults, parse_csv_file, run_batch  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("batch_csv")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Gera matérias GEO em lote a partir de um CSV.",
    )
    parser.add_argument("csv", type=Path, help="Caminho do ficheiro CSV")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Pasta de saída (por omissão: output/batch_AAAAMMDD_HHMMSS)",
    )
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="Geração local sem IA (mais rápido, rascunhos)",
    )
    parser.add_argument(
        "--provider",
        default=None,
        help="Provedor de IA (openai, anthropic, …)",
    )
    parser.add_argument(
        "--word-count",
        type=int,
        default=2500,
        help="Palavras por omissão se a coluna «palavras» estiver vazia",
    )
    parser.add_argument(
        "--niche",
        default="generic",
        help="Nicho GEO por omissão (generic, health, finance, saas)",
    )
    args = parser.parse_args()

    defaults = BatchDefaults(
        word_count=args.word_count,
        geo_niche=args.niche,
        use_llm=not args.no_llm,
    )

    try:
        specs, warnings = parse_csv_file(args.csv, defaults=defaults)
    except (ValueError, FileNotFoundError) as exc:
        logger.error("%s", exc)
        return 1

    for w in warnings:
        logger.warning("%s", w)

    logger.info("%d linha(s) a processar…", len(specs))

    def on_progress(current: int, total: int, topic: str) -> None:
        logger.info("[%d/%d] %s", current, total, topic[:80])

    result = run_batch(
        specs,
        use_llm=defaults.use_llm,
        provider=args.provider,
        output_dir=args.output_dir,
        on_progress=on_progress,
    )

    logger.info(
        "Concluído: %d ok, %d falha(s). Pasta: %s",
        result.succeeded,
        result.failed,
        result.output_dir,
    )
    logger.info("Manifesto: %s", result.manifest_path)
    return 0 if result.ok or result.succeeded > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
