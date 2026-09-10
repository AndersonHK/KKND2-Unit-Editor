from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, mock
import json
import struct
from support import editor, make_editor
from kknd2_editor import overrides, overrides_patch, game_launcher, building_limits


def defaults():
    return {k: s['default'] for k, s in overrides.OVERRIDES.items()}


class OverridesTests(TestCase):
    def test_defaults_roundtrip_undo_redo_no_backups(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / 'overrides.cfg'
            doc = overrides.OverridesConfig(path)
            self.assertFalse(path.exists())
            self.assertEqual(doc.values, defaults())
            doc.apply(dict(doc.values, tanker_capacity=1200, research_cost_step=0, rig_loading_rate=65536))
            changed = dict(doc.values)
            doc.undo()
            self.assertEqual(doc.values, defaults())
            doc.redo()
            self.assertEqual(doc.values, changed)
            doc.save()
            self.assertEqual(overrides.OverridesConfig(path).values, changed)
            doc.apply(doc.defaults)
            doc.save()
            self.assertEqual(list(Path(folder).iterdir()), [path])

    def test_schema_ranges_duplicate_keys_and_external_changes(self):
        for key, spec in overrides.OVERRIDES.items():
            for value in (True, '1', 1.5, spec['minimum'] - 1, spec['maximum'] + 1):
                with self.assertRaises(ValueError):
                    overrides.validate(dict(defaults(), **{key: value}))
        with TemporaryDirectory() as folder:
            path = Path(folder) / 'overrides.cfg'
            for raw in ('{}', '{"version":1,"version":1}', json.dumps({
                    'schema': 'kknd2-editor-overrides', 'version': True, 'overrides': defaults()})):
                path.write_text(raw, encoding='utf-8')
                with self.assertRaises(ValueError):
                    overrides.OverridesConfig(path)
            path.unlink()
            doc = overrides.OverridesConfig(path)
            doc.save()
            before = path.read_bytes()
            doc.apply(dict(doc.values, tanker_capacity=600))
            with mock.patch.object(building_limits.os, 'replace', side_effect=PermissionError('locked')):
                with self.assertRaises(OSError):
                    doc.save()
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(list(Path(folder).iterdir()), [path])
            path.write_bytes(before + b'\n')
            with self.assertRaises(OSError):
                doc.save()

    def test_combined_patches_validate_before_any_write(self):
        memory = {}
        def put(address, data):
            memory.update({address + i: value for i, value in enumerate(data)})
        def read(address, size):
            return bytes(memory.get(address + i, 0) for i in range(size))
        limits = {k: s['default'] for k, s in building_limits.BUILDINGS.items()}
        for spec in building_limits.BUILDINGS.values():
            put(spec['address'], struct.pack('<H', spec['default']))
        for address, before in overrides_patch.SITES.items():
            put(address, before)
        settings = dict(defaults(), tanker_capacity=1000, rig_loading_rate=65536,
                        powerplant_unloading_rate=8192, research_cost_step=0, research_time_step=2)
        writes = mock.Mock(side_effect=put)
        allocation = mock.Mock(return_value=0x10000000)
        seal = mock.Mock()
        last = max(overrides_patch.SITES)
        memory[last] ^= 1
        with self.assertRaises(ValueError):
            game_launcher.apply_configuration(read, writes, limits, settings, allocation, seal)
        writes.assert_not_called()
        allocation.assert_not_called()
        memory[last] ^= 1
        count, patched = game_launcher.apply_configuration(read, writes, limits, settings, allocation, seal)
        self.assertEqual(count, 0)
        self.assertGreater(patched, 10)
        seal.assert_called_once()
        for address, before, after in overrides_patch.patch_plan(settings, 0x10000000):
            self.assertEqual(read(address, len(after)), after)

    def test_defaults_override_option_reads_without_transfer_hooks(self):
        plan = overrides_patch.patch_plan(defaults())
        self.assertEqual(len(plan), 3)
        self.assertEqual(overrides_patch.stub_bundle(defaults()), (b'', {}))
        self.assertEqual(plan[0][2], b'\xb8' + struct.pack('<I', 20) + b'\x90\x90')

    def test_slow_low_cost_research_retains_native_minimum_progress(self):
        values = dict(defaults(), research_cost=50, research_time=600,
                      research_cost_step=0, research_time_step=40)
        self.assertEqual(overrides.validate(values), values)
        self.assertEqual(len(overrides_patch.stub_bundle(values)[1]), 2)


class OverridesGuiTests(TestCase):
    def test_shared_toolbar_edit_save_switch_and_reset(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / 'overrides.cfg'
            app = make_editor(overrides_path=path)
            try:
                app.geometry('1800x1100')
                app.update()
                before = [(str(b), b.winfo_rootx(), b.winfo_rooty()) for b in app.toolbar.buttons]
                page = app.overrides_page
                app.notebook.select(page)
                app.update()
                self.assertEqual(before, [(str(b), b.winfo_rootx(), b.winfo_rooty()) for b in app.toolbar.buttons])
                page.variables['tanker_capacity'].set('800')
                self.assertEqual(page.labels['tanker_capacity'][1].cget('text'), '+400')
                self.assertTrue(app.active_action('save'))
                self.assertFalse(page.dirty())
                self.assertEqual(overrides.OverridesConfig(path).values['tanker_capacity'], 800)
                page.reset()
                self.assertEqual(page.variables['tanker_capacity'].get(), '400')
                page.undo()
                self.assertEqual(page.variables['tanker_capacity'].get(), '800')
                page.variables['research_cost_step'].set('0')
                with mock.patch.object(editor.messagebox, 'askyesnocancel', return_value=None):
                    self.assertFalse(page.load_file(path))
                with mock.patch.object(editor.messagebox, 'askyesnocancel', return_value=False):
                    self.assertTrue(page.load_file(path))
                self.assertEqual(page.variables['research_cost_step'].get(), '20')
                page.variables['tanker_capacity'].set('not an integer')
                with mock.patch.object(editor.messagebox, 'showerror'), mock.patch.object(editor, 'launch_game') as launch:
                    app.launch()
                    launch.assert_not_called()
            finally:
                app.destroy()

    def test_invalid_file_recovery_and_other_page_error_blocks_launch(self):
        with TemporaryDirectory() as folder:
            folder = Path(folder)
            bad = folder / 'bad.cfg'
            bad.write_text('{}')
            app = make_editor(overrides_path=bad, limits_path=bad)
            try:
                self.assertEqual(str(app.launch_button.cget('state')), 'disabled')
                self.assertTrue(app.overrides_page.load_file(folder / 'good.cfg'))
                self.assertEqual(str(app.launch_button.cget('state')), 'disabled')
                self.assertTrue(app.limits_page.load_file(folder / 'limits.cfg'))
                self.assertEqual(str(app.launch_button.cget('state')), 'normal')
            finally:
                app.destroy()

    def test_fields_accessible_at_high_dpi(self):
        with TemporaryDirectory() as folder:
            app = make_editor(overrides_path=Path(folder) / 'overrides.cfg', tk_scaling=96/72*2)
            try:
                app.minsize(1, 1)
                app.geometry('1000x850')
                app.notebook.select(app.overrides_page)
                app.update()
                page = app.overrides_page
                for entry in page.entries.values():
                    page.panel.reveal(entry)
                    app.update()
                    self.assertGreaterEqual(entry.winfo_rooty(), page.panel.canvas.winfo_rooty() - 2)
                    self.assertLessEqual(entry.winfo_rooty() + entry.winfo_height(),
                                         page.panel.canvas.winfo_rooty() + page.panel.canvas.winfo_height() + 2)
                self.assertTrue(app.launch_button.winfo_ismapped())
            finally:
                app.destroy()
