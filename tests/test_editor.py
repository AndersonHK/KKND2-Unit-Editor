"""Safety regression tests. Read source once; write only to temporary copies."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, main, mock
import os
from support import editor, SOURCE, make_editor




class SafetyTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = SOURCE.read_bytes()

    def setUp(self):
        self.doc = editor.Config(self.raw)


    def test_editor_limits_for_every_field(self):
        self.assertEqual(editor.FIELD_MAXIMUMS[0], 10000)
        self.assertEqual(editor.FIELD_MAXIMUMS[11], 600)
        for col, maximum in enumerate(editor.FIELD_MAXIMUMS):
            row = next(r for r, u in enumerate(self.doc.units) if u.cells[col].original != "-")
            self.doc.apply({(row, col): str(maximum)})
            self.assertEqual(editor.Config(self.doc.serialize()).value(row, col), str(maximum))
            with self.assertRaisesRegex(ValueError, "maximum"):
                self.doc.apply({(row, col): str(maximum + 1)})
        with self.assertRaises(ValueError):
            self.doc.apply({(0, 1): "0"})

    def test_existing_above_limit_is_preserved_without_permitting_new_overruns(self):
        cell = self.doc.units[0].cells[0]
        raw = bytearray(self.raw)
        raw[cell.offset:cell.offset + cell.width] = b"999999"
        doc = editor.Config(raw)
        self.assertEqual(doc.serialize(), bytes(raw))
        doc.apply({(0, 0): "999999", (0, 2): "9000"})
        self.assertEqual(editor.Config(doc.serialize()).value(0, 0), "999999")
        with self.assertRaises(ValueError):
            doc.apply({(0, 0): "999998"})
        doc.apply({(0, 0): "5000"})

    def test_all_display_names_and_units(self):
        self.assertEqual(set(editor.UNIT_NAMES), {u.identifier for u in self.doc.units})
        self.assertEqual(editor.UNIT_NAMES["UNIT_SURV_GUNNER"], "Machine Gunner")
        self.assertEqual(editor.UNIT_NAMES["UNIT_MUTE_GUNNER"], "Berzerker")
        self.assertEqual(editor.UNIT_NAMES["UNIT_ROBOT_GUNNER"], "Seeder")
        self.assertEqual(len(editor.FIELD_UNITS), len(editor.FIELDS))
        self.assertIn("32 = 1 tile", editor.field_hint(7))
        self.assertIn("1/60 s", editor.field_hint(10))

    def test_unchanged_roundtrip_is_byte_identical(self):
        self.assertEqual(self.doc.serialize(), self.raw)
        self.assertEqual(len(self.doc.units), 110)
        self.assertEqual(self.doc.body_offset, 534)
        self.assertEqual(len(self.doc.units[0].cells), 17)

    def test_each_edit_changes_only_its_original_field(self):
        for row, unit in enumerate(self.doc.units):
            for col, cell in enumerate(unit.cells):
                if cell.original == "-":
                    continue
                value = "2" if col == 1 else ("1" if cell.original == "0" else "0")
                self.doc.changes = {(row, col): value}
                out = self.doc.serialize()
                self.assertEqual(out[:cell.offset], self.raw[:cell.offset])
                self.assertEqual(out[cell.offset + cell.width:], self.raw[cell.offset + cell.width:])
                self.assertEqual(editor.Config(out).value(row, col), value)
        self.doc.changes.clear()

    def test_wider_and_narrower_numbers_preserve_offsets(self):
        cell = self.doc.units[0].cells[0]
        for value in ("0", "10000", "1234"):
            self.doc.apply({(0, 0): value})
            out = self.doc.serialize()
            self.assertEqual(len(out), len(self.raw))
            self.assertEqual(out[cell.offset + cell.width:], self.raw[cell.offset + cell.width:])

    def test_invalid_inputs_and_unavailable_fields_blocked(self):
        for value in ("", "-1", "1.5", "1000000", "1\nUNIT_X", " 3", "3\t", "\u0663", "-"):
            with self.assertRaises(ValueError):
                self.doc.apply({(0, 0): value})
        row = next(i for i, u in enumerate(self.doc.units) if u.cells[12].original == "-")
        with self.assertRaises(ValueError):
            self.doc.apply({(row, 12): "10"})
        self.assertEqual(self.doc.serialize(), self.raw)

    def test_edit_transaction_undo_redo_and_revert(self):
        self.doc.apply({(0, 0): "12", (1, 1): "20"})
        edited = self.doc.serialize()
        self.doc.undo()
        self.assertEqual(self.doc.serialize(), self.raw)
        self.doc.redo()
        self.assertEqual(self.doc.serialize(), edited)
        before = self.doc.changes.copy()
        with self.assertRaises(ValueError):
            self.doc.apply({(0, 0): "17", (0, 1): "bad"})
        self.assertEqual(self.doc.changes, before)
        self.doc.apply({key: self.doc.units[key[0]].cells[key[1]].original for key in before})
        self.assertEqual(self.doc.serialize(), self.raw)

    def test_malformed_headers_and_rows_rejected(self):
        for raw in (b"\xff\xfe" + self.raw, self.raw[:300], self.raw.replace(b"C\0o\0s\0t\0", b"X\0o\0s\0t\0", 1),
                    self.raw[:600], self.raw + self.raw[self.doc.body_offset:self.doc.body_offset + 151]):
            with self.assertRaises(editor.FormatError):
                editor.Config(raw)

    def test_noop_save_creates_no_backup(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "UCONFIG_02.cfg"
            path.write_bytes(self.raw)
            self.assertIsNone(editor.save_config(path, self.doc))
            self.assertEqual(list(Path(folder).iterdir()), [path])

    def test_atomic_save_backup_and_reopen(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "UCONFIG_02.cfg"
            path.write_bytes(self.raw)
            self.doc.apply({(0, 2): "9876", (109, 16): "1"})
            backup = editor.save_config(path, self.doc)
            self.assertEqual(backup.read_bytes(), self.raw)
            self.assertEqual(path.read_bytes(), self.doc.serialize())
            fresh = editor.Config(path.read_bytes())
            self.assertEqual(fresh.value(0, 2), "9876")
            fresh.apply({(0, 2): "5"})
            backup2 = editor.save_config(path, fresh)
            self.assertNotEqual(backup, backup2)
            self.assertEqual(backup2.read_bytes(), self.doc.serialize())
            self.assertFalse(list(Path(folder).glob(".kknd2-*.tmp")))

    def test_external_edit_is_never_overwritten(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "UCONFIG_02.cfg"
            external = self.raw + b"\n"
            path.write_bytes(external)
            self.doc.apply({(0, 0): "42"})
            with self.assertRaises(OSError):
                editor.save_config(path, self.doc)
            self.assertEqual(path.read_bytes(), external)

    def test_failed_replacement_keeps_original_and_backup(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "UCONFIG_02.cfg"
            path.write_bytes(self.raw)
            self.doc.apply({(0, 0): "42"})
            with mock.patch.object(editor.os, "replace", side_effect=PermissionError("File locked")):
                with self.assertRaises(PermissionError):
                    editor.save_config(path, self.doc)
            self.assertEqual(path.read_bytes(), self.raw)
            self.assertEqual(next((Path(folder) / "backups").iterdir()).read_bytes(), self.raw)
            self.assertFalse(list(Path(folder).glob(".kknd2-*.tmp")))

    def test_backup_failure_prevents_replacement(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "UCONFIG_02.cfg"
            path.write_bytes(self.raw)
            (Path(folder) / "backups").write_text("blocked")
            self.doc.apply({(0, 0): "42"})
            with self.assertRaises(OSError):
                editor.save_config(path, self.doc)
            self.assertEqual(path.read_bytes(), self.raw)


class GuiTests(TestCase):
    def test_edit_navigation_filter_undo_save_and_reopen(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "UCONFIG_02.cfg"
            original = SOURCE.read_bytes()
            path.write_bytes(original)
            app = make_editor(Path(folder))
            app.withdraw()
            try:
                app.update()
                self.assertEqual(app.current, 0)
                self.assertEqual(len(app.tree.get_children()), 110)
                app.values[2].set("9876")
                app.tree.selection_set("1")
                app.select_unit()
                self.assertEqual(app.config_doc.value(0, 2), "9876")
                app.undo()
                self.assertEqual(app.config_doc.serialize(), original)
                app.redo()
                self.assertEqual(app.config_doc.value(0, 2), "9876")
                app.faction_var.set("Survivors")
                self.assertTrue(all(app.config_doc.units[int(x)].faction == "Survivors" for x in app.tree.get_children()))
                app.search_var.set("GUNNER")
                self.assertEqual(app.tree.get_children(), ("0",))
                app.tree.selection_set("0")
                app.select_unit()
                app.values[0].set("bad")
                with mock.patch.object(editor.messagebox, "showerror") as error:
                    self.assertFalse(app.save())
                    error.assert_called_once()
                self.assertEqual(path.read_bytes(), original)
                app.values[0].set("222")
                self.assertTrue(app.save())
                self.assertEqual(editor.Config(path.read_bytes()).value(0, 0), "222")
                self.assertEqual(editor.Config(path.read_bytes()).value(0, 2), "9876")
                self.assertFalse(app.form_dirty())
                self.assertFalse(app.config_doc.changes)
                self.assertTrue(app.load_file(path))
                self.assertEqual(app.values[0].get(), "222")
                # All fields remain reachable in the scrollable viewport.
                app.deiconify()
                app.update()
                for entry in app.entries:
                    app.stats.reveal(entry)
                    app.update()
                    canvas = app.stats.canvas
                    self.assertGreaterEqual(entry.winfo_rootx(), canvas.winfo_rootx() - 2)
                    self.assertGreaterEqual(entry.winfo_rooty(), canvas.winfo_rooty() - 2)
                    self.assertLessEqual(entry.winfo_rootx() + entry.winfo_width(), canvas.winfo_rootx() + canvas.winfo_width() + 2)
                    self.assertLessEqual(entry.winfo_rooty() + entry.winfo_height(), canvas.winfo_rooty() + canvas.winfo_height() + 2)
            finally:
                app.destroy()

    def test_defaults_are_frozen_and_survive_save_reload_and_reset(self):
        frozen = dict(editor.DEFAULTS)
        self.assertEqual(len(frozen), 110)
        self.assertTrue(all(len(row) == 17 for row in frozen.values()))
        with TemporaryDirectory() as folder:
            path = Path(folder) / 'UCONFIG_02.cfg'
            baseline = editor.Config(SOURCE.read_bytes())
            baseline.apply({(r, c): value for r, unit in enumerate(baseline.units)
                            for c, value in enumerate(frozen[unit.identifier])})
            path.write_bytes(baseline.serialize())
            app = make_editor(Path(folder))
            app.withdraw()
            try:
                app.update()
                self.assertEqual(app.comparison_rows(True), [])
                app.values[2].set('9876')
                self.assertEqual(app.delta_labels[2].cget('text'), '+9426')
                self.assertTrue(app.different(0))
                self.assertTrue(app.save())
                self.assertEqual(app.comparison_rows(False), [])
                self.assertEqual(len(app.comparison_rows(True)), 1)
                self.assertTrue(app.load_file(path))
                self.assertEqual(app.default_labels[2].cget('text'), '450')
                self.assertEqual(app.original_labels[2].cget('text'), '9876')
                app.defaults_only.set(True)
                app.filter_units()
                self.assertEqual(app.tree.get_children(), ('0',))
                app.reset_defaults()
                self.assertEqual(app.values[2].get(), '450')
                self.assertEqual(app.comparison_rows(True), [])
                self.assertEqual(len(app.comparison_rows(False)), 1)
                app.undo()
                self.assertEqual(app.values[2].get(), '9876')
                app.redo()
                self.assertEqual(app.values[2].get(), '450')
                self.assertEqual(editor.DEFAULTS, frozen)
                # Reset is pending until Save; source still holds the edit.
                self.assertEqual(editor.Config(path.read_bytes()).value(0, 2), '9876')
            finally:
                app.destroy()

    def test_layout_at_100_150_200_250_percent_and_small_windows(self):
        for percent in (100, 150, 200, 250):
            for dimensions in ('1050x690', '800x760'):
                with self.subTest(dpi=percent, window=dimensions):
                    app = make_editor(SOURCE.parent, SOURCE, tk_scaling=(96 / 72) * percent / 100)
                    callback_errors = []
                    app.report_callback_exception = lambda *args: callback_errors.append(args)
                    try:
                        app.minsize(1, 1)
                        app.geometry(dimensions)
                        app.update()
                        self.assertFalse(callback_errors)
                        self.assertGreater(app.stats.canvas.winfo_height(), 25)
                        expected_row_height = editor.tkfont.nametofont('TkDefaultFont').metrics('linespace')
                        self.assertGreaterEqual(int(app.style.lookup('Treeview', 'rowheight')), expected_row_height)
                        # Every toolbar/action control is visible, and buttons wrap.
                        for bar in (app.toolbar, app.actions):
                            for button in bar.buttons:
                                self.assertGreater(button.winfo_width(), 10)
                                self.assertLessEqual(button.winfo_x() + button.winfo_width(), bar.winfo_width() + 1)
                                self.assertLessEqual(button.winfo_y() + button.winfo_height(), bar.winfo_height() + 1)
                                self.assertLessEqual(button.winfo_rooty() + button.winfo_height(), app.winfo_rooty() + app.winfo_height())
                        # Scroll to all 17 inputs and the Default/Delta/Saved columns.
                        for entry in app.entries:
                            app.stats.reveal(entry)
                            app.update()
                            canvas = app.stats.canvas
                            self.assertGreaterEqual(entry.winfo_rooty(), canvas.winfo_rooty() - 2)
                            self.assertLessEqual(entry.winfo_rooty() + entry.winfo_height(), canvas.winfo_rooty() + canvas.winfo_height() + 2)
                        app.stats.reveal(app.original_labels[-1])
                        app.update()
                        label = app.original_labels[-1]
                        self.assertLessEqual(label.winfo_rootx() + label.winfo_width(), canvas.winfo_rootx() + canvas.winfo_width() + 2)
                    finally:
                        app.destroy()


if __name__ == "__main__":
    main(verbosity=2)
