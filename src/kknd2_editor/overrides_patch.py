"""Audited x86 patch sites for the hash-checked KWIPv3 build.

Only the launcher-created suspended process is modified. Code stubs execute on
the game's own simulation thread. No on-disk EXE changes or runtime dependencies.
"""
import struct
from .overrides import OVERRIDES, validate

SITES = {address: bytes.fromhex(raw) for address, raw in {
    0x494528: '8b 4d f0 0f bf 51 4a 8b 04 95 c4 b2 51 00',
    0x40EF92: 'ba 07 00 00 00',
    0x40EF4F: 'ba 15 00 00 00',
    0x466E81: '8d 4c 10 04',
    0x466E8E: '8d 4c 10 04',
    0x466E98: '83 ea 05',
    0x466EA1: '83 e8 05',
    0x466EAA: '83 e9 06',
    0x466EC1: '8d 54 01 06',
    0x466ED1: '83 e8 06',
    0x466EE8: '8d 4c 10 06',
    0x49431F: 'b1 1b e8 d9 0b fa ff',  # research time initializer input
    0x494329: 'b1 1a e8 cf 0b fa ff',  # research cost initializer input
    0x49434B: 'b9 05 00 00 00 2b 4d f4',  # (5-index), time step
    0x494362: 'b9 05 00 00 00 2b 4d f4 6b c9 14',  # (5-index)*20
    0x4482C9: '81 7d f8 90 01 00 00',  # cargo bar clamp
    0x4482D2: 'c7 45 f8 90 01 00 00',
    0x4482F3: 'b9 90 01 00 00',        # cargo bar denominator
    0x4AAFB6: '81 b8 a4 01 00 00 90 01 00 00',  # routing full check
    0x4ABD3D: '81 b9 a4 01 00 00 90 01 00 00',  # loading full check
    0x4ABDCF: '81 b9 a4 01 00 00 90 01 00 00',
    0x4ABDDE: 'c7 82 a4 01 00 00 90 01 00 00',  # cargo clamp
    0x4C8A61: 'c7 81 a4 01 00 00 90 01 00 00',  # spawn flag: initially full
    0x4ABD5A: 'a1 8c 05 51 00 c1 e0 0f c1 f8 10',  # load increment
    0x4ABD72: 'a1 8c 05 51 00 c1 e0 0f c1 f8 10',
    0x4ABDA9: '8b 55 f8 c1 fa 08',     # rig debit
    0x4AC1E6: '8b 0d 8c 05 51 00 c1 e1 0c c1 f9 10',  # unload amount
}.items()}
CAPACITY_SITES = (0x4482C9, 0x4482D2, 0x4482F3, 0x4AAFB6,
                  0x4ABD3D, 0x4ABDCF, 0x4ABDDE, 0x4C8A61)


def u32(value):
    return struct.pack('<I', value)


class Code:
    """Tiny label resolver for these fixed, reviewed instruction sequences."""
    def __init__(self):
        self.data, self.labels, self.fixups = bytearray(), {}, []

    def emit(self, hex_bytes):
        self.data.extend(bytes.fromhex(hex_bytes))

    def immediate(self, hex_bytes, value):
        self.emit(hex_bytes)
        self.data.extend(u32(value))

    def label(self, name):
        self.labels[name] = len(self.data)

    def branch(self, opcode, name):
        self.emit(opcode)
        self.fixups.append((len(self.data), name))
        self.data.append(0)

    def finish(self):
        for offset, name in self.fixups:
            self.data[offset] = struct.pack('b', self.labels[name] - offset - 1)[0]
        return bytes(self.data)


def loading_stub(values):
    c = Code()
    c.emit('51 52')                   # preserve ecx, edx; result in eax
    c.immediate('a1', 0x51058C)       # game speed
    c.immediate('b9', values['rig_loading_rate'])
    c.emit('f7 e1 0f ac d0 10 c1 ea 10')  # unsigned 64-bit product >> 16
    c.emit('8b 4d f0')                # unit = [ebp-0x10]
    c.emit('51')                      # preserve unit temporarily
    c.immediate('b9', values['tanker_capacity'] << 8)
    c.emit('87 0c 24')                # ecx=unit; stack top=capacity fixed point
    c.emit('8b 89 a8 01 00 00')       # current loading accumulator
    c.emit('29 0c 24 59')             # ecx=remaining capacity
    c.emit('85 c9')
    c.branch('7e', 'empty')
    c.emit('85 d2')                   # high product bits => clamp
    c.branch('75', 'clamp')
    c.emit('39 c8')
    c.branch('76', 'done')
    c.label('clamp')
    c.emit('89 c8')                   # eax=remaining capacity
    c.branch('eb', 'done')
    c.label('empty')
    c.emit('31 c0')
    c.label('done')
    c.emit('5a 59 c3')
    return c.finish()


def debit_stub():
    # Debit only the increase in whole oil units, carrying fractional loading
    # forward. The original increment>>8 would mint oil at fractional rates.
    return bytes.fromhex(
        '50 51 8b 4d f0 8b 91 a8 01 00 00 89 d0 '
        '2b 45 f8 c1 fa 08 c1 f8 08 29 c2 59 58 c3')


def unloading_stub(values):
    c = Code()
    c.emit('50 52')                   # preserve eax, edx; result in ecx
    c.immediate('a1', 0x51058C)
    c.immediate('b9', values['powerplant_unloading_rate'])
    c.emit('f7 e1 0f ac d0 10 c1 ea 10')
    c.emit('8b 4d ec 8b 89 a8 01 00 00')  # remaining payout
    c.emit('85 d2')
    c.branch('75', 'done')            # huge result => use remaining payout
    c.emit('39 c8')
    c.branch('73', 'done')
    c.emit('89 c1')
    c.label('done')
    c.emit('5a 58 c3')
    return c.finish()


def needs_loading_hook(values):
    return any(values[key] != OVERRIDES[key]['default']
               for key in ('rig_loading_rate', 'tanker_capacity'))


def research_step_stub(step):
    return bytes.fromhex('b9 05 00 00 00 2b 4d f4 69 c9') + u32(step) + b'\xc3'


def stub_bundle(values):
    validate(values)
    blob, offsets = bytearray(), {}
    for key in ('research_cost_step', 'research_time_step'):
        if values[key] != OVERRIDES[key]['default']:
            offsets[key] = len(blob)
            blob.extend(research_step_stub(values[key]))
    if needs_loading_hook(values):
        offsets['loading'] = len(blob)
        blob.extend(loading_stub(values))
        offsets['debit'] = len(blob)
        blob.extend(debit_stub())
    if values['powerplant_unloading_rate'] != OVERRIDES['powerplant_unloading_rate']['default']:
        offsets['unloading'] = len(blob)
        blob.extend(unloading_stub(values))
    return bytes(blob), offsets


def patch_plan(values, stub_address=0):
    validate(values)
    blob, offsets = stub_bundle(values)
    if blob and not 0 < stub_address <= 0xFFFFFFFF - len(blob):
        raise ValueError('Override stubs require a valid 32-bit allocation.')
    plan = []

    def add(address, after):
        before = SITES[address]
        if len(before) != len(after):
            raise ValueError('Override patch changed instruction span length.')
        plan.append((address, before, after))

    # Always replace the native option reads: these are absolute settings,
    # including when set to their stock defaults. Reapplied on each match init.
    for address, key in ((0x49431F, 'research_time'), (0x494329, 'research_cost')):
        add(address, b'\xb8' + u32(values[key]) + b'\x90\x90')
    # Match the lab-owned remaining-cost field, not the target building's tier.
    add(0x494528, bytes.fromhex('8b 4d f8 0f bf 51 fe 8b 04 95 c4 b2 51 00'))
    for address, key in ((0x40EF92, 'solar_income'), (0x40EF4F, 'thermal_income')):
        if values[key] != OVERRIDES[key]['default']:
            add(address, b'\xba' + u32(values[key]))
    if values['building_placement_range'] != 5:
        for address, delta in {4615809: -1, 4615822: -1, 4615832: 0, 4615841: 0, 4615850: 1, 4615873: 1, 4615889: 1, 4615912: 1}.items():
            add(address, SITES[address][:-1] + bytes([values['building_placement_range'] + delta]))
    if values['tanker_capacity'] != 400:
        for address in CAPACITY_SITES:
            add(address, SITES[address][:-4] + u32(values['tanker_capacity']))
    for address, key in ((0x4ABD5A, 'loading'), (0x4ABD72, 'loading'),
                         (0x4ABDA9, 'debit'), (0x4AC1E6, 'unloading'),
                         (0x49434B, 'research_time_step'), (0x494362, 'research_cost_step')):
        if key in offsets:
            relative = (stub_address + offsets[key] - address - 5) & 0xFFFFFFFF
            add(address, b'\xe8' + u32(relative) + b'\x90' * (len(SITES[address]) - 5))
    return plan


def validate_memory(read):
    for address, before in SITES.items():
        if read(address, len(before)) != before:
            raise ValueError(f'Unsupported KWIPv3 override instructions at {address:#x}; launch cancelled.')
