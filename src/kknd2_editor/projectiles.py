"""Absolute projectile settings, saved separately from native unit configurations."""
from .building_limits import LimitsConfig
from .projectile_data import PROJECTILES

FIELDS = {}
for key, projectile in PROJECTILES.items():
    if projectile['speed'] is not None:
        # Several flight routines divide by speed >> 4. Values below 16 divide by zero.
        FIELDS[key + '.speed'] = dict(name=projectile['name'] + ' / Speed',
            default=projectile['speed'], minimum=16, maximum=2048)
    if projectile['lifetime'] is not None:
        FIELDS[key + '.lifetime'] = dict(name=projectile['name'] + ' / Expiration',
            default=projectile['lifetime'], minimum=1, maximum=255)


def validate(values):
    if not isinstance(values, dict) or set(values) != set(FIELDS):
        raise ValueError('Projectiles must contain exactly the supported speed and expiration IDs.')
    for key, value in values.items():
        spec = FIELDS[key]
        if type(value) is not int or not spec['minimum'] <= value <= spec['maximum']:
            raise ValueError(f"{spec['name']}: enter a whole number from {spec['minimum']} to {spec['maximum']}.")
    return dict(values)


class ProjectilesConfig(LimitsConfig):
    specs = FIELDS
    schema = 'kknd2-editor-projectiles'
    value_key = 'projectiles'
    title = 'Projectiles'
    temporary_prefix = '.projectiles-'
    validate = staticmethod(validate)
