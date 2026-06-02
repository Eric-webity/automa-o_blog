# Interface legada (Streamlit)

Esta pasta guarda a **primeira interface** do GEO Extractor. Não recebe novas funcionalidades.

## Uso

Na **raiz do projeto**, com o ambiente virtual ativo:

```powershell
python -m streamlit run legacy/app.py
```

Artefatos continuam a ser gravados em `output/` na raiz. O ficheiro `.env` também é lido da raiz.

## Interface atual

```powershell
python main.py
```

Content Studio (NiceGUI): login, histórico, dashboard, API no mesmo processo.
