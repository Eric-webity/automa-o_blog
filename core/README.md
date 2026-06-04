# `core/` — motor GEO (sem efeitos externos)

Lógica pura: esqueleto, índice IA, extração de insights, FAQ JSON-LD, nichos, agentes.

- **Sem** chamadas HTTP, SQLite ou NiceGUI.
- **Sem** importar `services/`.

Consumidores típicos: `services/blog/`, `services/url_pipeline.py`, testes em `tests/test_geo_*.py`.
