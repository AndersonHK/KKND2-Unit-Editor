"""Per-weapon speed data and homing lifetime initialization for supported KWIPv3."""
from .projectile_data import PROJECTILES
from .projectiles import validate
from .overrides_patch import Code, u32

LIFETIME_SITE = 0x4E1C99
LIFETIME_ORIGINAL = bytes.fromhex('8b 55 fc c6 42 50 22')


def lifetime_stub(values):
    validate(values)
    changed = [(p['address'], values[key + '.lifetime']) for key, p in PROJECTILES.items()
               if p['lifetime'] is not None and values[key + '.lifetime'] != p['lifetime']]
    if not changed:
        return b''
    c = Code()
    c.emit('8b 55 fc')                 # original edx = projectile instance
    c.emit('9c 50 8b 42 4c')          # preserve flags/eax; eax = weapon definition
    c.emit('c6 42 50 22')             # default for unedited / unlisted homing weapons
    for i, (address, lifetime) in enumerate(changed):
        c.immediate('3d', address)
        c.branch('75', str(i))
        c.emit('c6 42 50 ' + f'{lifetime:02x}')
        c.branch('eb', 'done')
        c.label(str(i))
    c.label('done')
    c.emit('58 9d c3')
    return c.finish()


def patch_plan(values, stub_address=0):
    validate(values)
    plan = []
    for key, projectile in PROJECTILES.items():
        if projectile['speed'] is not None:
            value = values[key + '.speed']
            if value != projectile['speed']:
                plan.append((projectile['address'] + 0x14, u32(projectile['speed']), u32(value)))
    blob = lifetime_stub(values)
    if blob:
        if not 0 < stub_address <= 0xffffffff - len(blob):
            raise ValueError('Projectile lifetime helper requires a valid 32-bit allocation.')
        relative = (stub_address - LIFETIME_SITE - 5) & 0xffffffff
        plan.append((LIFETIME_SITE, LIFETIME_ORIGINAL, b'\xe8' + u32(relative) + b'\x90\x90'))
    return plan


def validate_memory(read):
    if read(LIFETIME_SITE, len(LIFETIME_ORIGINAL)) != LIFETIME_ORIGINAL:
        raise ValueError('Unsupported KWIPv3 projectile lifetime instructions.')
    for projectile in PROJECTILES.values():
        address = projectile['address']
        if read(address + 4, 4) != u32(projectile['handler']):
            raise ValueError(f'Unexpected projectile handler at {address:#x}.')
        if projectile['speed'] is not None and read(address + 0x14, 4) != u32(projectile['speed']):
            raise ValueError(f'Unexpected projectile speed at {address:#x}.')
