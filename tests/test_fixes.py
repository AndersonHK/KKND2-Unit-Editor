import hashlib
import json
import struct
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, mock
from support import make_editor, editor
from kknd2_editor import fixes, fixes_patch, game_launcher, building_limits


def settings(**kwargs):
    return dict({k: s['default'] for k, s in fixes.FIXES.items()}, **kwargs)


class FixesTests(TestCase):
    def test_boolean_schema_history_atomic_save_and_external_change(self):
        with TemporaryDirectory() as folder:
            path = Path(folder)/'fixes.cfg'
            doc = fixes.FixesConfig(path)
            self.assertFalse(path.exists())
            self.assertEqual(doc.values, settings())
            doc.apply(settings(shift_build=True, damage_priority=True))
            doc.undo()
            self.assertEqual(doc.values, settings())
            doc.redo()
            doc.save()
            self.assertEqual(fixes.FixesConfig(path).values, doc.values)
            doc.apply(settings(zero_damage_filter=True))
            doc.save()
            self.assertEqual(list(Path(folder).iterdir()), [path])
            path.write_text('{}')
            with self.assertRaises(OSError): doc.save()
        for value in (0, 1, 'true', None, [], 1.0):
            with self.assertRaises(ValueError): fixes.validate(settings(shift_build=value))
        for values in ({}, dict(settings(), typo=True)):
            with self.assertRaises(ValueError): fixes.validate(values)

    def test_disabled_does_not_allocate_or_patch(self):
        args = [mock.Mock() for _ in range(4)]
        self.assertEqual(fixes_patch.prepare(*args, settings()), [])
        for arg in args: arg.assert_not_called()

    def test_bad_hook_aborts_before_any_feature_write(self):
        memory = {}
        for spec in building_limits.BUILDINGS.values():
            for i, b in enumerate(struct.pack('<H', spec['default'])): memory[spec['address']+i] = b
        read = lambda a, n: bytes(memory.get(a+i, 0) for i in range(n))
        write, allocate = mock.Mock(), mock.Mock()
        limits = {k: s['default'] for k, s in building_limits.BUILDINGS.items()}
        with self.assertRaises(ValueError):
            game_launcher.apply_configuration(read, write, limits, None, allocate, mock.Mock(),
                                              fixes=settings(damage_priority=True))
        write.assert_not_called()
        allocate.assert_not_called()

    def test_compiled_payload_matches_source(self):
        native = Path(__file__).resolve().parents[1]/'native'
        digest = hashlib.sha256(b''.join((native/name).read_bytes().replace(b'\r\n', b'\n')
                                        for name in ('fixes.cpp', 'kwip_abi.h', 'upgrades.h'))).hexdigest()
        self.assertEqual(fixes_patch.load_payload()['source_sha256'], digest)

    def test_toggle_ui_shared_toolbar_filter_history_and_save(self):
        with TemporaryDirectory() as folder:
            path = Path(folder)/'fixes.cfg'
            app = make_editor(fixes_path=path, tk_scaling=96/72*2)
            try:
                app.geometry('2280x2000')
                app.update()
                toolbar = [(str(b), b.winfo_rootx(), b.winfo_rooty()) for b in app.toolbar.buttons]
                page = app.fixes_page
                app.notebook.select(page)
                app.update()
                self.assertEqual(toolbar, [(str(b), b.winfo_rootx(), b.winfo_rooty()) for b in app.toolbar.buttons])
                self.assertEqual(len(page.entries), 4)
                for key, entry in page.entries.items():
                    self.assertEqual(entry.winfo_class(), 'TCheckbutton')
                    self.assertEqual(len(page.display_name(key).splitlines()), 3)
                    page.panel.reveal(entry)
                    app.update()
                    self.assertTrue(entry.winfo_ismapped())
                page.entries['shift_build'].invoke()
                self.assertTrue(page.dirty())
                self.assertEqual(page.labels['shift_build'][1].cget('text'), 'Enabled')
                page.only_changed.set(True)
                page.filter()
                self.assertFalse(page.entries['damage_priority'].winfo_ismapped())
                app.active_action('save')
                self.assertTrue(fixes.FixesConfig(path).values['shift_build'])
                page.reset()
                self.assertFalse(page.variables['shift_build'].get())
                page.undo()
                self.assertTrue(page.variables['shift_build'].get())
                page.revert()
                self.assertFalse(page.dirty())
                app.geometry('1050x760')
                app.update()
                for _, button in app.notebook.pages.values():
                    self.assertTrue(button.winfo_ismapped())
                    self.assertLessEqual(button.winfo_x()+button.winfo_width(), app.notebook.bar.winfo_width())
                self.assertEqual(list(Path(folder).iterdir()), [path])
            finally:
                app.destroy()
