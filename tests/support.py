"""Synthetic fixtures and isolated GUI state; no game installation required."""
import atexit
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from kknd2_editor import app as editor

_temporary = TemporaryDirectory(prefix='kknd2-tests-')
atexit.register(_temporary.cleanup)
FIXTURE_FOLDER = Path(_temporary.name)


def synthetic_config():
    title = 'Test configuration'.ljust(60, '\0').encode('utf-16le')
    header = ('/'.join(field + ' ' for field in editor.FIELDS) + '/\n').encode('utf-16le')
    records = []
    for identifier, values in editor.DEFAULTS.items():
        records.append(identifier.ljust(30) + '\t' +
                       '\t'.join(value.ljust(6) for value in values) + '\t\n')
    return title + header + ''.join(records).encode('ascii')


# Optional real-format integration input is only read, and copied before use.
external = os.environ.get('KKND2_TEST_FILE')
SOURCE = FIXTURE_FOLDER / 'UCONFIG_02.cfg'
SOURCE.write_bytes(Path(external).read_bytes() if external else synthetic_config())


def make_editor(*args, **kwargs):
    if not args:
        kwargs.setdefault('folder', FIXTURE_FOLDER)
    kwargs.setdefault('limits_path', FIXTURE_FOLDER / 'unused-default-limits.cfg')
    kwargs.setdefault('overrides_path', FIXTURE_FOLDER / 'unused-default-overrides.cfg')
    kwargs.setdefault('unlocks_path', FIXTURE_FOLDER / 'unused-default-unlocks.cfg')
    kwargs.setdefault('projectiles_path', FIXTURE_FOLDER / 'unused-default-projectiles.cfg')
    kwargs.setdefault('upgrades_path', FIXTURE_FOLDER / 'unused-default-upgrades.cfg')
    kwargs.setdefault('fixes_path', FIXTURE_FOLDER / 'unused-default-fixes.cfg')
    return editor.Editor(*args, **kwargs)
