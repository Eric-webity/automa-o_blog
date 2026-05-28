"""Prompts e carregamento de skills para geração de blog."""

from __future__ import annotations

from pathlib import Path

SKILLS_DIR = Path(__file__).resolve().parent.parent.parent / "skills"

BLOG_SYSTEM = """Você é redator sênior de blog e especialista em SEO + GEO (Generative Engine Optimization).
Crie matérias ORIGINAIS em português (Brasil) para publicação em blog.

Siga rigorosamente as skills anexadas (seo-geo, seo-audit, blog-post).

Regras críticas:
- Matéria 100% original; não plagiAR frases das fontes.
- Answer-first no lead e em cada secção H2.
- H1 editorial humano (sem siglas técnicas no título).
- Incluir secção FAQ se solicitado.
- Terminar com "## Fontes consultadas" listando URLs usadas (ou "Pesquisa editorial" se sem URLs).
- Ao final, após o markdown, inclua um bloco JSON entre linhas ---META--- e ---END--- com:
  {"meta_title":"...","meta_description":"...","slug":"...","keywords":["..."],"faq":[{"question":"...","answer":"..."}]}
"""


def load_skills() -> str:
    parts = []
    for name in ("seo_geo.md", "seo_audit.md", "blog_post.md"):
        path = SKILLS_DIR / name
        if path.exists():
            parts.append(path.read_text(encoding="utf-8"))
    return "\n\n".join(parts)


def build_system_prompt() -> str:
    return f"{BLOG_SYSTEM}\n\n# Skills\n{load_skills()}"
