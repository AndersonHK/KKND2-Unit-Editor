"""Per-faction production unlock tiers and relocated native menu lists."""
import struct
from .building_limits import LimitsConfig
from .unlock_data import UNLOCKS, TABLES, ORIGINAL


def validate(values):
    if not isinstance(values, dict) or set(values) != set(UNLOCKS):
        raise ValueError('Tech unlocks must contain exactly the supported unit/building IDs.')
    for key, value in values.items():
        if type(value) is not int or not 0 <= value <= 5:
            raise ValueError(f'{key}: enter a tech level from 0 to 5.')
    return dict(values)


class UnlocksConfig(LimitsConfig):
    specs = UNLOCKS
    schema = 'kknd2-editor-tech-unlocks'
    value_key = 'unlocks'
    title = 'Tech unlocks'
    temporary_prefix = '.unlocks-'
    validate = staticmethod(validate)


def validate_memory(read):
    for address, expected in ORIGINAL.items():
        if read(address, len(expected)) != expected:
            raise ValueError(f'Unsupported KWIPv3 tech unlock table at {address:#x}; launch cancelled.')


def table_bundle(values, base=0):
    """Keep producer, faction, order, duplicates and special commands intact.

    Split a three-faction row only when its factions select different tiers.
    The engine already handles 0xffff absent-faction slots and list sentinels.
    """
    validate(values)
    if all(values[k] == s['default'] for k, s in UNLOCKS.items()):
        return b'', []
    tiers = {spec['enum']: values[key] for key, spec in UNLOCKS.items()}
    blob, plan = bytearray(), []
    for table, levels in TABLES.items():
        new_levels = [[] for _ in range(6)]
        for original_level, rows in enumerate(levels):
            for row in rows:
                destinations = {tiers.get(unit, original_level) for unit in row if unit != 0xffff}
                for level in sorted(destinations):
                    new_levels[level].append(tuple(unit if unit != 0xffff and tiers.get(unit, original_level) == level
                                                   else 0xffff for unit in row))
        pointers = []
        for rows in new_levels:
            pointers.append(base + len(blob))
            for row in rows:
                blob.extend(struct.pack('<3H', *row))
            blob.extend(b'\xff' * 6)
        plan.append((table, ORIGINAL[table], struct.pack('<6I', *pointers)))
    return bytes(blob), plan
