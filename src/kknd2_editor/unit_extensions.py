"""Versioned, per-preset additions that never alter the native UCONFIG schema."""
import json
import os
from pathlib import Path
import struct
import tempfile

# Verified KWIPv3 vehicle turret definitions. Infantry/direct weapons still use
# native Bullet-Count; specialized tower/aircraft handlers are not covered here.
# Stable unit ID: (unit enum, turret definition address, stock shots per burst).
BURSTS = {
    'UNIT_SURV_HOVERBUGGY': (52, 0x52af60, 6),
    'UNIT_SURV_ATV': (53, 0x52afd0, 8),
    'UNIT_SURV_ANACONDATANK': (54, 0x52af98, 2),
    'UNIT_SURV_BARRAGECRAFT': (55, 0x52af28, 1),
    'UNIT_SURV_AUTOCANNONTANK': (56, 0x52b008, 2),
    'UNIT_SURV_JUGGERNAUT': (57, 0x52b040, 10),
    'UNIT_MUTE_CRINOID': (60, 0x52acf8, 5),
    'UNIT_MUTE_MASTODON': (61, 0x52ad68, 2),
    'UNIT_MUTE_HIPPO': (62, 0x52ad30, 10),
    'UNIT_MUTE_CRAB': (63, 0x52ada0, 1),
    'UNIT_ROBOT_RESPONSEBOT': (66, 0x52aeb8, 8),
    'UNIT_ROBOT_RADIATOR': (67, 0x52ae10, 1),
    'UNIT_ROBOT_TANKBOT': (68, 0x52aef0, 2),
    'UNIT_ROBOT_DOOMDOME': (69, 0x52add8, 1),
    'UNIT_ROBOT_CAUTERISER': (70, 0x52ae48, 1),
    'UNIT_ROBOT_GRIMREAPER': (71, 0x52ae80, 15),
}
SCHEMA = 'kknd2-editor-unit-extensions'
VERSION = 1
MAX_BURST = 127  # Runtime counter unit+0x310 is incremented/read as signed char.


def extension_path(config_path):
    path = Path(config_path)
    if path.stem.lower().endswith('_ext'):
        raise ValueError('Open the original UCONFIG file, not its _ext companion.')
    return path.with_name(path.stem + '_ext.cfg')


def validate(units, identifiers=None):
    if not isinstance(units, dict):
        raise ValueError('Extended units must be an object keyed by unit ID.')
    for identifier, fields in units.items():
        if identifier not in BURSTS or (identifiers is not None and identifier not in identifiers):
            raise ValueError(f'Unsupported extended unit: {identifier}')
        if not isinstance(fields, dict) or set(fields) != {'burst_count'}:
            raise ValueError(f'{identifier}: expected burst_count only.')
        value = fields['burst_count']
        if type(value) is not int or not 1 <= value <= MAX_BURST:
            raise ValueError(f'{identifier}: Burst Count must be a whole number from 1 to {MAX_BURST}.')
    return units


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f'Duplicate extension key: {key}')
        result[key] = value
    return result


def encode(title_header, units):
    validate(units)
    # The game's UCONFIG_*.CFG scan accepts _nn_ext too, reads its title, then
    # loads the canonical _nn.cfg. An identical terminated title makes either
    # enumeration order harmless. The remaining bytes belong only to us.
    title = title_header[:120].decode('utf-16le').split('\0', 1)[0]
    if len(title.encode('utf-16le')) > 118 or '\n' in title or '\r' in title:
        raise ValueError('The extension requires a single-line preset title shorter than 60 WCHARs.')
    header = title.encode('utf-16le').ljust(120, b'\0')
    body = dict(schema=SCHEMA, version=VERSION, units=units)
    return header + (json.dumps(body, indent=2, sort_keys=True) + '\n').encode('utf-8')


class UnitExtensions:
    def __init__(self, config_path, identifiers):
        self.path = extension_path(config_path)
        self.raw = self.path.read_bytes() if self.path.exists() else None
        self.units = {}
        if self.raw is not None:
            try:
                header = self.raw[:120]
                if len(header) != 120 or '\0' not in header.decode('utf-16le'):
                    raise ValueError('Missing native preset title header.')
                data = json.loads(self.raw[120:].decode('utf-8'), object_pairs_hook=unique_object)
                if not isinstance(data, dict) or set(data) != {'schema', 'version', 'units'}:
                    raise ValueError('Expected schema, version and units.')
                if data['schema'] != SCHEMA or type(data['version']) is not int or data['version'] != VERSION:
                    raise ValueError('Unsupported unit-extension schema or version.')
                self.units = validate(data['units'], identifiers)
            except (ValueError, UnicodeError) as exc:
                raise ValueError(f'Cannot read {self.path.name}: {exc}') from exc

    def check_unchanged(self):
        if self.path.is_symlink():
            raise OSError('The extension must be a regular file, not a symbolic link.')
        disk = self.path.read_bytes() if self.path.exists() else None
        if disk != self.raw:
            raise OSError(f'{self.path.name} changed on disk. Reopen the preset before saving.')

    def save(self, title_header, units):
        self.check_unchanged()
        # No companion is needed until an extended field is customized.
        if self.raw is None and not units:
            return
        payload = encode(title_header, units)
        if payload == self.raw:
            return
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode='wb', dir=self.path.parent,
                    prefix='.kknd2-', suffix='.tmp', delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            if temporary.read_bytes() != payload:
                raise OSError('Extension write verification failed.')
            self.check_unchanged()
            os.replace(str(temporary), str(self.path))
            temporary = None
            self.raw = payload
            self.units = units
            if self.path.read_bytes() != payload:
                raise OSError('Extension post-save verification failed.')
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)


def patch_plan(read, units):
    """Check original pointers/handler/count before returning data-only writes."""
    validate(units)
    plan = []
    for identifier, fields in units.items():
        enum, turret, default = BURSTS[identifier]
        for address, expected in ((0x52bed8 + enum * 0x110 + 0x60, turret),
                                  (turret + 0x28, 0x4da4d9), (turret + 0x10, default)):
            if read(address, 4) != struct.pack('<I', expected):
                raise ValueError(f'KWIPv3 turret data does not match: {identifier}.')
        value = fields['burst_count']
        if value != default:
            plan.append((turret + 0x10, struct.pack('<I', default), struct.pack('<I', value)))
    return plan
