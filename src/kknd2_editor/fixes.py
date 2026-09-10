"""Opt-in behavior fixes. False means the original game's behavior."""
from .building_limits import LimitsConfig

FIXES = {
    'shift_build': dict(default=False, name='Shift build',
        hint='Hold Shift when placing a building to keep that building selected.\n'
             'Click again to place another; placement ends when it becomes unavailable.'),
    'zero_damage_filter': dict(default=False, name='Zero damage acts as a target filter',
        hint='Reject target types against which the current weapon deals zero damage.\n'
             'Applies to automatic targeting and attack checks, including targets out of range.'),
    'damage_priority': dict(default=False, name='Prioritize target types by damage',
        hint='Choose valid target types from highest to lowest weapon damage.\n'
             'Equal damage keeps the game’s selection rules; explicit target orders keep priority.'),
}


def validate(values):
    if not isinstance(values, dict) or set(values) != set(FIXES):
        raise ValueError('Fixes must contain exactly the three supported settings.')
    for key, value in values.items():
        if type(value) is not bool:
            raise ValueError(f'{FIXES[key]["name"]}: use true or false.')
    return dict(values)


class FixesConfig(LimitsConfig):
    specs = FIXES
    schema = 'kknd2-editor-fixes'
    value_key = 'fixes'
    title = 'Fixes'
    temporary_prefix = '.fixes-'
    validate = staticmethod(validate)
