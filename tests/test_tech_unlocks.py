from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, mock
import struct
from collections import Counter
from support import make_editor, editor
from kknd2_editor import tech_unlocks as unlocks
from kknd2_editor.unlock_data import UNLOCKS, TABLES


class UnlockTests(TestCase):
    def test_faction_split_preserves_commands_and_every_original_occurrence(self):
        values = {k: s['default'] for k, s in UNLOCKS.items()}
        self.assertEqual(unlocks.table_bundle(values), (b'', []))
        values['UNIT_SURV_GUNNER'] = 4
        values['UNIT_MUTE_GUNNER'] = 2
        values['UNIT_ROBOT_TOWER1'] = 0
        blob, plan = unlocks.table_bundle(values, 0x10000000)
        by_id = {s['enum']: values[k] for k, s in UNLOCKS.items()}
        for table, before, after in plan:
            expected, actual = Counter(), Counter()
            for tier, rows in enumerate(TABLES[table]):
                for row in rows:
                    for faction, unit in enumerate(row):
                        if unit != 0xffff:
                            expected[(faction, unit, by_id.get(unit, tier))] += 1
            for tier, pointer in enumerate(struct.unpack('<6I', after)):
                offset = pointer - 0x10000000
                while True:
                    row = struct.unpack_from('<3H', blob, offset)
                    offset += 6
                    if row == (0xffff,) * 3:
                        break
                    for faction, unit in enumerate(row):
                        if unit != 0xffff:
                            actual[(faction, unit, tier)] += 1
            self.assertEqual(actual, expected)

    def test_defaults_schema_and_no_backups(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / 'tech_unlocks.cfg'
            doc = unlocks.UnlocksConfig(path)
            self.assertEqual(len(doc.values), 106)
            self.assertEqual(doc.values['UNIT_SURV_SNIPER'], 5)
            self.assertEqual(doc.values['UNIT_SURV_GUNNER'], 0)
            doc.apply(dict(doc.values, UNIT_SURV_SNIPER=1))
            doc.save()
            self.assertEqual(unlocks.UnlocksConfig(path).values['UNIT_SURV_SNIPER'], 1)
            doc.apply(doc.defaults)
            doc.save()
            self.assertEqual(list(Path(folder).iterdir()), [path])
            for value in (True, -1, 6, 1.5):
                with self.assertRaises(ValueError):
                    doc.apply(dict(doc.values, UNIT_SURV_GUNNER=value))

    def test_gui_zero_level_defaults_filter_and_toolbar_dispatch(self):
        with TemporaryDirectory() as folder:
            app = make_editor(unlocks_path=Path(folder) / 'unlocks.cfg')
            try:
                app.notebook.select(app.unlocks_page)
                app.update()
                page = app.unlocks_page
                page.variables['UNIT_SURV_SNIPER'].set('0')
                self.assertEqual(page.labels['UNIT_SURV_SNIPER'][1].cget('text'), '-5')
                self.assertEqual(page.labels['UNIT_SURV_SNIPER'][3].cget('text'), '0–5')
                self.assertNotEqual(str(page.entries['UNIT_TEMPLE'].cget('state')), 'disabled')
                with mock.patch.object(page, 'save') as save:
                    app.toolbar.buttons[0].invoke()
                    save.assert_called_once()
                page.only_changed.set(True)
                page.filter()
                app.update()
                self.assertTrue(page.entries['UNIT_SURV_SNIPER'].winfo_ismapped())
                self.assertFalse(page.entries['UNIT_SURV_GUNNER'].winfo_ismapped())
                self.assertTrue(page.save())
            finally:
                app.destroy()
