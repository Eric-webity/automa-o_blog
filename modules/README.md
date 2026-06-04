# `modules/` — compatibilidade legada

Esta pasta **não recebe lógica nova**. Cada ficheiro reexporta símbolos de `core/` ou `services/`.

## Código novo

```python
# Correto
from services.blog import BlogBrief, parse_keywords
from core.geo_engine import generate_geo_skeleton

# Evitar
from modules.blog_brief import parse_keywords
```

Única excepção: `legacy/app.py` (Streamlit) pode manter imports antigos até ser removido.

## Remoção futura

Quando `legacy/app.py` deixar de ser suportado, esta pasta pode ser apagada após confirmar que nenhum consumidor externo importa `modules.*`.
