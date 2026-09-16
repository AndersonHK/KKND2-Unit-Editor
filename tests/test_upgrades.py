import json
import struct
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, mock
from support import make_editor
from kknd2_editor import upgrades, upgrades_patch, fixes, game_launcher, building_limits, overrides


def settings(**changes):
    return dict({key: s['default'] for key, s in upgrades.UPGRADES.items()}, **changes)


class UpgradeTests(TestCase):
    def test_schema_defaults_decimal_history_atomic_save(self):
        with TemporaryDirectory() as folder:
            path = Path(folder)/'upgrades.cfg'
            doc = upgrades.UpgradesConfig(path)
            self.assertEqual(len(doc.values), 42)
            self.assertFalse(path.exists())
            doc.apply(settings(**{'lab_upgrade.5': 2, 'infantry_speed.3': 1.75}))
            doc.undo(); self.assertEqual(doc.values, settings())
            doc.redo(); doc.save()
            self.assertEqual(upgrades.UpgradesConfig(path).values, doc.values)
            doc.apply(settings()); doc.save()
            self.assertEqual(list(Path(folder).iterdir()), [path])
            path.write_text('{}')
            with self.assertRaises(OSError): doc.save()
        for value in (True, float('nan'), float('inf'), 0, -1, 1.001, 11, '2'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                upgrades.validate(settings(**{'lab_upgrade.5': value}))

    def test_old_fixes_imports_fourth_toggle_disabled_without_rewriting(self):
        with TemporaryDirectory() as folder:
            path = Path(folder)/'fixes.cfg'
            old = {key: True for key in fixes.FIXES if key != 'acquisition_range'}
            raw = json.dumps(dict(schema=fixes.FixesConfig.schema, version=1, fixes=old)).encode()
            path.write_bytes(raw)
            doc = fixes.FixesConfig(path)
            self.assertFalse(doc.values['acquisition_range'])
            self.assertTrue(doc.values['damage_priority'])
            self.assertEqual(path.read_bytes(), raw)
            doc.save()
            self.assertEqual(json.loads(path.read_bytes())['version'], 2)

    def test_stock_no_hooks_or_table_writes_and_cross_setting_bound(self):
        self.assertEqual(upgrades_patch.selected_hooks(settings()), {})
        self.assertEqual(upgrades_patch.table_plan(settings()), [])
        customized = settings(**{'oil_yield.2': 1.5})
        self.assertEqual(upgrades_patch.table_plan(customized),
                         [(0x5285e4, struct.pack('<I',72090), struct.pack('<I',98304))])
        high_cost = {k:s['default'] for k,s in overrides.OVERRIDES.items()}
        high_cost.update(research_cost=10000, research_cost_step=1000)
        with self.assertRaisesRegex(ValueError, '32,767'):
            upgrades_patch.validate_memory(mock.Mock(), settings(**{'lab_upgrade.5': 3}), high_cost)

    def test_bad_upgrade_hook_aborts_before_any_write(self):
        memory = {}
        for spec in building_limits.BUILDINGS.values():
            for i,b in enumerate(struct.pack('<H',spec['default'])): memory[spec['address']+i] = b
        read = lambda a,n: bytes(memory.get(a+i,0) for i in range(n))
        write, allocate = mock.Mock(), mock.Mock()
        with self.assertRaises(ValueError):
            game_launcher.apply_configuration(read, write,
                {k:s['default'] for k,s in building_limits.BUILDINGS.items()}, None, allocate, mock.Mock(),
                upgrades=settings(**{'lab_upgrade.5':2}))
        write.assert_not_called(); allocate.assert_not_called()

    def test_matrix_ui_shared_actions_defaults_and_small_window(self):
        with TemporaryDirectory() as folder:
            path = Path(folder)/'upgrades.cfg'
            app = make_editor(upgrades_path=path, tk_scaling=96/72*2)
            try:
                app.geometry('2400x2000'); app.update()
                toolbar = [(str(b), b.winfo_rootx(), b.winfo_rooty()) for b in app.toolbar.buttons]
                page = app.upgrades_page
                app.notebook.select(page); app.update()
                self.assertEqual(toolbar, [(str(b), b.winfo_rootx(), b.winfo_rooty()) for b in app.toolbar.buttons])
                self.assertEqual(len(page.entries), 42)
                for widgets in page.rows.values():
                    label = widgets[0]
                    self.assertEqual(len(label.cget('text').splitlines()), 2)
                    self.assertEqual(label.grid_info()['sticky'], 'w')
                    self.assertEqual(str(label.cget('justify')), 'left')
                page.variables['lab_upgrade.5'].set('2')
                self.assertTrue(page.dirty())
                self.assertIn('+1', page.labels['lab_upgrade.5'].cget('text'))
                app.active_action('save')
                self.assertEqual(upgrades.UpgradesConfig(path).values['lab_upgrade.5'],2)
                page.reset(); page.undo()
                self.assertEqual(page.variables['lab_upgrade.5'].get(), '2')
                page.only_changed.set(True); page.filter(); app.update()
                self.assertFalse(page.rows['oil_yield'][0].winfo_ismapped())
                app.geometry('1000x760'); app.update()
                for entry in page.entries.values():
                    if entry.winfo_ismapped():
                        page.panel.reveal(entry); app.update()
                self.assertEqual(list(Path(folder).iterdir()), [path])
            finally: app.destroy()
