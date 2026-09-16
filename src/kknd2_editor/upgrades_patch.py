"""Audited KWIPv3 upgrade sites and fixed-point payload data."""
import struct
from .upgrades import UPGRADES, validate
from .overrides import OVERRIDES

HOOKS = {
    'production_bill': (0x45ee4f, bytes.fromhex('55 8b ec 83 ec 1c')),
    'ai_production': (0x419a89, bytes.fromhex('8b 55 e0 89 42 44')),
    'ai_construction': (0x419c6d, bytes.fromhex('8b 55 c4 66 89 82 12 49 00 00')),
    'lab_start': (0x4947cd, bytes.fromhex('66 8b 04 8d c4 b2 51 00')),
    'lab_bar': (0x494528, bytes.fromhex('8b 4d f0 0f bf 51 4a 8b 04 95 c4 b2 51 00')),
    'lab_resume': (0x406e8b, bytes.fromhex('66 8b 0c 85 c4 b2 51 00')),
    'ai_lab': (0x419dbc, bytes.fromhex('8b 55 c8 8b 45 ec')),
    'repair_tier': (0x4d5a90, bytes.fromhex('c1 e1 07 81 c1 00 01 00 00 c1 e1 08 0f af 0d 8c 05 51 00 c1 f9 10')),
}
OIL_TABLE = 0x5285dc
STOCK_OIL = (65536, 68813, 72090, 75367, 78644, 81921)
PRODUCTION_ROWS = ('outpost_speed', 'infantry_speed', 'vehicle_speed', 'armoury_speed')


def changed(values, row):
    return values is not None and any(values[f'{row}.{i}'] != UPGRADES[f'{row}.{i}']['default'] for i in range(6))


def selected_hooks(values):
    if values is None: return {}
    validate(values)
    names = []
    if any(changed(values, row) for row in PRODUCTION_ROWS):
        names.extend(('production_bill', 'ai_production', 'ai_construction'))
    if changed(values, 'lab_upgrade'):
        names.extend(('lab_start', 'lab_bar', 'lab_resume', 'ai_lab'))
    if changed(values, 'repair_rate'): names.append('repair_tier')
    return {name: HOOKS[name] for name in names}


def validate_memory(read, values, overrides=None):
    if values is None: return
    validate(values)
    settings = overrides if overrides is not None else {key: s['default'] for key, s in OVERRIDES.items()}
    maximum_cost = settings['research_cost'] + 5 * settings['research_cost_step']
    if any(round(maximum_cost * values[f'lab_upgrade.{i}']) > 32767 for i in range(1, 6)):
        raise ValueError('Research lab multiplier × research cost can exceed the game’s 32,767 RU counter. Lower the lab multiplier or research cost/step.')
    for name, (address, before) in selected_hooks(values).items():
        if read(address, len(before)) != before:
            raise ValueError(f'KWIPv3 {name} code does not match the supported build.')
    for address, before, _ in table_plan(values):
        if read(address, len(before)) != before:
            raise ValueError('KWIPv3 oil yield table does not match the supported build.')


def table_plan(values):
    if values is None or not changed(values, 'oil_yield'): return []
    result = []
    for level, stock in enumerate(STOCK_OIL):
        value = values[f'oil_yield.{level}']
        # Stock uses a rounded increment of 3277, not individually rounded ratios.
        raw = stock if value == UPGRADES[f'oil_yield.{level}']['default'] else round(value * 65536)
        if raw != stock:
            result.append((OIL_TABLE+4*level, struct.pack('<I', stock), struct.pack('<I', raw)))
    return result


def fill_payload(image, exports, values):
    if values is None: return
    arrays = {
        'lab_factors': [round(values[f'lab_upgrade.{i}']*100) for i in range(6)],
        'repair_rates': [round(values[f'repair_rate.{i}']*128) for i in range(6)],
        'production_factors': [round(values[f'{row}.{i}']*100) for row in PRODUCTION_ROWS for i in range(6)],
    }
    for name, data in arrays.items():
        struct.pack_into('<'+'I'*len(data), image, exports[name], *data)
