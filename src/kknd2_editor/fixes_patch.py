"""Version-specific bridge to the compiled, import-free native fixes module.

Only pristine, whole instructions are intercepted. Business logic is C++ in
native/fixes.cpp; the generated payload needs no compiler on players' machines.
"""
import base64
import json
from pathlib import Path
import struct
from .fixes import validate
from . import upgrades_patch
from .building_limits import validate as validate_limits

HOOKS = {
    'select_near': (0x4a1893, bytes.fromhex('55 8b ec 81 ec 8c 00 00 00')),
    'select_wide': (0x4a2039, bytes.fromhex('55 8b ec 83 ec 74')),
    'validate_target': (0x4a265e, bytes.fromhex('55 8b ec 81 ec 8c 00 00 00')),
    'shift_placement': (0x466d01, bytes.fromhex('88 15 08 55 56 00')),
    'ai_solar_limit': (0x4277a6, bytes.fromhex('83 b8 94 00 00 00 04')),
    'ai_thermal_limit': (0x4277f4, bytes.fromhex('83 b8 90 00 00 00 04')),
}
CALL_HOOKS = {'shift_placement', 'ai_solar_limit', 'ai_thermal_limit'}


def selected_hooks(values, limits=None):
    validate(values)
    names = []
    if values['damage_priority'] or values['acquisition_range']: names.extend(('select_near', 'select_wide'))
    if values['damage_priority'] or values['zero_damage_filter']: names.append('validate_target')
    if values['shift_build']: names.append('shift_placement')
    if limits is not None:
        validate_limits(limits)
        for suffix, hook in (('COLLECTOR', 'ai_solar_limit'), ('CONVERTER', 'ai_thermal_limit')):
            if any(limits[f'UNIT_{faction}_{suffix}'] != 4 for faction in ('SURV', 'MUTE', 'ROBOT')):
                names.append(hook)
    return {key: HOOKS[key] for key in names}


def validate_memory(read, values, limits=None):
    for name, (address, before) in selected_hooks(values, limits).items():
        if read(address, len(before)) != before:
            raise ValueError(f'KWIPv3 {name} code does not match the supported build.')


def load_payload():
    data = json.loads(Path(__file__).with_name('fixes_native.json').read_text(encoding='utf-8'))
    if data['format'] != 1 or not 0 < data['size'] <= 0x100000:
        raise ValueError('Unsupported native fixes payload.')
    return data


def branch(address, destination, size, call=False):
    return bytes([0xe8 if call else 0xe9]) + struct.pack('<I', (destination-address-5) & 0xffffffff) + b'\x90'*(size-5)


def prepare(read, write, allocate, seal, values, limits=None, upgrades=None):
    """Write/verify helpers first; return hooks to install after all validation."""
    hooks = selected_hooks(values, limits)
    upgrade_hooks = upgrades_patch.selected_hooks(upgrades)
    hooks.update(upgrade_hooks)
    if not hooks: return []
    payload = load_payload()
    size = payload['size']
    address = allocate(size + 0x1000) # One additional executable page for original prologues.
    if not 0 < address <= 0xffffffff-size-0x1000 or address % 0x1000:
        raise ValueError('Native fixes require a page-aligned 32-bit allocation.')
    image = bytearray(size + 0x1000)
    for section in payload['sections']:
        raw = base64.b64decode(section['data'], validate=True)
        start, length = section['rva'], section['size']
        if start % 4096 or len(raw) > length or start+length > size:
            raise ValueError('Invalid native fixes section.')
        image[start:start+len(raw)] = raw
    for offset in payload['relocations']:
        if not 0 <= offset <= size-4: raise ValueError('Invalid native relocation.')
        original = struct.unpack_from('<I', image, offset)[0]
        struct.pack_into('<I', image, offset, (original + address - payload['base']) & 0xffffffff)
    exports = payload['exports']
    def set_export(key, value):
        offset = exports[key]
        if not 0 <= offset <= size-4: raise ValueError('Invalid native export.')
        struct.pack_into('<I', image, offset, value)
    set_export('zero_damage', int(values['zero_damage_filter']))
    set_export('damage_priority', int(values['damage_priority']))
    set_export('acquisition_range', int(values['acquisition_range']))
    upgrades_patch.fill_payload(image, exports, upgrades)
    cursor = size
    originals = {'select_near': 'original_near', 'select_wide': 'original_wide', 'validate_target': 'original_validate', 'production_bill': 'original_production'}
    plan = []
    for name, (site, before) in hooks.items():
        if name in originals:
            # These verified prologues contain no relative instructions.
            code = before + branch(address+cursor+len(before), site+len(before), 5)
            image[cursor:cursor+len(code)] = code
            set_export(originals[name], address+cursor)
            cursor += 32
        plan.append((site, before, branch(site, address+exports[name], len(before), name in CALL_HOOKS or (name in upgrade_hooks and name not in originals))))
    write(address, bytes(image))
    if read(address, len(image)) != image: raise OSError('Native fixes verification failed.')
    for section in payload['sections']:
        if section['executable']: seal(address+section['rva'], section['size'])
    seal(address+size, 0x1000)
    # Globals/context remain RW and non-executable; only code pages become RX.
    return plan
