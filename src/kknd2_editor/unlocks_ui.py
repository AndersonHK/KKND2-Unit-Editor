from .limits_ui import LimitsPage
from .tech_unlocks import UnlocksConfig, UNLOCKS


class UnlocksPage(LimitsPage):
    specs = UNLOCKS
    config_type = UnlocksConfig
    title = 'Tech unlocks'
    filename = 'tech_unlocks.cfg'
    path_attribute = 'unlocks_path'
    heading = 'UNIT / BUILDING / PREREQUISITE'
    value_heading = 'TECH LEVEL'
    note_text = ('Levels 0–5 refer to the listed production building; level 0 needs no research. Other prerequisites still apply.\n'
                 'Drill Rigs deploy from Mobile Drill Rigs; the Scourge Demon uses the Altar. They have no independent tier here.')

    def display_name(self, key):
        return super().display_name(key) + '\nRequires: ' + self.specs[key]['producer']
