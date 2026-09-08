from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, mock
import json
import struct
import time
from support import editor, SOURCE, make_editor
from kknd2_editor import building_limits as limits
from kknd2_editor import game_launcher as launcher


class LimitsTests(TestCase):
    def test_roundtrip_undo_defaults_and_no_backup_files(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / 'building_limits.cfg'
            doc = limits.LimitsConfig(path)
            self.assertFalse(path.exists())
            changed = dict(doc.values, UNIT_SURV_TOWER1=12, UNIT_ROBOT_POWERSTATION=8)
            doc.apply(changed)
            doc.undo()
            self.assertEqual(doc.values, doc.defaults)
            doc.redo()
            self.assertEqual(doc.values, changed)
            doc.save()
            self.assertEqual(limits.LimitsConfig(path).values, changed)
            doc.apply(doc.defaults)
            doc.save()
            self.assertEqual(list(Path(folder).iterdir()), [path])
            self.assertEqual(limits.LimitsConfig(path).values, doc.defaults)

    def test_invalid_schema_and_limits_are_rejected(self):
        defaults = {k:s['default'] for k,s in limits.BUILDINGS.items()}
        for value in (-1, 0, 101, 1.5, True, '4'):
            with self.assertRaises(ValueError):
                limits.validate(dict(defaults, UNIT_SURV_TOWER1=value))
        for key, value in [('UNIT_SURV_MACHINESHOP', 5), ('UNIT_MUTE_BARRACKS', 8), ('UNIT_TEMPLE', 1)]:
            with self.assertRaises(ValueError):
                limits.validate(dict(defaults, **{key:value}))
        with TemporaryDirectory() as folder:
            path = Path(folder)/'building_limits.cfg'
            for raw in ('{}', '{"version":1,"version":1}', '{"schema":"kknd2-editor-building-limits","version":2,"limits":{}}'):
                path.write_text(raw)
                with self.assertRaises(ValueError):
                    limits.LimitsConfig(path)

    def test_external_changes_and_failed_save_preserve_original(self):
        with TemporaryDirectory() as folder:
            path = Path(folder)/'building_limits.cfg'
            doc = limits.LimitsConfig(path)
            doc.save()
            raw = path.read_bytes()
            doc.apply(dict(doc.values, UNIT_SURV_TOWER1=8))
            with mock.patch.object(limits.os, 'replace', side_effect=PermissionError('locked')):
                with self.assertRaises(OSError):
                    doc.save()
            self.assertEqual(path.read_bytes(), raw)
            self.assertEqual(doc.values['UNIT_SURV_TOWER1'], 8)
            path.write_bytes(raw + b'\n')
            with self.assertRaises(OSError):
                doc.save()

    def test_patch_plan_validates_all_memory_before_writing(self):
        memory = {s['address']:struct.pack('<H',s['default']) for s in limits.BUILDINGS.values()}
        defaults = {k:s['default'] for k,s in limits.BUILDINGS.items()}
        modified = dict(defaults, UNIT_SURV_TOWER1=12, UNIT_ROBOT_TOWER1=6)
        writes = []
        def write(a,b):
            writes.append((a,b))
            memory[a] = b
        self.assertEqual(launcher.apply_limits(lambda a,n:memory[a],write,modified), 2)
        self.assertTrue(all(len(b)==2 for a,b in writes))
        self.assertEqual(len(set(s['address'] for s in limits.BUILDINGS.values())), len(limits.BUILDINGS))
        writes.clear()
        with self.assertRaises(ValueError):
            launcher.apply_limits(lambda a,n:memory[a],write,modified)
        self.assertEqual(writes, [])

    def test_unsupported_executable_cannot_launch(self):
        with TemporaryDirectory() as folder:
            exe=Path(folder)/'KWIPv3.exe'
            exe.write_bytes(b'not the verified game')
            with self.assertRaisesRegex(ValueError, 'Unsupported'):
                launcher.launch_game(exe, {k:s['default'] for k,s in limits.BUILDINGS.items()})


class LimitsGuiTests(TestCase):
    def test_live_resize_and_original_row_spacing(self):
        with TemporaryDirectory() as folder:
            app=make_editor(limits_path=Path(folder)/'limits.cfg')
            try:
                app.update()
                for width in range(1000,1100,10):
                    app.geometry(f'{width}x800')
                    app.update()
                    self.assertTrue(app.stats.canvas.winfo_ismapped())
                app.update()
                stat_labels=[w for w in app.stats.content.winfo_children()
                             if w.grid_info().get('column') == 0 and w.grid_info().get('row') == 1]
                self.assertIn('\n',stat_labels[0].cget('text'))
                self.assertEqual(stat_labels[0].grid_info()['pady'], app.px(7))
            finally:
                app.destroy()

    def test_tab_edit_save_reset_and_launcher(self):
        with TemporaryDirectory() as folder:
            folder = Path(folder)
            cfg=folder/'UCONFIG_02.cfg'
            cfg.write_bytes(SOURCE.read_bytes())
            settings=folder/'building_limits.cfg'
            app=make_editor(folder, cfg, limits_path=settings, game_dir=folder)
            app.withdraw()
            try:
                app.update()
                page=app.limits_page
                app.notebook.select(page)
                page.variables['UNIT_SURV_TOWER1'].set('12')
                self.assertTrue(page.dirty())
                self.assertEqual(page.labels['UNIT_SURV_TOWER1'][1].cget('text'), '+8')
                app.active_action('save')
                self.assertEqual(limits.LimitsConfig(settings).values['UNIT_SURV_TOWER1'],12)
                page.reset()
                self.assertEqual(page.variables['UNIT_SURV_TOWER1'].get(),'4')
                page.undo()
                self.assertEqual(page.variables['UNIT_SURV_TOWER1'].get(),'12')
                with mock.patch.object(editor,'launch_game',return_value={'pid':1,'patched':1}) as launched:
                    app.launch()
                    deadline=time.monotonic()+3
                    while app.launching and time.monotonic()<deadline:
                        app.update()
                        time.sleep(.01)
                    self.assertFalse(app.launching)
                    self.assertEqual(launched.call_args.args[1]['UNIT_SURV_TOWER1'],12)
                    self.assertIn('Select UCONFIG_02.cfg',app.status.get())
                page.variables['UNIT_SURV_TOWER1'].set('101')
                with mock.patch.object(editor,'launch_game') as launched, mock.patch.object(editor.messagebox,'showerror'):
                    app.launch()
                    launched.assert_not_called()
            finally:
                app.destroy()

    def test_building_page_fields_reachable_at_high_dpi(self):
        with TemporaryDirectory() as folder:
            for dpi in (1,1.5,2,2.5):
                app=make_editor(tk_scaling=96/72*dpi,limits_path=Path(folder)/'limits.cfg')
                try:
                    app.minsize(1,1)
                    app.geometry('1050x760')
                    app.notebook.select(app.limits_page)
                    app.update()
                    page=app.limits_page
                    self.assertGreater(page.panel.canvas.winfo_height(),25)
                    for entry in page.entries.values():
                        page.panel.reveal(entry)
                        app.update()
                        self.assertGreaterEqual(entry.winfo_rooty(),page.panel.canvas.winfo_rooty()-2)
                        self.assertLessEqual(entry.winfo_rooty()+entry.winfo_height(),page.panel.canvas.winfo_rooty()+page.panel.canvas.winfo_height()+2)
                    self.assertTrue(app.launch_button.winfo_ismapped())
                finally:
                    app.destroy()
