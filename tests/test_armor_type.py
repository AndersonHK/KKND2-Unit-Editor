"""Extended armor types: named controls, enum persistence and native damage lookup."""
import json
import os
import struct
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, skipUnless, mock
from support import editor, synthetic_config, make_editor
from kknd2_editor import unit_extensions as ext, game_launcher, building_limits
from test_fixes_native import World, Uc
from test_fixes import settings


class ArmorTests(TestCase):
    def test_all_stock_rows_and_enum_validation(self):
        self.assertEqual(set(ext.ARMOR), set(editor.DEFAULTS))
        self.assertEqual(ext.ARMOR_TYPES, {'Infantry':0,'Vehicle':1,'Beast':2,'Aircraft':4,'Building':3})
        for bad in (-1,5,True,'2',2.0,None):
            with self.assertRaises(ValueError): ext.validate({'UNIT_SURV_GUNNER':{'armor_type':bad}})
        for fields in ({}, {'typo':2}, {'burst_count':2}):
            with self.assertRaises(ValueError): ext.validate({'UNIT_SURV_GUNNER':fields})

    def test_v1_import_history_combined_save_and_preset_isolation(self):
        with TemporaryDirectory() as folder:
            path=Path(folder)/'UCONFIG_02.cfg';raw=synthetic_config();path.write_bytes(raw)
            sidecar=ext.extension_path(path)
            v1=raw[:120]+json.dumps(dict(schema=ext.SCHEMA,version=1,units={'UNIT_SURV_ANACONDATANK':{'burst_count':4}})).encode()
            sidecar.write_bytes(v1)
            doc=editor.ExtendedConfig(raw,path)
            row=next(i for i,u in enumerate(doc.units) if u.identifier=='UNIT_SURV_ANACONDATANK')
            self.assertEqual(doc.value(row,editor.BURST_COLUMN),'4')
            self.assertEqual(doc.value(row,editor.ARMOR_COLUMN),'Vehicle')
            self.assertEqual(sidecar.read_bytes(),v1)
            doc.apply({(row,editor.ARMOR_COLUMN):'Beast'})
            doc.undo();self.assertEqual(doc.value(row,editor.ARMOR_COLUMN),'Vehicle')
            doc.redo();doc.save()
            self.assertEqual(path.read_bytes(),raw)
            self.assertEqual(set(Path(folder).iterdir()),{path,sidecar})
            data=json.loads(sidecar.read_bytes()[120:])
            self.assertEqual(data['version'],2)
            self.assertEqual(data['units']['UNIT_SURV_ANACONDATANK'],{'burst_count':4,'armor_type':2})
            self.assertEqual(editor.ExtendedConfig(raw,path).value(row,editor.ARMOR_COLUMN),'Beast')
            self.assertEqual(editor.ExtendedConfig(raw,path.with_name('UCONFIG_03.cfg')).value(row,editor.ARMOR_COLUMN),'Vehicle')
            doc.apply({(row,editor.ARMOR_COLUMN):'Vehicle'});doc.save()
            self.assertEqual(doc.extension_values(),{'UNIT_SURV_ANACONDATANK':{'burst_count':4}})
            # A failed companion save after a native save preserves both virtual fields.
            doc.apply({(row,0):'9999',(row,editor.ARMOR_COLUMN):'Infantry',(row,editor.BURST_COLUMN):'5'})
            with mock.patch.object(ext.UnitExtensions,'save',side_effect=OSError('disk full')):
                with self.assertRaises(OSError):doc.save()
            self.assertEqual(doc.value(row,editor.ARMOR_COLUMN),'Infantry')
            self.assertEqual(doc.value(row,editor.BURST_COLUMN),'5')
            doc.save()
            self.assertEqual(editor.ExtendedConfig(path.read_bytes(),path).value(row,editor.ARMOR_COLUMN),'Infantry')

    def test_armor_schema_not_accepted_as_v1(self):
        with TemporaryDirectory() as folder:
            path=Path(folder)/'UCONFIG_02.cfg';raw=synthetic_config()
            data=dict(schema=ext.SCHEMA,version=1,units={'UNIT_SURV_GUNNER':{'armor_type':2}})
            ext.extension_path(path).write_bytes(raw[:120]+json.dumps(data).encode())
            with self.assertRaises(ValueError):editor.ExtendedConfig(raw,path)

    def test_dropdown_labels_history_reset_and_review(self):
        with TemporaryDirectory() as folder:
            path=Path(folder)/'UCONFIG_02.cfg';raw=synthetic_config();path.write_bytes(raw)
            app=make_editor(path.parent,tk_scaling=96/72*2)
            try:
                app.update();col=editor.ARMOR_COLUMN
                self.assertEqual(str(app.entries[col].cget('state')),'readonly')
                self.assertEqual(app.values[col].get(),'Infantry')
                self.assertEqual(str(app.tk.call('tk_focusNext',str(app.entries[5]))),str(app.entries[col]))
                self.assertEqual(str(app.tk.call('tk_focusNext',str(app.entries[col]))),str(app.entries[6]))
                app.values[col].set('Aircraft')
                self.assertEqual(app.delta_labels[col].cget('text'),'changed')
                self.assertTrue(app.commit_form())
                self.assertEqual(app.comparison_rows()[0][1:4],('Armor-Type','Infantry','Aircraft'))
                app.undo();self.assertEqual(app.values[col].get(),'Infantry')
                app.redo();self.assertTrue(app.save())
                self.assertEqual(app.original_labels[col].cget('text'),'Aircraft')
                app.reset_defaults();self.assertEqual(app.values[col].get(),'Infantry')
                app.revert_unit();self.assertEqual(app.values[col].get(),'Aircraft')
                self.assertEqual(path.read_bytes(),raw)
            finally:app.destroy()

    def test_mismatched_armor_data_aborts_before_any_writes(self):
        memory={s['address']:struct.pack('<H',s['default']) for s in building_limits.BUILDINGS.values()}
        write=mock.Mock()
        with self.assertRaisesRegex(ValueError,'armor type'):
            game_launcher.apply_configuration(lambda a,n:memory.get(a,bytes(n)),write,
                {k:s['default'] for k,s in building_limits.BUILDINGS.items()},None,mock.Mock(),mock.Mock(),
                extensions={'UNIT_SURV_ANACONDATANK':{'armor_type':2}})
        write.assert_not_called()


@skipUnless(Uc and os.environ.get('KKND2_TEST_EXE'),'Optional native instruction tests')
class NativeArmorTests(TestCase):
    @classmethod
    def setUpClass(cls):
        import hashlib, pefile
        from kknd2_editor.game_launcher import SUPPORTED_SHA256
        raw=Path(os.environ["KKND2_TEST_EXE"]).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==SUPPORTED_SHA256
        cls.image=pefile.PE(data=raw).get_memory_mapped_image()

    def test_catalog_matches_native_ids_and_each_damage_lookup(self):
        from unicorn.x86_const import UC_X86_REG_EBP,UC_X86_REG_ECX
        w=World(self.image,settings())
        by_enum={enum:key for key,(enum,_) in ext.ARMOR.items()}
        for i in range(110):
            enum,ptr=struct.unpack('<II',w.cpu.mem_read(0x5061b0+i*8,8))
            name=bytes(w.cpu.mem_read(ptr,100)).decode('utf-16le').split('\0')[0]
            self.assertEqual(by_enum[enum],name)
        for key,(enum,stock) in ext.ARMOR.items():
            definition=0x52bed8+enum*0x110
            self.assertEqual(w.get(definition+0x9c),stock)
            w.put(0x108000-8,w.unit);w.put(w.unit+0x60,definition)
            w.put(0x108000-12,0x250000)
            w.cpu.mem_write(0x250010,struct.pack('<5h',11,22,33,44,55))
            for value in range(5):
                for a,before,after in ext.patch_plan(w.cpu.mem_read,{key:{'armor_type':value}}):w.cpu.mem_write(a,after)
                w.cpu.reg_write(UC_X86_REG_EBP,0x108000)
                w.cpu.emu_start(0x404d4b,0x404d5f,count=20)
                self.assertEqual(w.cpu.reg_read(UC_X86_REG_ECX),(11,22,33,44,55)[value])
                w.put(definition+0x9c,stock)

    def test_zero_filter_and_priority_observe_overridden_armor_type(self):
        w=World(self.image,settings(damage_priority=True,zero_damage_filter=True),damages=(10,0,30,0,0))
        infantry=w.add(0);tank=w.add(1)
        enum,stock=ext.ARMOR['UNIT_SURV_ANACONDATANK']
        w.put(tank+0x60,0x52bed8+enum*0x110)
        self.assertEqual(w.select(),infantry)
        for a,_,b in ext.patch_plan(w.cpu.mem_read,{'UNIT_SURV_ANACONDATANK':{'armor_type':2}}):w.cpu.mem_write(a,b)
        self.assertEqual(w.select(),tank)
