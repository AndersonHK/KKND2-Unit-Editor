"""Six-level building benefits; independent of research base/step overrides."""
import math
from .building_limits import LimitsConfig

ROWS = {
    'lab_upgrade': dict(name='Research lab upgrade cost and time',
        hint='Multiplier when upgrading the lab to this level', defaults=(1,)*6, minimum=0.1, maximum=10),
    'oil_yield': dict(name='Power station oil yield',
        hint='Resource units earned per unit of delivered oil', defaults=(1, 1.05, 1.10, 1.15, 1.20, 1.25), minimum=0.1, maximum=3),
    'repair_rate': dict(name='Repair and healing rate',
        hint='HP per repair update at normal speed; game-speed scaled', defaults=(2, 3, 4, 5, 6, 7), minimum=0.1, maximum=32),
    'outpost_speed': dict(name='Outpost construction speed',
        hint='Buildings: 2 halves build time; highest owned tier', defaults=(1,)*6, minimum=0.1, maximum=10),
    'infantry_speed': dict(name='Infantry production speed',
        hint='Speed multiplier: 2 builds in half the time', defaults=(1,)*6, minimum=0.1, maximum=10),
    'vehicle_speed': dict(name='Vehicle production speed',
        hint='Speed multiplier: 2 builds in half the time', defaults=(1,)*6, minimum=0.1, maximum=10),
    'armoury_speed': dict(name='Armoury construction speed',
        hint='Defenses and walls: 2 halves build time; highest owned tier', defaults=(1,)*6, minimum=0.1, maximum=10),
}
UPGRADES = {f'{row}.{level}': dict(spec, default=value, level=level, row=row)
            for row, spec in ROWS.items() for level, value in enumerate(spec['defaults'])}


def validate(values):
    if not isinstance(values, dict) or set(values) != set(UPGRADES):
        raise ValueError('Upgrades must contain all six levels of every supported benefit.')
    for key, value in values.items():
        spec = UPGRADES[key]
        if (type(value) not in (int, float) or not math.isfinite(value)
                or not spec['minimum'] <= value <= spec['maximum']
                or abs(value * 100 - round(value * 100)) > 1e-7):
            raise ValueError(f"{spec['name']}, level {spec['level']}: enter {spec['minimum']}–{spec['maximum']}, up to two decimal places.")
    return dict(values)


class UpgradesConfig(LimitsConfig):
    specs = UPGRADES
    schema = 'kknd2-editor-upgrades'
    value_key = 'upgrades'
    title = 'Upgrades'
    temporary_prefix = '.upgrades-'
    validate = staticmethod(validate)
