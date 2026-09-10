"""Build the portable Windows x64 EXE and a two-file ZIP; never package presets."""
import ast
import hashlib
from importlib.metadata import distribution
import os
from pathlib import Path
import re
import struct
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
EXE_NAME = 'KKND2 Unit Editor.exe'


def version():
    source = (ROOT/'src/kknd2_editor/__init__.py').read_text(encoding='utf-8')
    for node in ast.parse(source).body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == '__version__' for t in node.targets):
            value = ast.literal_eval(node.value)
            if re.fullmatch(r'\d+\.\d+\.\d+', value): return value
    raise ValueError('Set a three-part release version in __init__.py.')


def runtime_notices():
    runtime = Path(sys.base_prefix)
    pyinstaller = distribution('pyinstaller')
    license_entry = next(f for f in pyinstaller.files if str(f).endswith('/licenses/COPYING.txt'))
    sources = [('Python and bundled library notices', runtime/'LICENSE.txt'),
               ('Tcl 8.6.9 notice', ROOT/'tools/licenses/TCL.txt'),
               ('Tk notice', runtime/'tcl/tk8.6/license.terms'),
               ('PyInstaller bootloader notice and exception', Path(pyinstaller.locate_file(license_entry)))]
    return '\n\n'.join(title+'\n'+'-'*len(title)+'\n'+path.read_text(encoding='utf-8') for title,path in sources)


def readme(release_version):
    template = (ROOT/'tools/release-readme.txt').read_text(encoding='ascii')
    result = template.replace('@VERSION@',release_version).replace('@RUNTIME_NOTICES@',runtime_notices())
    return result.replace('\r\n','\n').replace('\n','\r\n').encode('utf-8')


def package(executable, destination, release_version, instructions):
    """Explicit allowlist: never recurse over a checkout or a game directory."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        archive.write(executable,EXE_NAME)
        archive.writestr('README.txt',instructions)
    with zipfile.ZipFile(destination) as archive:
        if set(archive.namelist()) != {EXE_NAME,'README.txt'} or archive.testzip():
            raise ValueError('Release ZIP verification failed.')
    digest = hashlib.sha256(destination.read_bytes()).hexdigest()
    destination.with_suffix('.sha256').write_text(digest+'  '+destination.name+'\n',encoding='ascii')
    return digest


def main():
    if os.name != 'nt' or struct.calcsize('P') != 8:
        raise SystemExit('Build with 64-bit Python on Windows.')
    release_version = version()
    instructions = readme(release_version) # Check required notices before building.
    numbers = tuple(int(v) for v in release_version.split('.'))+(0,)
    resource = f'''VSVersionInfo(
  ffi=FixedFileInfo(filevers={numbers!r}, prodvers={numbers!r}, mask=0x3f,
    flags=0, OS=0x40004, fileType=1, subtype=0, date=(0, 0)),
  kids=[StringFileInfo([StringTable('040904B0', [
    StringStruct('FileDescription', 'KKND2 Unit Editor'),
    StringStruct('FileVersion', '{release_version}'),
    StringStruct('ProductName', 'KKND2 Unit Editor'),
    StringStruct('ProductVersion', '{release_version}'),
    StringStruct('OriginalFilename', '{EXE_NAME}')])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])])
'''
    with tempfile.TemporaryDirectory(prefix='kknd2-release-') as temporary:
        folder=Path(temporary)
        resource_file=folder/'version.txt'
        resource_file.write_text(resource,encoding='ascii')
        # Isolate PyInstaller caches/specs/intermediates from the repository.
        environment=dict(os.environ,PYINSTALLER_CONFIG_DIR=str(folder/'cache'))
        subprocess.run([sys.executable,'-m','PyInstaller','--noconfirm','--clean',
            '--onefile','--windowed','--noupx','--name','KKND2 Unit Editor',
            '--paths',str(ROOT/'src'),
            '--add-data',str(ROOT/'src/kknd2_editor/fixes_native.json')+os.pathsep+'kknd2_editor',
            '--version-file',str(resource_file),'--distpath',str(folder/'dist'),
            '--workpath',str(folder/'build'),'--specpath',str(folder),
            str(ROOT/'Launch Editor.pyw')],cwd=ROOT,env=environment,check=True)
        destination=ROOT/'release'/f'KKND2-Unit-Editor-v{release_version}-windows-x64.zip'
        digest=package(folder/'dist'/EXE_NAME,destination,release_version,instructions)
    print('Release:',destination)
    print('SHA-256:',digest)


if __name__ == '__main__': main()
