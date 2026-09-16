"""Responsive six-column benefits table with the shared settings actions."""
import tkinter as tk
from tkinter import ttk
from .limits_ui import LimitsPage
from .upgrades import ROWS, UPGRADES, UpgradesConfig, validate


class UpgradesPage(LimitsPage):
    specs, config_type = UPGRADES, UpgradesConfig
    title, filename, path_attribute = 'Upgrades', 'upgrades.cfg', 'upgrades_path'
    has_factions = False
    heading = 'BUILDING BENEFIT / TECH LEVEL'

    @staticmethod
    def variable_value(value): return f'{value:g}'
    format_value = variable_value

    @staticmethod
    def format_delta(old, value): return f'{value-old:+g}' if value != old else '0'

    def display_name(self, key):
        spec = self.specs[key]
        return f"{spec['name']} — level {spec['level']}"

    def parse_value(self, key):
        try: return float(self.variables[key].get())
        except ValueError: raise ValueError(self.display_name(key) + ': enter a number.') from None

    def _build(self):
        app = self.app
        controls = ttk.Frame(self)
        controls.grid(row=1, column=0, sticky='ew', pady=app.px(8))
        self.only_changed = tk.BooleanVar(value=False)
        ttk.Checkbutton(controls, text='Different from defaults', variable=self.only_changed,
                        command=self.filter).pack(side='left')
        ttk.Label(controls, text='Blue = unsaved; amber = different from default',
                  foreground='#666666').pack(side='left', padx=app.px(15))
        self.panel = self.scroll_panel(self, app.style.lookup('TFrame', 'background') or '#f0f0f0')
        self.panel.grid(row=2, column=0, sticky='nsew')
        grid = self.panel.content
        grid.columnconfigure(0, weight=1)
        ttk.Label(grid, text='BUILDING BENEFIT', foreground='#666666').grid(
            row=0, column=0, sticky='w', padx=app.px(7), pady=app.px(6))
        for level in range(6):
            ttk.Label(grid, text=f'LEVEL {level}', foreground='#666666').grid(
                row=0, column=level+1, padx=app.px(7), pady=app.px(6))
        self.variables, self.entries, self.rows, self.labels = {}, {}, {}, {}
        for row_number, (row, spec) in enumerate(ROWS.items(), 1):
            label = ttk.Label(grid, text=spec['name']+'\n'+spec['hint'], justify='left')
            label.grid(row=row_number, column=0, sticky='w', padx=app.px(7), pady=app.px(7))
            widgets = [label]
            for level in range(6):
                key = f'{row}.{level}'
                cell = ttk.Frame(grid)
                cell.grid(row=row_number, column=level+1, padx=app.px(7), pady=app.px(7))
                var = tk.StringVar(value=self.variable_value(self.doc.values[key]))
                entry = ttk.Spinbox(cell, from_=spec['minimum'], to=spec['maximum'], increment=0.05,
                                    width=7, textvariable=var)
                entry.pack()
                entry.bind('<FocusIn>', lambda _, e=entry: self.panel.reveal(e))
                comparison = ttk.Label(cell, foreground='#777777', justify='center')
                comparison.pack(pady=(app.px(2), 0))
                self.variables[key], self.entries[key], self.labels[key] = var, entry, comparison
                var.trace_add('write', lambda *_, k=key: self.refresh(k))
                widgets.append(cell)
            self.rows[row] = widgets
        self.note = ttk.Label(self, foreground='#666666', text=(
            'Each cell shows its default and difference (Δ); focus a cell to see its saved value and limits.\n'
            'All factions share these curves. Lab columns are destination levels; level 0 has no upgrade into it.'))
        self.note.grid(row=3, column=0, sticky='w', pady=app.px(6))
        self._show_note = True
        self.bind('<Configure>', self.resize_note)
        self.status = tk.StringVar()
        ttk.Label(self, textvariable=self.status).grid(row=4, column=0, sticky='w')
        self.actions = self.flow_bar(self, app.px(5))
        self.actions.grid(row=5, column=0, sticky='ew', pady=(app.px(8), 0))
        for label, command in [('Undo', self.undo), ('Redo', self.redo),
                               ('Revert saved', self.revert), ('Reset defaults', self.reset)]:
            self.actions.add(label, command)
        for key, entry in self.entries.items():
            entry.bind('<FocusIn>', lambda _, k=key: self.refresh(k), add='+')
        self.refresh_all()

    def refresh(self, key):
        spec, default, saved = self.specs[key], self.doc.defaults[key], self.doc.saved[key]
        try:
            value = self.parse_value(key)
            validate(dict(self.doc.defaults, **{key: value}))
            delta = self.format_delta(default, value)
            color = '#005ca8' if value != saved else '#986009' if value != default else '#000000'
        except ValueError:
            delta, color = 'invalid', '#bd2727'
        self.entries[key].configure(foreground=color)
        self.labels[key].configure(text=f'{default:g} | Δ {delta}', foreground='#bd2727' if delta == 'invalid' else '#777777')
        self.status.set(f"{self.doc.path.name} | {self.display_name(key)} | Saved {saved:g} | Allowed {spec['minimum']:g}–{spec['maximum']:g} | "
                        + ('Unsaved changes' if self.dirty() else 'Defaults ready — save to create file' if self.doc.raw is None else 'All changes saved'))

    def filter(self):
        for row, widgets in self.rows.items():
            show = not self.only_changed.get() or any(
                self.variables[f'{row}.{level}'].get() != self.variable_value(self.doc.defaults[f'{row}.{level}']) for level in range(6))
            for widget in widgets:
                widget.grid() if show else widget.grid_remove()
