"""Build our import-free x86 module with MSVC; export a constrained payload.

Run from a VS x86 Native Tools prompt, or pass --compiler PATH/TO/x86/cl.exe.
The editor ships the generated payload and does not require a compiler.
"""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile


def extract(raw):
    def u16(offset): return struct.unpack_from('<H', raw, offset)[0]
    def u32(offset): return struct.unpack_from('<I', raw, offset)[0]
    pe = u32(0x3c)
    if raw[pe:pe+4] != b'PE\0\0' or u16(pe+4) != 0x14c or u16(pe+24) != 0x10b:
        raise ValueError('Expected an x86 PE32 module.')
    opt = pe+24
    if u32(opt+16) or any(u32(opt+96+i*8) for i in (1, 9, 11, 12, 13)):
        raise ValueError('Module must have no entry point, imports, TLS or delay imports.')
    sections = []
    table = opt+u16(pe+20)
    for i in range(u16(pe+6)):
        offset = table+i*40
        name = raw[offset:offset+8].rstrip(b'\0').decode('ascii')
        size, rva, disk_size, disk = struct.unpack_from('<4I', raw, offset+8)
        sections.append(dict(name=name, rva=rva, size=max(size, disk_size),
                             executable=bool(u32(offset+36) & 0x20000000),
                             data=base64.b64encode(raw[disk:disk+disk_size]).decode()))
    def file_offset(rva):
        for i in range(u16(pe+6)):
            off = table+i*40
            size, address, disk_size, disk = struct.unpack_from('<4I', raw, off+8)
            if address <= rva < address+disk_size: return disk+rva-address
        raise ValueError('RVA outside initialized sections.')
    exports = {}
    off = file_offset(u32(opt+96))
    functions, names, ordinals = (file_offset(u32(off+i)) for i in (28, 32, 36))
    for i in range(u32(off+24)):
        start = file_offset(u32(names+4*i))
        name = raw[start:raw.index(b'\0', start)].decode('ascii').lstrip('_@').split('@')[0]
        exports[name] = u32(functions+4*u16(ordinals+2*i))
    relocations = []
    reloc, size = u32(opt+136), u32(opt+140)
    cursor, end = file_offset(reloc), file_offset(reloc)+size
    while cursor < end:
        page, block_size = u32(cursor), u32(cursor+4)
        if block_size < 8 or cursor+block_size > end: raise ValueError('Invalid relocations.')
        for off in range(cursor+8, cursor+block_size, 2):
            entry = u16(off)
            if entry >> 12 == 3: relocations.append(page+(entry & 0xfff))
            elif entry >> 12: raise ValueError('Only HIGHLOW relocations are supported.')
        cursor += block_size
    return dict(format=1, base=u32(opt+28), size=u32(opt+56),
                sections=sections, exports=exports, relocations=relocations)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--compiler', default=shutil.which('cl'))
    args = parser.parse_args()
    if not args.compiler: parser.error('Use a VS x86 Native Tools prompt or --compiler.')
    compiler = Path(args.compiler).resolve()
    environment = dict(os.environ)
    # Cross-compilers keep their host support DLLs in the sibling x64 folder.
    environment['PATH'] = os.pathsep.join((str(compiler.parent), str(compiler.parent.parent/'x64'),
                                          environment.get('PATH', '')))
    source = Path(__file__).resolve().parent
    with tempfile.TemporaryDirectory(prefix='kknd2-native-') as folder:
        obj, dll = Path(folder)/'fixes.obj', Path(folder)/'fixes.dll'
        subprocess.run([str(compiler), '/nologo', '/c', '/O2', '/GS-', '/GR-', '/Zl',
                        '/EHs-c-', '/W4', '/WX', '/Fo'+str(obj), str(source/'fixes.cpp')], check=True, env=environment)
        subprocess.run([str(compiler.with_name('link.exe')), '/nologo', '/DLL', '/NOENTRY',
                        '/NODEFAULTLIB', '/MACHINE:X86', '/SAFESEH:NO', '/DYNAMICBASE',
                        '/NXCOMPAT', '/OPT:REF', '/OPT:ICF', '/Brepro', '/OUT:'+str(dll), str(obj)], check=True, env=environment)
        payload = extract(dll.read_bytes())
    payload['source_sha256'] = hashlib.sha256((source/'fixes.cpp').read_bytes().replace(b'\r\n', b'\n') +
                                             (source/'kwip_abi.h').read_bytes().replace(b'\r\n', b'\n') +
                                             (source/'upgrades.h').read_bytes().replace(b'\r\n', b'\n')).hexdigest()
    output = source.parent/'src'/'kknd2_editor'/'fixes_native.json'
    output.write_text(json.dumps(payload, indent=2)+'\n', encoding='utf-8')
    print('Built', output.name, 'from', len(payload['sections']), 'sections.')


if __name__ == '__main__': main()
