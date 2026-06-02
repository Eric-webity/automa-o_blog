"""
A interface principal mudou para NiceGUI (main.py).

A app Streamlit legada está em legacy/app.py:

    python -m streamlit run legacy/app.py
"""

from __future__ import annotations

import sys


def main() -> None:
    print(__doc__.strip())
    print()
    print("Para abrir o Content Studio:")
    print("  python main.py")
    sys.exit(0)


if __name__ == "__main__":
    main()
