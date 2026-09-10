import json
import struct
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, mock, skipUnless
from support import make_editor
from kknd2_editor import projectiles, projectiles_patch, overrides, overrides_patch, game_launcher, building_limits
from kknd2_editor.projectile_data import PROJECTILES
try:
    from unicorn import Uc, UC_ARCH_X86, UC_MODE_32
    from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_ECX, UC_X86_REG_EDX, UC_X86_REG_EBP, UC_X86_REG_ESP, UC_X86_REG_EFLAGS
except ImportError:
    Uc = None


def defaults(specs):
    return {key: spec['default'] for key, spec in specs.items()}


ROCKET = 'SURV_ROCKETEER_519C30'


class ProjectileTests(TestCase):
    def test_roundtrip_bounds_and_no_backups(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / 'projectiles.cfg'
            doc = projectiles.ProjectilesConfig(path)
            self.assertFalse(path.exists())
            changed = dict(doc.values, **{ROCKET + '.speed': 2048, ROCKET + '.lifetime': 68})
            doc.apply(changed)
            doc.undo()
            self.assertEqual(doc.values, doc.defaults)
            doc.redo()
            doc.save()
            self.assertEqual(projectiles.ProjectilesConfig(path).values, changed)
            doc.apply(doc.defaults)
            doc.save()
            self.assertEqual(list(Path(folder).iterdir()), [path])
        for key, spec in projectiles.FIELDS.items():
            for value in (True, 1.5, spec['minimum']-1, spec['maximum']+1):
                with self.assertRaises(ValueError):
                    projectiles.validate(dict(defaults(projectiles.FIELDS), **{key: value}))

    def test_legacy_overrides_migrate_without_losing_settings_or_writing_on_open(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / 'overrides.cfg'
            old = {k: s['default'] for k, s in overrides.OVERRIDES.items() if k in overrides.V1_KEYS}
            old.update(tanker_capacity=800, research_cost_step=50, research_time_step=5, powerplant_unloading_rate=8192)
            raw = json.dumps(dict(schema='kknd2-editor-overrides', version=1, overrides=old)).encode()
            path.write_bytes(raw)
            doc = overrides.OverridesConfig(path)
            self.assertEqual(path.read_bytes(), raw)
            self.assertEqual({k: doc.values[k] for k in old}, old)
            self.assertEqual(doc.values['solar_income'], 7)
            self.assertEqual(doc.values['building_placement_range'], 5)
            self.assertTrue(doc.needs_migration)
            doc.save()
            self.assertEqual(json.loads(path.read_bytes())['version'], 2)
            self.assertEqual(overrides.OverridesConfig(path).values, doc.values)
            self.assertEqual(list(Path(folder).iterdir()), [path])
            for invalid in (dict(old, typo=1), {k: v for k, v in old.items() if k != 'research_time'}):
                path.write_text(json.dumps(dict(schema=doc.schema, version=1, overrides=invalid)))
                with self.assertRaises(ValueError):
                    overrides.OverridesConfig(path)

    def test_projectile_validation_precedes_every_write(self):
        memory = {}
        def put(a, data):
            memory.update({a+i: b for i, b in enumerate(data)})
        def read(a, n):
            return bytes(memory.get(a+i, 0) for i in range(n))
        for s in building_limits.BUILDINGS.values():
            put(s['address'], struct.pack('<H', s['default']))
        for a, raw in overrides_patch.SITES.items():
            put(a, raw)
        for p in PROJECTILES.values():
            put(p['address']+4, struct.pack('<I', p['handler']))
            if p['speed'] is not None:
                put(p['address']+0x14, struct.pack('<I', p['speed']))
        put(projectiles_patch.LIFETIME_SITE, projectiles_patch.LIFETIME_ORIGINAL)
        memory[projectiles_patch.LIFETIME_SITE] ^= 1
        write, allocate = mock.Mock(side_effect=put), mock.Mock()
        with self.assertRaises(ValueError):
            game_launcher.apply_configuration(read, write, defaults(building_limits.BUILDINGS),
                dict(defaults(overrides.OVERRIDES), tanker_capacity=800), allocate, mock.Mock(),
                projectiles=defaults(projectiles.FIELDS))
        write.assert_not_called()
        allocate.assert_not_called()

    def test_gui_search_edit_switch_save_and_selected_reset(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / 'projectiles.cfg'
            app = make_editor(projectiles_path=path)
            try:
                app.geometry('2000x1300')
                app.update()
                buttons = [(str(b), b.winfo_rootx(), b.winfo_rooty()) for b in app.toolbar.buttons]
                page = app.projectiles_page
                app.notebook.select(page)
                app.update()
                self.assertEqual(buttons, [(str(b), b.winfo_rootx(), b.winfo_rooty()) for b in app.toolbar.buttons])
                page.search.set('rocketeer')
                app.update()
                page.tree.selection_set(ROCKET)
                app.update()
                page.variables[ROCKET+'.lifetime'].set('68')
                other = 'MUTE_ROCKETEER_519DF0.lifetime'
                page.variables[other].set('50')
                self.assertTrue(page.dirty())
                self.assertEqual(page.labels[ROCKET+'.lifetime'][1].cget('text'), '+34')
                self.assertTrue(app.active_action('save'))
                self.assertEqual(projectiles.ProjectilesConfig(path).values[ROCKET+'.lifetime'], 68)
                page.reset()
                self.assertEqual(page.variables[ROCKET+'.lifetime'].get(), '34')
                self.assertEqual(page.variables[other].get(), '50')
                page.undo()
                self.assertEqual(page.variables[ROCKET+'.lifetime'].get(), '68')
                page.search.set('no matching weapon')
                app.update()
                self.assertIsNone(page.selected)
                self.assertEqual(list(Path(folder).iterdir()), [path])
            finally:
                app.destroy()


@skipUnless(Uc, 'Optional unicorn emulator is not installed')
class NativeProjectileTests(TestCase):
    def cpu(self):
        cpu = Uc(UC_ARCH_X86, UC_MODE_32)
        cpu.mem_map(0x100000, 0x10000)
        cpu.mem_map(0x200000, 0x10000)
        cpu.mem_map(0x300000, 0x10000)
        cpu.reg_write(UC_X86_REG_EBP, 0x208000)
        cpu.reg_write(UC_X86_REG_ESP, 0x207000)
        cpu.mem_write(0x207000, struct.pack('<I', 0x101000))
        return cpu

    def test_all_lifetime_types_independent_and_registers_preserved(self):
        values = defaults(projectiles.FIELDS)
        keys = [key for key in values if key.endswith('.lifetime')]
        for n, key in enumerate(keys):
            values[key] = [1, 68, 127, 128, 254, 255, 80][n]
        code = projectiles_patch.lifetime_stub(values)
        for key in keys + [None]:
            cpu = self.cpu()
            weapon = PROJECTILES[key.rsplit('.',1)[0]]['address'] if key else 0x519000
            cpu.mem_write(0x207ffc, struct.pack('<I', 0x300000))
            cpu.mem_write(0x30004c, struct.pack('<I', weapon))
            cpu.reg_write(UC_X86_REG_EAX, 0x12345678)
            cpu.reg_write(UC_X86_REG_ECX, 0x87654321)
            cpu.reg_write(UC_X86_REG_EFLAGS, 0x246)
            cpu.mem_write(0x100000, code)
            cpu.emu_start(0x100000, 0x101000, count=100)
            self.assertEqual(cpu.mem_read(0x300050,1)[0], values[key] if key else 34)
            self.assertEqual(cpu.reg_read(UC_X86_REG_EAX), 0x12345678)
            self.assertEqual(cpu.reg_read(UC_X86_REG_ECX), 0x87654321)
            self.assertEqual(cpu.reg_read(UC_X86_REG_EDX), 0x300000)
            self.assertEqual(cpu.reg_read(UC_X86_REG_EFLAGS), 0x246)
            self.assertEqual(cpu.reg_read(UC_X86_REG_ESP), 0x207004)

    def test_research_bar_denominator_uses_billing_tier(self):
        code = next(after for a, before, after in overrides_patch.patch_plan(defaults(overrides.OVERRIDES)) if a == 0x494528)
        for lab in range(6):
            for target in range(6):
                cpu = self.cpu()
                cpu.mem_map(0x510000, 0x10000)
                cpu.mem_write(0x51b2c4, struct.pack('<6I', *[250+(5-i)*50 for i in range(6)]))
                cpu.mem_write(0x207ff8, struct.pack('<I', 0x30004c))
                cpu.mem_write(0x207ff0, struct.pack('<I', 0x301000))
                cpu.mem_write(0x30004a, struct.pack('<H', lab))
                cpu.mem_write(0x30104a, struct.pack('<H', target))
                cpu.mem_write(0x100000, code + b'\xc3')
                cpu.emu_start(0x100000, 0x101000, count=20)
                self.assertEqual(cpu.reg_read(UC_X86_REG_EAX), 250+(5-lab)*50)
