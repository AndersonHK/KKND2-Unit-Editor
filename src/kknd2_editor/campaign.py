"""Resolve the native -stats display-name option without copying game files."""
from pathlib import Path
import re
import subprocess


def command_line(executable, configuration=None):
    exe = Path(executable).resolve()
    args = [str(exe)]
    if configuration is not None:
        path = Path(configuration).resolve()
        folder = exe.parent / 'UCONFIG'
        match = re.fullmatch(r'UCONFIG_(\d{2})\.cfg', path.name, re.IGNORECASE)
        if path.parent != folder.resolve() or not match or int(match[1]) >= 30:
            raise ValueError('Campaign unit stats require a UCONFIG_00.cfg through UCONFIG_29.cfg '
                             'file inside this game\'s UCONFIG folder. Open that file in the Unit editor tab.')
        def title(file):
            with file.open('rb') as stream:
                raw = stream.read(120)
            if len(raw) != 120:
                raise ValueError(f'{file.name}: incomplete unit configuration title.')
            return raw.decode('utf-16le').split('\0', 1)[0]
        name = title(path)
        if not name or len(name) >= 60 or any(ord(c) < 32 or c == '"' for c in name):
            raise ValueError('The campaign configuration needs a nonempty title under 60 characters, '
                             'without control characters or double quotes.')
        # Native selection compares display names and chooses the first match.
        # Refuse duplicates rather than silently loading a different preset.
        for sibling in folder.iterdir():
            other = re.fullmatch(r'UCONFIG_(\d{2})\.cfg', sibling.name, re.IGNORECASE)
            if sibling.resolve() == path or not other or int(other[1]) >= 30:
                continue
            if title(sibling).casefold() == name.casefold():
                raise ValueError(f'{path.name} and {sibling.name} share the title {name!r}. '
                                 'Give the presets unique names in the game\'s unit editor before campaign launch.')
        args.extend(('-stats', name))
    return subprocess.list2cmdline(args)
