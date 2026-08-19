"""Lancement de Chrome avec le débogage distant activé et un profil dédié.

Un profil Chrome dédié est utilisé (dans le répertoire de l'assistant) pour deux
raisons :
- Depuis Chrome 136, le débogage distant est refusé sur le profil par défaut
  pour des raisons de sécurité : il faut un `--user-data-dir` explicite distinct.
- Vous vous connectez à Vinted une seule fois dans ce profil ; la session y
  persiste ensuite d'un lancement à l'autre. L'assistant ne voit jamais vos
  identifiants.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional

# Emplacements usuels de l'exécutable Chrome selon le système.
_MAC_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
]
_WINDOWS_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]
_LINUX_COMMANDS = [
    "google-chrome",
    "google-chrome-stable",
    "chromium",
    "chromium-browser",
]


class LauncherError(RuntimeError):
    """Erreur lors du lancement du navigateur."""


def find_chrome() -> Optional[str]:
    """Localise l'exécutable Chrome/Chromium, ou None si introuvable."""
    system = platform.system()
    if system == "Darwin":
        for path in _MAC_CANDIDATES:
            if Path(path).exists():
                return path
    elif system == "Windows":
        local = os.environ.get("LOCALAPPDATA", "")
        candidates = list(_WINDOWS_CANDIDATES)
        if local:
            candidates.append(
                str(Path(local) / "Google/Chrome/Application/chrome.exe")
            )
        for path in candidates:
            if Path(path).exists():
                return path
    # Linux (et repli général).
    for command in _LINUX_COMMANDS:
        found = shutil.which(command)
        if found:
            return found
    return None


def build_launch_args(
    profile_dir: Path,
    debug_port: int,
    start_url: Optional[str] = None,
) -> List[str]:
    """Construit la liste d'arguments de lancement de Chrome."""
    args = [
        f"--remote-debugging-port={debug_port}",
        f"--user-data-dir={profile_dir}",
        "--no-first-run",
        "--no-default-browser-check",
    ]
    if start_url:
        args.append(start_url)
    return args


def launch_chrome(
    profile_dir: Path,
    debug_port: int,
    start_url: Optional[str] = None,
    chrome_path: Optional[str] = None,
) -> subprocess.Popen:
    """Lance Chrome avec le débogage distant et un profil dédié.

    Returns:
        Le processus Chrome lancé.
    """
    executable = chrome_path or find_chrome()
    if not executable:
        raise LauncherError(
            "Chrome/Chromium introuvable. Installez Google Chrome, ou indiquez "
            "le chemin de l'exécutable via --chrome-path."
        )

    profile_dir.mkdir(parents=True, exist_ok=True)
    args = build_launch_args(profile_dir, debug_port, start_url)

    try:
        return subprocess.Popen([executable, *args])
    except Exception as exc:  # pragma: no cover - dépend de l'OS
        raise LauncherError(f"Échec du lancement de Chrome : {exc}") from exc
