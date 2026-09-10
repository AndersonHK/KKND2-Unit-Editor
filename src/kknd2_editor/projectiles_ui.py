"""Projectile browser with the same settings actions and comparisons as other tabs."""
import tkinter as tk
from tkinter import ttk
from .limits_ui import LimitsPage
from .projectiles import FIELDS, ProjectilesConfig
from .projectile_data import PROJECTILES


class ProjectilesPage(LimitsPage):
    specs = FIELDS
    config_type = ProjectilesConfig
    title = 'Projectiles'
    filename = 'projectiles.cfg'
    path_attribute = 'projectiles_path'
    heading = 'PROJECTILE / FIELD'

    def display_name(self, key):
        return self.specs[key]['name']

    def _build(self):
        app, p = self.app, self.app.px
        self.selected = None
        self._refreshing = True
        self.body = ttk.Frame(self)
        self.body.grid(row=2, column=0, sticky='nsew')
        self.body.columnconfigure(0, weight=0, minsize=p(300))
        self.body.columnconfigure(1, weight=1)
        self.body.rowconfigure(0, weight=1)
        left = ttk.Frame(self.body)
        left.grid(row=0, column=0, sticky='nsew', padx=(0, p(12)))
        left.columnconfigure(0, weight=1)
        left.rowconfigure(3, weight=1)
        self.search = tk.StringVar()
        search = ttk.Entry(left, textvariable=self.search)
        search.grid(row=0, column=0, columnspan=2, sticky='ew', pady=(0, p(6)))
        self.search.trace_add('write', lambda *_: self.filter())
        self.faction = tk.StringVar(value='All factions')
        combo = ttk.Combobox(left, textvariable=self.faction, state='readonly',
                            values=('All factions', 'Survivors', 'Evolved', 'Series 9'))
        combo.grid(row=1, column=0, columnspan=2, sticky='ew', pady=(0, p(6)))
        combo.bind('<<ComboboxSelected>>', lambda _: self.filter())
        self.only_changed = tk.BooleanVar()
        ttk.Checkbutton(left, text='Different from defaults', variable=self.only_changed,
                        command=self.filter).grid(row=2, column=0, columnspan=2, sticky='w', pady=(0, p(6)))
        self.tree = ttk.Treeview(left, columns=('faction',), show='tree headings', selectmode='browse')
        self.tree.heading('#0', text='Projectile (* unsaved, ~ modified)')
        self.tree.heading('faction', text='Faction')
        self.tree.column('#0', width=p(265), minwidth=p(180))
        self.tree.column('faction', width=p(95), minwidth=p(80), stretch=False)
        self.tree.grid(row=3, column=0, sticky='nsew')
        vertical = ttk.Scrollbar(left, command=self.tree.yview)
        vertical.grid(row=3, column=1, sticky='ns')
        horizontal = ttk.Scrollbar(left, orient='horizontal', command=self.tree.xview)
        horizontal.grid(row=4, column=0, sticky='ew')
        self.tree.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        self.tree.bind('<<TreeviewSelect>>', self.select_projectile)
        right = ttk.Frame(self.body)
        right.grid(row=0, column=1, sticky='nsew')
        right.columnconfigure(0, weight=1)
        right.rowconfigure(2, weight=1)
        self.selection_title = ttk.Label(right, style='Title.TLabel')
        self.selection_title.grid(row=0, column=0, sticky='w', pady=(0, p(8)))
        self.description = ttk.Label(right, justify='left', wraplength=p(650))
        self.description.grid(row=1, column=0, sticky='ew', pady=(0, p(12)))
        self.panel = self.scroll_panel(right, app.style.lookup('TFrame', 'background') or '#f0f0f0')
        self.panel.grid(row=2, column=0, sticky='nsew')
        grid = self.panel.content
        grid.columnconfigure(0, weight=1)
        for column, text in enumerate(('STAT', 'VALUE', 'DEFAULT', 'DELTA', 'SAVED', 'ALLOWED')):
            ttk.Label(grid, text=text, foreground='#666666').grid(row=0, column=column, sticky='e' if column else 'w', padx=p(7), pady=p(6))
        self.variables, self.entries, self.rows, self.labels = {}, {}, {}, {}
        hints = {'speed': '1/256 world pixel per velocity step',
                 'lifetime': 'Homing updates (game-speed dependent)'}
        for key, spec in self.specs.items():
            field = key.rsplit('.', 1)[1]
            row = 1 if field == 'speed' else 2
            label = ttk.Label(grid, text=('Speed' if field == 'speed' else 'Expiration time') + '\n' + hints[field], justify='left')
            label.grid(row=row, column=0, sticky='w', padx=p(7), pady=p(12))
            var = tk.StringVar(value=str(self.doc.values[key]))
            entry = ttk.Spinbox(grid, from_=spec['minimum'], to=spec['maximum'], width=9, textvariable=var)
            entry.grid(row=row, column=1, padx=p(7), pady=p(8))
            entry.bind('<FocusIn>', lambda _, e=entry: self.panel.reveal(e))
            labels = []
            for column in range(2, 6):
                item = ttk.Label(grid, width=9, anchor='e')
                item.grid(row=row, column=column, sticky='e', padx=p(7))
                labels.append(item)
            labels[3].configure(text=f"{spec['minimum']:,}–{spec['maximum']:,}")
            self.variables[key], self.entries[key] = var, entry
            self.rows[key], self.labels[key] = [label, entry] + labels, labels
            var.trace_add('write', lambda *_, k=key: self.refresh(k))
        self.empty = ttk.Label(grid, text='No editable travel speed or fixed expiration for this effect.', foreground='#666666')
        self.empty.grid(row=3, column=0, columnspan=6, sticky='w', pady=p(12))
        self.note = ttk.Label(self, text='Speed changes can affect collision and accuracy. Expiration is a maximum lifetime, not a guaranteed flight time.', foreground='#666666')
        self.note.grid(row=3, column=0, sticky='w', pady=p(6))
        self._show_note = True
        self.status = tk.StringVar()
        ttk.Label(self, textvariable=self.status).grid(row=4, column=0, sticky='w')
        self.actions = self.flow_bar(self, p(5))
        self.actions.grid(row=5, column=0, sticky='ew', pady=(p(8), 0))
        for text, command in (('Undo', self.undo), ('Redo', self.redo), ('Revert saved', self.revert), ('Reset defaults', self.reset)):
            self.actions.add(text, command)
        right.bind('<Configure>', self.resize_details)
        self.bind('<Configure>', self.resize_note)
        self.refresh_all()

    def resize_details(self, event):
        width = max(self.app.px(260), event.width - self.app.px(12))
        if width != getattr(self, '_wrap', None):
            self._wrap = width
            self.description.configure(wraplength=width)

    def refresh(self, key):
        super().refresh(key)
        if not self._refreshing:
            projectile = key.rsplit('.', 1)[0]
            if self.tree.exists(projectile):
                self.tree.item(projectile, text=self.item_text(projectile))

    def refresh_all(self):
        self._refreshing = True
        super().refresh_all()
        self._refreshing = False

    def item_text(self, key):
        keys = [k for k in self.variables if k.startswith(key + '.')]
        dirty = any(self.variables[k].get() != str(self.doc.saved[k]) for k in keys)
        modified = any(self.variables[k].get() != str(self.doc.defaults[k]) for k in keys)
        return ('* ' if dirty else '~ ' if modified else '') + PROJECTILES[key]['name']

    def filter(self):
        if not hasattr(self, 'tree'):
            return
        query = self.search.get().casefold().strip()
        visible = []
        for key, projectile in PROJECTILES.items():
            keys = [k for k in self.variables if k.startswith(key + '.')]
            changed = any(self.variables[k].get() != str(self.doc.defaults[k]) for k in keys)
            if (self.faction.get() in ('All factions', projectile['faction']) and
                    (not self.only_changed.get() or changed) and
                    query in (key + ' ' + projectile['name'] + ' ' + ' '.join(projectile['units'])).casefold()):
                visible.append(key)
        self.tree.delete(*self.tree.get_children())
        for key in visible:
            self.tree.insert('', 'end', iid=key, text=self.item_text(key), values=(PROJECTILES[key]['faction'],))
        self.selected = self.selected if self.selected in visible else next(iter(visible), None)
        if self.selected:
            self.tree.selection_set(self.selected)
            self.tree.see(self.selected)
        self.show_projectile()

    def select_projectile(self, _event=None):
        selected = self.tree.selection()
        if selected:
            self.selected = selected[0]
        self.show_projectile()

    def show_projectile(self):
        for key, widgets in self.rows.items():
            show = self.selected is not None and key.startswith(self.selected + '.')
            for widget in widgets:
                widget.grid() if show else widget.grid_remove()
        if not self.selected:
            self.selection_title.configure(text='No matching projectiles')
            self.description.configure(text='Change the search or filters to see projectiles.')
            self.empty.grid_remove()
            return
        p = PROJECTILES[self.selected]
        self.selection_title.configure(text=p['name'] + ' / ' + p['faction'])
        from .app import UNIT_NAMES
        text = 'Used by: ' + ', '.join(UNIT_NAMES.get(u, u) for u in p['units']) + '.\n'
        if p['speed'] is not None:
            text += 'Game speed scales projectile motion. '
        if p['lifetime'] is not None:
            text += 'Fixed expiration is independent of weapon range. Each missile type can have its own timer.\nA lost target or an impact can end the flight earlier.'
        elif p['speed'] is not None:
            text += 'Flight ends at the calculated destination or impact; this handler has no fixed expiration setting.'
        else:
            text += 'This effect uses instant hits or specialized motion. A generic travel-speed field would not control it.'
        self.description.configure(text=text)
        self.empty.grid() if p['speed'] is None else self.empty.grid_remove()

    def selected_reset(self, baseline):
        if self.selected and self.commit():
            self.doc.apply({k: baseline[k] if k.startswith(self.selected + '.') else v for k, v in self.doc.values.items()})
            self.refresh_all()

    def reset(self):
        self.selected_reset(self.doc.defaults)

    def revert(self):
        self.selected_reset(self.doc.saved)
