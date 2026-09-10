"""Raw engine overrides using the same settings-page controls as building limits."""
from .limits_ui import LimitsPage
from .overrides import OVERRIDES, OverridesConfig
from tkinter import ttk


class OverridesPage(LimitsPage):
    specs = OVERRIDES
    config_type = OverridesConfig
    title = 'Overrides'
    filename = 'overrides.cfg'
    path_attribute = 'overrides_path'
    has_factions = False
    heading = 'SETTING / RAW UNITS'
    value_heading = 'VALUE'
    note_text = ('Absolute values apply when launched here, including defaults. Research tiers use base + (5 - index) × step.\n'
                 'Transfer rates are raw constants, not percentages. Timing depends on game speed and transfer scheduling.')

    def display_name(self, key):
        return self.specs[key]['name'] + '\n' + self.specs[key]['hint']

    def section_before(self, grid, row, key):
        sections = {
            'research_cost': ('Research',
                'Cost: base cost + (5 - tier index) × cost step\n'
                'Time: base time + (5 - tier index) × time step\n'
                'The research lab supplies the tier index, from 0–5. A zero step removes that surcharge.\n'
                'Time is nominal seconds before speed scaling: at speed 512 / 60 Hz, 20 is about 10 seconds.\n'
                'At speed 256 it is about 20 seconds. Rounding and resource shortages affect completion time.'),
            'tanker_capacity': ('Oil and Tankers',
                'Capacity is raw oil carried by a tanker. Refining upgrades can change its resource payout.\n'
                'Load increment: game speed × loading constant / 65,536, in 1/256-oil units; fractions round down.\n'
                'Unload amount: game speed × unloading constant / 65,536, in resource units.\n'
                'Solar and thermal payouts are shared across factions, about every 3 seconds at speed 512 / 60 Hz.'),
            'building_placement_range': ('Building Placement',
                'Reach is measured on the tile grid around the new footprint, including diagonals.\n'
                'Default 5 permits up to four clear tiles between occupied footprints. Advanced walls retain one extra tile.\n'
                'Terrain, ownership, building limits and eligible base-building checks still apply.'),
        }
        if key not in sections:
            return row
        if not hasattr(self, 'section_labels'):
            self.section_labels = []
        title, explanation = sections[key]
        ttk.Label(grid, text=title, style='Title.TLabel').grid(row=row, column=0, columnspan=6,
            sticky='w', padx=self.app.px(7), pady=(self.app.px(18), self.app.px(5)))
        label = ttk.Label(grid, text=explanation, justify='left', wraplength=self.app.px(750))
        label.grid(row=row+1, column=0, columnspan=6, sticky='w', padx=self.app.px(7), pady=(0, self.app.px(10)))
        self.section_labels.append(label)
        return row + 2

    def resize_note(self, event):
        super().resize_note(event)
        width = max(self.app.px(250), ((event.width - self.app.px(50)) // 32) * 32)
        if width != getattr(self, '_section_wrap', None):
            self._section_wrap = width
            for label in getattr(self, 'section_labels', ()):
                if label.winfo_exists():
                    label.configure(wraplength=width)
