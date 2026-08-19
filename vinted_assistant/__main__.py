"""Permet d'exécuter le paquet avec `python -m vinted_assistant`."""

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
