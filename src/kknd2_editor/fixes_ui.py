"""Boolean settings, reusing the shared settings page and toolbar actions."""
import tkinter as tk
from tkinter import ttk
from .limits_ui import LimitsPage
from .fixes import FIXES, FixesConfig


class FixesPage(LimitsPage):
    specs = FIXES
    config_type = FixesConfig
    title = 'Fixes'
    filename = 'fixes.cfg'
    path_attribute = 'fixes_path'
    has_factions = False
    heading = 'FIX / BEHAVIOR'
    value_heading = 'ENABLED'
    note_text = ('Off preserves the original behavior. Changes apply on the next launch.\n'
                 'Targeting fixes apply to all players, including AI; multiplayer participants need matching settings.')

    def display_name(self, key):
        spec = self.specs[key]
        return spec['name'] + '\n' + spec['hint']

    def column_headings(self):
        return (self.heading, self.value_heading, 'DEFAULT', 'CHANGE', 'SAVED')

    @staticmethod
    def variable_value(value):
        return value

    @staticmethod
    def format_value(value):
        return 'On' if value else 'Off'

    @staticmethod
    def format_delta(old, value):
        return ('Enabled' if value else 'Disabled') if old != value else '—'

    def create_control(self, grid, key):
        self.app.style.configure('Unsaved.TCheckbutton', foreground='#005ca8')
        var = tk.BooleanVar(value=self.doc.values[key])
        return var, ttk.Checkbutton(grid, variable=var, text=self.format_value(var.get()))

    def parse_value(self, key):
        return self.variables[key].get()

    def refresh(self, key):
        value, default, saved = self.variables[key].get(), self.doc.defaults[key], self.doc.saved[key]
        self.entries[key].configure(text=self.format_value(value),
                                    style='Unsaved.TCheckbutton' if value != saved else 'TCheckbutton')
        labels = self.labels[key]
        labels[0].configure(text=self.format_value(default))
        labels[1].configure(text=self.format_delta(default, value), foreground='#986009' if value != default else '#777777')
        labels[2].configure(text=self.format_value(saved), foreground='#777777')
        self.status.set(self.doc.path.name + ' | ' + ('Unsaved changes' if self.dirty() else
                        'Defaults ready — save to create file' if self.doc.raw is None else 'All changes saved'))
