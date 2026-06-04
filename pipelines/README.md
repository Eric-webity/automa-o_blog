# `pipelines/` — atalhos para `services/`

Reexportações para código ou scripts antigos. O fluxo real está em:

| Atalho | Implementação |
|--------|----------------|
| `pipelines.blog_pipeline` | `services/blog_pipeline.py` |
| `pipelines` (`run_url_pipeline`) | `services/url_pipeline.py` |
| `pipelines.storage` | `services/storage.py` |

Não duplique funções aqui — edite sempre `services/`.
