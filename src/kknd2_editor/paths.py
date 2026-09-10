"""Portable checkout paths; no installation paths or personal settings in source."""
import os
import sys
from pathlib import Path

def application_root():
    """Keep personal settings beside the EXE, never in its extraction folder."""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


PROJECT_ROOT = application_root()


def find_game_dir(config_folder=None):
    """Prefer the selected game's folder, then environment and nearby installs."""
    candidates = []
    if config_folder is not None:
        candidates.append(Path(config_folder).resolve().parent)
    if os.environ.get('KKND2_GAME_DIR'):
        candidates.append(Path(os.environ['KKND2_GAME_DIR']).expanduser())
    candidates.extend((PROJECT_ROOT.parent, PROJECT_ROOT, Path.cwd()))
    for candidate in candidates:
        if (candidate / 'KWIPv3.exe').is_file() or (candidate / 'UCONFIG').is_dir():
            return candidate.resolve()
    return None


def default_folder(game_dir=None):
    game = Path(game_dir) if game_dir else find_game_dir()
    return (game if game else PROJECT_ROOT) / 'UCONFIG'


def default_limits_path():
    return PROJECT_ROOT / 'building_limits.cfg'


def default_overrides_path():
    return PROJECT_ROOT / 'overrides.cfg'


def default_unlocks_path():
    return PROJECT_ROOT / 'tech_unlocks.cfg'


def default_projectiles_path():
    return PROJECT_ROOT / 'projectiles.cfg'


def default_fixes_path():
    return PROJECT_ROOT / 'fixes.cfg'
