"""Release metadata and strict archive contents; no compiler needed here."""
import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
import zipfile
from support import editor
from kknd2_editor import __version__

root=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('build_release',root/'tools/build_release.py')
build=importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


class ReleaseTests(TestCase):
    def test_version_and_ascii_player_instructions(self):
        self.assertEqual(build.version(),__version__)
        template=(root/'tools/release-readme.txt').read_text(encoding='ascii')
        for expected in ('@VERSION@','INSTALL','BASIC USE','https://github.com/AndersonHK/KKND2-Unit-Editor'):
            self.assertIn(expected,template)
        self.assertIn(f'v{__version__}-windows-x64.zip',(root/'README.md').read_text(encoding='utf-8'))

    def test_archive_uses_allowlist_instead_of_directory_scan(self):
        with TemporaryDirectory() as temporary:
            folder=Path(temporary)
            executable=folder/build.EXE_NAME
            executable.write_bytes(b'test executable')
            (folder/'fixes.cfg').write_text('private settings')
            (folder/'KWIPv3.exe').write_bytes(b'game')
            target=folder/'release.zip'
            digest=build.package(executable,target,__version__,b'ASCII README')
            with zipfile.ZipFile(target) as archive:
                self.assertEqual(archive.namelist(),[build.EXE_NAME,'README.txt'])
                self.assertEqual(archive.read('README.txt'),b'ASCII README')
            self.assertEqual(target.with_suffix('.sha256').read_text().split()[0],digest)
