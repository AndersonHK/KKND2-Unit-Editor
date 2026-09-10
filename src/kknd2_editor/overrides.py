"""Absolute KWIPv3 settings. Defaults are embedded; personal files are not shipped."""
from .building_limits import LimitsConfig

OVERRIDES = {
    'research_cost': dict(name='Base research cost', default=250, minimum=50, maximum=10000,
                         hint='Resource units (RU), before tier surcharge'),
    'research_time': dict(name='Base research time', default=20, minimum=1, maximum=600,
                         hint='Seconds before speed scaling (nominal)'),
    'research_cost_step': dict(name='Research cost step', default=20, minimum=0, maximum=1000,
                              hint='Extra RU per tier below research index 5'),
    'research_time_step': dict(name='Research time step', default=1, minimum=0, maximum=40,
                              hint='Extra nominal seconds per lower tier'),
    'tanker_capacity': dict(name='Tanker capacity', default=400, minimum=1, maximum=10000,
                           hint='Oil units carried; refining changes RU payout'),
    'rig_loading_rate': dict(name='Rig loading rate', default=32768, minimum=1, maximum=1048576,
                            hint='1/32,768 oil per load update at speed 512'),
    'powerplant_unloading_rate': dict(name='Powerplant unloading rate', default=4096, minimum=512, maximum=1048576,
                                    hint='1/128 RU per unload opportunity at speed 512'),
    'solar_income': dict(name='Solar-class income', default=7, minimum=0, maximum=10000,
                         hint='RU per payout per building; all three factions'),
    'thermal_income': dict(name='Thermal-class income', default=21, minimum=0, maximum=10000,
                           hint='RU per payout per building; all three factions'),
    'building_placement_range': dict(name='Building placement reach', default=5, minimum=1, maximum=32,
                                    hint='Tile-cell reach from footprint; 5 allows four clear tiles'),
}


V1_KEYS = frozenset(OVERRIDES) - {'solar_income', 'thermal_income', 'building_placement_range'}

def validate(values):
    if not isinstance(values, dict) or set(values) != set(OVERRIDES):
        raise ValueError('Overrides must contain exactly the supported setting IDs.')
    for key, value in values.items():
        spec = OVERRIDES[key]
        if type(value) is not int or not spec['minimum'] <= value <= spec['maximum']:
            raise ValueError(f"{spec['name']}: enter a whole number from {spec['minimum']:,} to {spec['maximum']:,}.")
    return dict(values)


class OverridesConfig(LimitsConfig):
    version = 2
    specs = OVERRIDES
    schema = 'kknd2-editor-overrides'
    value_key = 'overrides'
    title = 'Overrides'
    temporary_prefix = '.overrides-'
    validate = staticmethod(validate)

    def decode_values(self, values, version):
        if version == 1:
            if not isinstance(values, dict) or set(values) != V1_KEYS:
                raise ValueError('Version 1 overrides must contain exactly the original seven settings.')
            return self.validate(dict(self.defaults, **values))
        return super().decode_values(values, version)
