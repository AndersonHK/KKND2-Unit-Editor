"""Building limits page; no game config parsing or writes in this module."""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
from .building_limits import BUILDINGS, LimitsConfig


class LimitsPage(ttk.Frame):
    def __init__(self, app, parent, path, names, scroll_panel, flow_bar):
        super().__init__(parent, padding=app.px(8))
        self.app, self.names = app, names
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)
        self.error = None
        self.scroll_panel, self.flow_bar = scroll_panel, flow_bar
        try:
            self.doc = LimitsConfig(path)
        except (OSError, ValueError) as exc:
            self.error = str(exc)
            self.doc = None
            ttk.Label(self, text='Cannot load building_limits.cfg: ' + self.error,
                      foreground='#bd2727', wraplength=600).grid(sticky='w')
            return
        self._build()

    def _build(self):
        app, names = self.app, self.names
        scroll_panel, flow_bar = self.scroll_panel, self.flow_bar
        controls = ttk.Frame(self)
        controls.grid(row=1, column=0, sticky='ew', pady=app.px(8))
        self.faction = tk.StringVar(value='All factions')
        combo = ttk.Combobox(controls, textvariable=self.faction, state='readonly', width=16,
                             values=('All factions', 'Survivors', 'Evolved', 'Series 9'))
        combo.pack(side='left')
        combo.bind('<<ComboboxSelected>>', lambda _: self.filter())
        self.only_changed = tk.BooleanVar(value=False)
        ttk.Checkbutton(controls, text='Different from defaults', variable=self.only_changed,
                        command=self.filter).pack(side='left', padx=app.px(8))
        self.panel = scroll_panel(self, app.style.lookup('TFrame', 'background') or '#f0f0f0')
        self.panel.grid(row=2, column=0, sticky='nsew')
        grid = self.panel.content
        grid.columnconfigure(0, weight=1)
        for col, label in enumerate(('BUILDING / FACTION', 'LIMIT', 'DEFAULT', 'DELTA', 'SAVED', 'ALLOWED')):
            ttk.Label(grid, text=label, foreground='#666666').grid(row=0, column=col, sticky='w', padx=app.px(7), pady=app.px(6))
        self.variables, self.entries, self.rows, self.labels = {}, {}, {}, {}
        for row, (key, spec) in enumerate(BUILDINGS.items(), 1):
            faction = self.faction_name(key)
            widgets = []
            label = ttk.Label(grid, text=names[key] + ' / ' + faction)
            label.grid(row=row, column=0, sticky='w', padx=app.px(7))
            widgets.append(label)
            var = tk.StringVar(value=str(self.doc.values[key]))
            entry = ttk.Spinbox(grid, from_=1, to=spec['maximum'], width=6, textvariable=var)
            entry.grid(row=row, column=1, padx=app.px(7), pady=app.px(3))
            if key == 'UNIT_TEMPLE':
                entry.configure(state='disabled')
            entry.bind('<FocusIn>', lambda _, e=entry: self.panel.reveal(e))
            widgets.append(entry)
            labels = []
            for col in range(2, 6):
                item = ttk.Label(grid, width=9, anchor='e')
                item.grid(row=row, column=col, sticky='e', padx=app.px(7))
                widgets.append(item)
                labels.append(item)
            labels[3].configure(text='Special' if key == 'UNIT_TEMPLE' else f"1–{spec['maximum']}")
            self.variables[key], self.entries[key], self.rows[key], self.labels[key] = var, entry, widgets, labels
            var.trace_add('write', lambda *_, k=key: self.refresh(k))
        self.note = ttk.Label(self, text='Limits apply per player and faction when launched here. Machine Shops: max 4; Barracks: max 7.\n'
                             'Other controls are capped at 100; game-wide unit caps still apply. The Altar uses special game logic.',
                             foreground='#666666')
        self.note.grid(row=3, column=0, sticky='w', pady=app.px(6))
        self._show_note = True
        self.bind('<Configure>', self.resize_note)
        self.status = tk.StringVar()
        ttk.Label(self, textvariable=self.status).grid(row=4, column=0, sticky='w')
        self.actions = flow_bar(self, app.px(5))
        self.actions.grid(row=5, column=0, sticky='ew', pady=(app.px(8), 0))
        for label, command in [('Undo', self.undo), ('Redo', self.redo),
                               ('Revert saved', self.revert), ('Reset defaults', self.reset)]:
            self.actions.add(label, command)
        self.refresh_all()

    def resize_note(self, event):
        show = event.height >= self.app.px(450)
        if show != self._show_note:
            self._show_note = show
            self.note.grid() if show else self.note.grid_remove()

    @staticmethod
    def faction_name(key):
        return 'Survivors' if '_SURV_' in key else 'Series 9' if '_ROBOT_' in key else 'Evolved'

    def refresh(self, key):
        text = self.variables[key].get()
        labels = self.labels[key]
        original, default = self.doc.saved[key], self.doc.defaults[key]
        try:
            if not text.isascii() or not text.isdigit():
                raise ValueError()
            value = int(text)
            spec = BUILDINGS[key]
            if not (0 if spec['default'] == 0 else 1) <= value <= spec['maximum']:
                raise ValueError()
            delta = value - default
            labels[1].configure(text=f'{delta:+d}' if delta else '0', foreground='#986009' if delta else '#777777')
            self.entries[key].configure(foreground='#005ca8' if value != original else '#000000')
        except ValueError:
            labels[1].configure(text='invalid', foreground='#bd2727')
            self.entries[key].configure(foreground='#bd2727')
        labels[0].configure(text=str(default))
        labels[2].configure(text=str(original))
        dirty = self.dirty()
        self.status.set(self.doc.path.name + ' | ' + ('Unsaved changes' if dirty else 'All changes saved'))

    def refresh_all(self):
        for key in self.variables:
            self.variables[key].set(str(self.doc.values[key]))
        self.filter()

    def dirty(self):
        return self.doc is not None and any(v.get() != str(self.doc.saved[k]) for k, v in self.variables.items())

    def commit(self):
        if self.error:
            messagebox.showerror('Building limits unavailable', self.error, parent=self.app)
            return False
        try:
            values = {}
            for key, var in self.variables.items():
                if not var.get().isascii() or not var.get().isdigit():
                    raise ValueError(f'{self.names[key]}: enter a whole number.')
                values[key] = int(var.get())
            self.doc.apply(values)
            return True
        except ValueError as exc:
            messagebox.showerror('Invalid building limit', str(exc), parent=self.app)
            return False

    def save(self):
        if not self.commit():
            return False
        try:
            self.doc.save()
        except (OSError, ValueError) as exc:
            messagebox.showerror('Cannot save building limits', str(exc), parent=self.app)
            return False
        self.refresh_all()
        return True

    def undo(self):
        if self.commit():
            self.doc.undo()
            self.refresh_all()

    def redo(self):
        if self.commit():
            self.doc.redo()
            self.refresh_all()

    def revert(self):
        if self.commit():
            self.doc.apply(self.doc.saved)
            self.refresh_all()

    def reset(self):
        if self.commit():
            self.doc.apply(self.doc.defaults)
            self.refresh_all()

    def filter(self):
        for key, widgets in self.rows.items():
            show = (self.faction.get() == 'All factions' or self.faction.get() == self.faction_name(key)) and (
                not self.only_changed.get() or self.variables[key].get() != str(self.doc.defaults[key]))
            for widget in widgets:
                widget.grid() if show else widget.grid_remove()

    def review_defaults(self):
        self.review(True)

    def can_leave(self):
        if not self.dirty():
            return True
        choice = messagebox.askyesnocancel('Unsaved building limits',
                                          'Save building limits before opening another configuration?', parent=self.app)
        return self.save() if choice is True else choice is False

    def load_file(self, path):
        try:
            candidate = LimitsConfig(path)
        except (OSError, ValueError) as exc:
            messagebox.showerror('Cannot open building limits', str(exc), parent=self.app)
            return False
        if not self.can_leave():
            return False
        # The save/discard decision can change the selected file's disk contents.
        try:
            candidate = LimitsConfig(path)
        except (OSError, ValueError) as exc:
            messagebox.showerror('Cannot open building limits', str(exc), parent=self.app)
            return False
        rebuild = self.error is not None
        self.doc, self.error = candidate, None
        self.app.limits_path = candidate.path
        if rebuild:
            for widget in self.winfo_children():
                widget.destroy()
            self._build()
        else:
            self.refresh_all()
        if not self.app.launching:
            self.app.launch_button.configure(state='normal')
        return True

    def open_file(self):
        initial = self.doc.path.parent if self.doc is not None else self.app.limits_path.parent
        chosen = filedialog.askopenfilename(parent=self.app, initialdir=initial,
                                            title='Open building limits', filetypes=[('Building limits', '*.cfg')])
        if chosen:
            self.load_file(chosen)

    def open_folder(self):
        initial = self.doc.path.parent if self.doc is not None else self.app.limits_path.parent
        chosen = filedialog.askdirectory(parent=self.app, initialdir=initial, title='Building limits folder')
        if chosen:
            self.load_file(Path(chosen) / 'building_limits.cfg')

    def review(self, defaults=False):
        if not self.commit():
            return
        window = tk.Toplevel(self.app)
        window.title('Building limits — ' + ('Differences from defaults' if defaults else 'Unsaved changes'))
        self.app.fit_window(window, 800, 500)
        panel = ttk.Frame(window, padding=self.app.px(10))
        panel.pack(fill='both', expand=True)
        panel.rowconfigure(0, weight=1)
        panel.columnconfigure(0, weight=1)
        table = ttk.Treeview(panel, columns=('name', 'old', 'new', 'delta'), show='headings')
        for key, label, width in [('name', 'Building / faction', 350), ('old', 'Default' if defaults else 'Saved', 90), ('new', 'Current', 90), ('delta', 'Delta', 90)]:
            table.heading(key, text=label)
            table.column(key, width=self.app.px(width), minwidth=self.app.px(width))
        table.grid(row=0, column=0, sticky='nsew')
        ttk.Scrollbar(panel, command=table.yview).grid(row=0, column=1, sticky='ns')
        vertical = panel.grid_slaves(row=0, column=1)[0]
        table.configure(yscrollcommand=vertical.set)
        horizontal = ttk.Scrollbar(panel, orient='horizontal', command=table.xview)
        horizontal.grid(row=1, column=0, sticky='ew')
        table.configure(xscrollcommand=horizontal.set)
        old = self.doc.defaults if defaults else self.doc.saved
        for key, value in self.doc.values.items():
            if value != old[key]:
                table.insert('', 'end', values=(self.names[key] + ' / ' + self.faction_name(key), old[key], value, f'{value-old[key]:+d}'))
