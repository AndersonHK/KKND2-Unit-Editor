"""Per-preset extension persistence, unified editing and native firing checks."""
import json
import os
from pathlib import Path
import struct
from tempfile import TemporaryDirectory
from unittest import TestCase, mock, skipUnless
from support import editor, synthetic_config, make_editor
from kknd2_editor import unit_extensions as ext, game_launcher, building_limits

ANACONDA = 'UNIT_SURV_ANACONDATANK'
COL = editor.BURST_COLUMN


class ExtensionTests(TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'UCONFIG_02.cfg'
        self.original = synthetic_config()
        self.path.write_bytes(self.original)
        self.doc = editor.ExtendedConfig(self.original, self.path)
        self.row = next(i for i, u in enumerate(self.doc.units) if u.identifier == ANACONDA)

    def test_defaults_extension_only_save_and_preset_isolation(self):
        self.assertEqual(self.doc.value(self.row, COL), '2')
        self.doc.save()
        self.assertFalse(ext.extension_path(self.path).exists())
        self.doc.apply({(self.row, COL): '3'})
        self.assertEqual(self.doc.serialize(), self.original)
        self.doc.save()
        sidecar = ext.extension_path(self.path)
        self.assertEqual(sidecar.name, 'UCONFIG_02_ext.cfg')
        self.assertEqual(self.path.read_bytes(), self.original)
        self.assertEqual(set(Path(self.temp.name).iterdir()), {self.path, sidecar})
        reloaded = editor.ExtendedConfig(self.original, self.path)
        self.assertEqual(reloaded.value(self.row, COL), '3')
        other = self.path.with_name('UCONFIG_03.cfg')
        self.assertEqual(editor.ExtendedConfig(self.original, other).value(self.row, COL), '2')
        self.assertEqual(editor.config_files(self.temp.name), [self.path])
        with self.assertRaisesRegex(ValueError, 'original UCONFIG'):
            ext.extension_path(sidecar)
        self.doc.apply({(self.row, COL): '2'})
        self.doc.save()
        self.assertEqual(self.doc.extension_values(), {})
        self.assertEqual(json.loads(sidecar.read_bytes()[120:])['units'], {})

    def test_combined_history_and_native_format(self):
        self.doc.apply({(self.row, COL): '5', (self.row, 0): '9999'})
        self.doc.undo()
        self.assertFalse(self.doc.changes)
        self.doc.save()  # A no-op Save must not erase Redo.
        self.doc.redo()
        self.assertEqual(self.doc.value(self.row, COL), '5')
        payload = self.doc.serialize()
        self.assertEqual(len(payload), len(self.original))
        self.assertEqual(len(editor.Config(payload).units[self.row].cells), 17)
        self.doc.save()
        self.assertFalse(self.doc.changes)
        self.assertEqual(editor.Config(self.path.read_bytes()).value(self.row, 0), '9999')

    def test_invalid_values_are_blocked(self):
        for value in ('0', '128', '250', '-1', '1.5', ' 2', '\u0663', ''):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.doc.apply({(self.row, COL): value})
        for value in ('1', '127'):
            self.doc.apply({(self.row, COL): value})
        with self.assertRaisesRegex(ValueError, 'no supported'):
            self.doc.apply({(0, COL): '2'})

    def test_disk_conflict_preflights_both_files(self):
        self.doc.apply({(self.row, COL): '5', (self.row, 0): '9999'})
        ext.extension_path(self.path).write_bytes(b'external changes')
        with self.assertRaisesRegex(OSError, 'changed on disk'):
            self.doc.save()
        self.assertEqual(self.path.read_bytes(), self.original)
        self.assertTrue(self.doc.changes)
        ext.extension_path(self.path).unlink()
        self.path.write_bytes(self.original + b'\n')
        with self.assertRaisesRegex(OSError, 'changed on disk'):
            self.doc.save()
        self.assertFalse(ext.extension_path(self.path).exists())

    def test_second_file_failure_preserves_pending_extension_and_retry(self):
        self.doc.apply({(self.row, COL): '5', (self.row, 0): '9999'})
        with mock.patch.object(ext.UnitExtensions, 'save', side_effect=OSError('disk full')):
            with self.assertRaisesRegex(OSError, 'extended edits remain pending'):
                self.doc.save()
        self.assertEqual(self.doc.changes, {(self.row, COL): '5'})
        self.doc.save()
        self.assertFalse(self.doc.changes)
        self.assertEqual(self.doc.value(self.row, COL), '5')

    def test_schema_validation_and_title_refresh(self):
        header = self.original[:120]
        valid = dict(schema=ext.SCHEMA, version=1, units={ANACONDA: {'burst_count': 3}})
        for data in (dict(valid, version=3), dict(valid, version=True),
                     dict(valid, units={ANACONDA: {'burst_count': True}}),
                     dict(valid, units={ANACONDA: {'burst_count': 128}}),
                     dict(valid, units={'UNIT_UNKNOWN': {'burst_count': 2}}),
                     dict(valid, units={ANACONDA: {'typo': 2}})):
            ext.extension_path(self.path).write_bytes(header + json.dumps(data).encode())
            with self.assertRaises(ValueError):
                editor.ExtendedConfig(self.original, self.path)
        ext.extension_path(self.path).write_bytes(header + b'{"schema":1,"schema":2}')
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            editor.ExtendedConfig(self.original, self.path)
        ext.extension_path(self.path).write_bytes(ext.encode(header, valid['units']))
        renamed = 'Renamed'.ljust(60, '\0').encode('utf-16le') + self.original[120:]
        self.path.write_bytes(renamed)
        doc = editor.ExtendedConfig(renamed, self.path)
        doc.save()
        self.assertEqual(ext.extension_path(self.path).read_bytes()[:120], renamed[:120])
        self.assertEqual(doc.value(self.row, COL), '3')

    def test_gui_default_delta_filter_save_reset_and_checkbox(self):
        app = make_editor(self.path.parent, tk_scaling=96/72*2)
        self.addCleanup(app.destroy)
        app.update()
        app.tree.selection_set(str(self.row))
        app.select_unit()
        app.update()
        self.assertEqual(app.values[COL].get(), '2')
        self.assertEqual(app.default_labels[COL].cget('text'), '2')
        self.assertEqual(str(app.tk.call('tk_focusNext', str(app.entries[9]))), str(app.entries[COL]))
        self.assertEqual(str(app.tk.call('tk_focusNext', str(app.entries[COL]))), str(app.entries[10]))
        app.values[COL].set('4')
        self.assertEqual(app.delta_labels[COL].cget('text'), '+2')
        self.assertTrue(app.commit_form())
        self.assertEqual(app.comparison_rows()[0][1:4], ('Burst-Count', '2', '4'))
        app.undo()
        self.assertEqual(app.values[COL].get(), '2')
        app.redo()
        app.defaults_only.set(True)
        app.filter_units()
        self.assertEqual(app.tree.get_children(), (str(self.row),))
        self.assertTrue(app.save())
        self.assertFalse(app.form_dirty())
        app.reset_defaults()
        self.assertEqual(app.values[COL].get(), '2')
        app.revert_unit()
        self.assertEqual(app.values[COL].get(), '4')
        self.assertEqual(self.path.read_bytes(), self.original)
        self.assertEqual(app.campaign_indicator_size, 20)
        self.assertGreater(abs(app.campaign_font.cget('size')), 28)
        app.campaign_check.invoke()
        self.assertTrue(app.campaign_stats.get())
        app.campaign_check.invoke()
        self.assertFalse(app.campaign_stats.get())

    def test_patch_validation_before_any_other_feature_writes(self):
        memory = {}
        for spec in building_limits.BUILDINGS.values():
            memory[spec['address']] = struct.pack('<H', spec['default'])
        writes = []
        with self.assertRaisesRegex(ValueError, 'turret data'):
            game_launcher.apply_configuration(lambda a, n: memory.get(a, bytes(n)),
                lambda *args: writes.append(args), {k: s['default'] for k, s in building_limits.BUILDINGS.items()},
                None, lambda n: 0x700000, lambda *args: None, extensions={ANACONDA: {'burst_count': 3}})
        self.assertEqual(writes, [])


try:
    import pefile
    from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
    from unicorn.x86_const import UC_X86_REG_EBP, UC_X86_REG_EIP, UC_X86_REG_ESP, UC_X86_REG_EAX
except ImportError:
    Uc = None


@skipUnless(Uc and os.environ.get('KKND2_TEST_EXE'), 'Optional native instruction tests')
class NativeExtensionTests(TestCase):
    def setUp(self):
        self.image = pefile.PE(os.environ['KKND2_TEST_EXE']).get_memory_mapped_image()
        self.cpu = Uc(UC_ARCH_X86, UC_MODE_32)
        self.cpu.mem_map(0x400000, 0x200000)
        self.cpu.mem_write(0x400000, self.image)
        self.cpu.mem_map(0x100000, 0x10000)
        self.cpu.reg_write(UC_X86_REG_EBP, 0x108000)
        self.cpu.reg_write(UC_X86_REG_ESP, 0x107000)

    def test_all_catalog_pointers_and_burst_transition_boundaries(self):
        for identifier, (enum, turret, default) in ext.BURSTS.items():
            for count in (1, 2, 3, 127):
                plan = ext.patch_plan(self.cpu.mem_read, {identifier: {'burst_count': count}})
                for a, before, after in plan:
                    self.cpu.mem_write(a, after)
                self.cpu.mem_write(0x108000-0x14, struct.pack('<I', 0x102000))
                self.cpu.mem_write(0x102064, struct.pack('<I', 0x103000))
                self.cpu.mem_write(0x103010, struct.pack('<I', turret))
                for completed in range(count):
                    self.cpu.mem_write(0x102310, bytes([completed]))
                    def stop(cpu, address, size, data):
                        if address in (0x4daf8b, 0x4db096): cpu.emu_stop()
                    hook = self.cpu.hook_add(UC_HOOK_CODE, stop)
                    self.cpu.emu_start(0x4daf5a, 0x4db097, count=30)
                    self.cpu.hook_del(hook)
                    self.assertEqual(self.cpu.reg_read(UC_X86_REG_EIP),
                                     0x4daf8b if completed+1 == count else 0x4db096)
                self.cpu.mem_write(turret+0x10, struct.pack('<I', default))

    def test_native_preset_title_reader_accepts_either_file_order(self):
        native = synthetic_config()
        extension = ext.encode(native[:120], {ANACONDA: {'burst_count': 3}})
        for pair in ((native, extension), (extension, native)):
            self.cpu.mem_write(0x5bd72c, bytes(30*120))
            for payload in pair:
                offset = [0]
                self.cpu.mem_write(0x108000-0x170, struct.pack('<I', 2))
                self.cpu.reg_write(UC_X86_REG_ESP, 0x107000)
                def read_file(cpu, address, size, data):
                    if address != 0x4e5542: return
                    sp = cpu.reg_read(UC_X86_REG_ESP)
                    ret, dest = struct.unpack('<II', cpu.mem_read(sp, 8))
                    chunk = payload[offset[0]:offset[0]+2]
                    offset[0] += 2
                    cpu.mem_write(dest, chunk)
                    cpu.reg_write(UC_X86_REG_EAX, 1 if len(chunk) == 2 else 0)
                    cpu.reg_write(UC_X86_REG_ESP, sp+4)
                    cpu.reg_write(UC_X86_REG_EIP, ret)
                hook = self.cpu.hook_add(UC_HOOK_CODE, read_file)
                self.cpu.emu_start(0x42e750, 0x42e7ea, count=5000)
                self.cpu.hook_del(hook)
                self.assertEqual(self.cpu.reg_read(UC_X86_REG_EIP), 0x42e7ea)
            title = bytes(self.cpu.mem_read(0x5bd72c+2*120, 120))
            self.assertEqual(title, native[:120])
