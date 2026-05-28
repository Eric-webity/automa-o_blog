# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec — GEO Extractor (Windows, pasta dist/GEO-Extractor/)

from pathlib import Path

block_cipher = None
root = Path(SPEC).resolve().parent

datas = [
    (str(root / "config"), "config"),
    (str(root / "ui" / "style.css"), "ui"),
    (str(root / "skills"), "skills"),
    (str(root / ".env.example"), "."),
]

hiddenimports = [
    "nicegui",
    "nicegui.elements",
    "uvicorn",
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "fastapi",
    "starlette",
    "sqlalchemy",
    "sqlalchemy.sql.default_comparator",
    "httpx",
    "dotenv",
    "yaml",
    "engineio.async_drivers.threading",
    "openai",
    "anthropic",
    "bs4",
    "requests",
]

# Evita empacotar dependências pesadas puxadas pelo venv (streamlit, torch, etc.)
EXCLUDES = [
    "streamlit",
    "matplotlib",
    "tkinter",
    "torch",
    "torchvision",
    "tensorflow",
    "pandas",
    "scipy",
    "sklearn",
    "pytest",
    "_pytest",
    "pyarrow",
    "altair",
    "IPython",
    "jupyter",
    "notebook",
    "transformers",
    "sentence_transformers",
    "spacy",
    "keybert",
    "sumy",
]

a = Analysis(
    ["main.py"],
    pathex=[str(root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=EXCLUDES,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="GEO-Extractor",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="GEO-Extractor",
)
