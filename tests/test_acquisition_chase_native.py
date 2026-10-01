"""Regressions: passive buildings, idle -> path -> firing, placed construction."""
import os
import struct
from unittest import TestCase, skipUnless
import test_fixes_native as native
from test_fixes import settings
from kknd2_editor import fixes_patch
if native.Uc:
    from unicorn import UC_HOOK_CODE
    from unicorn.x86_const import UC_X86_REG_ECX, UC_X86_REG_EDX, UC_X86_REG_ESP


@skipUnless(native.Uc and os.environ.get('KKND2_TEST_EXE'), 'Native emulator/game required')
class AcquisitionChaseTests(TestCase):
    @classmethod
    def setUpClass(cls):
        native.NativeFixesTests.setUpClass()
        cls.image = native.NativeFixesTests.image

    def world(self, turret=False, **opts):
        w = native.World(self.image, settings(acquisition_range=True, **opts), turret=turret)
        w.cpu.mem_write(w.unit+0x2e6, struct.pack('<h',1))
        w.put(0x51058c,512); w.put(0x55eaf8,1)
        w.put(w.unit+0x1000+0x68,1)
        w.put(w.unit+0x1000+0xc0,0x4d2172)
        w.put(w.unit+0x90,0x4cc43e)
        return w

    def functions(self, w):
        calls=[]
        def hook(cpu,at,size,user):
            if at in (0x4c3200,0x443548,0x4c7890,0x47e570,0x4d05da):
                calls.append(at)
                w.returned(0,4 if at in (0x4c3200,0x443548) else 0)
        w.cpu.hook_add(UC_HOOK_CODE,hook)
        return calls

    def test_idle_acquires_paths_then_fires_at_original_range(self):
        for turret in (False,True):
            w=self.world(turret,zero_damage_filter=True,damage_priority=True)
            target=w.add(1,(27,16))
            calls=self.functions(w)
            w.run(0x4cc43e)
            self.assertEqual(w.get(w.unit+0x148),target)
            self.assertEqual(w.get(w.unit+0x90),0x4ce7c6)
            self.assertEqual(struct.unpack('<h',w.cpu.mem_read(w.unit+0x2e6,2))[0],33)
            self.assertEqual(w.validate(target),1)
            calls.clear()
            w.run(0x4ce7c6)
            self.assertEqual(calls,[0x47e570]) # real FSM requests native pathing
            self.assertEqual(w.get(w.unit+0x100),(27<<13)+0x1000)
            # Simulate arrival in weapon range; run the same unmodified chase FSM.
            w.put(w.unit+0x2000+0x18,20<<13)
            self.assertEqual(w.validate(target),0)
            w.put(w.unit+0x1000+0x9c,0) # avoid an unrelated animation turn
            calls.clear();w.run(0x4ce7c6)
            self.assertNotIn(0x47e570,calls)
            if turret:
                self.assertEqual(calls,[0x4d05da])
            else:
                self.assertEqual(w.get(w.unit+0x168),target)
                self.assertEqual(w.get(w.unit+0x90),0x4d2172)

    def test_idle_respects_range_sight_damage_orders_and_stagger(self):
        for condition in ('far','hidden','ally','sight','zero','hold','move','guard','off_tick','contained','building','in_range'):
            w=self.world(zero_damage_filter=True)
            position=(28,16) if condition=='far' else (17,16) if condition=='in_range' else (27,16)
            w.add(1,position,hidden=condition=='hidden',player=1 if condition=='ally' else 2)
            if condition=='sight':w.put(w.unit+0x1000+0x20,8)
            if condition=='zero':w.set_damage((10,0,30,5,1))
            if condition in ('hold','move','guard'):
                w.cpu.mem_write(w.unit+0x2e6,struct.pack('<h',dict(hold=8,move=2,guard=9)[condition]))
            if condition=='off_tick':w.put(0x55eaf8,2)
            if condition=='contained':w.put(w.unit+0x1fc,0x260000)
            if condition=='building':w.cpu.mem_write(w.unit+0x1000+0xe4,struct.pack('<H',4))
            original=w.get(0x700000+fixes_patch.load_payload()['exports']['original_idle'])
            calls=[]
            def hook(cpu,at,size,user):
                if at==original:calls.append(at);w.returned(0)
            w.cpu.hook_add(UC_HOOK_CODE,hook)
            w.run(0x4cc43e)
            self.assertEqual(calls,[original],condition)
            self.assertEqual(w.get(w.unit+0x90),0x4cc43e,condition)

    def test_firing_only_scan_does_not_pin_out_of_range_turret_target(self):
        w=self.world(True)
        w.add(1,(27,16))
        self.assertIsNone(w.select())
        self.assertIsNotNone(w.select(True))

    def test_orderless_idle_unit_survives_lost_target_or_failed_path(self):
        for outcome in ('dead','reused','zero',4,5):
            w=self.world(zero_damage_filter=True)
            target=w.add(1,(27,16));self.functions(w)
            w.run(0x4cc43e)
            self.assertEqual(w.get(w.unit+0x114),0)
            if outcome in ('dead','reused'):
                w.cpu.mem_write(target+0x212,struct.pack('<H',0 if outcome=='dead' else 2))
            if outcome=='zero':w.set_damage((10,0,30,5,1))
            if isinstance(outcome,int):
                w.cpu.mem_write(w.unit+0x2f7,bytes([outcome]))
                w.run(0x4cec3e)
            else:w.run(0x4ce7c6)
            self.assertEqual(w.get(w.unit+0x90),0x4cbd4a,outcome)
            self.assertEqual(struct.unpack('<h',w.cpu.mem_read(w.unit+0x2e6,2))[0],1)
            self.assertEqual(w.get(w.unit+0x114),0)

    def test_fight_can_target_real_passive_buildings_with_acquisition_on_or_off(self):
        for acquisition in (False,True):
            for turret in (False,True):
                w=native.World(self.image,settings(acquisition_range=acquisition,zero_damage_filter=True),turret=turret)
                building=w.add(3,(27,16))
                # Prior tests incorrectly marked buildings as armed. Copy an
                # actual passive Outpost definition's physical/behavior flags.
                stock=0x52bed8+72*0x110
                w.put(building+0x1000+0x98,w.get(stock+0x98))
                w.cpu.mem_write(building+0x1000+0xe4,struct.pack('<H',4))
                w.put(0x5c27d8,w.unit);w.put(w.unit,building);w.put(building,0x5c27d8)
                self.assertEqual(w.run(0x4a2455),1)
                self.assertEqual(w.get(w.output+4),building)
                w.set_damage((10,20,30,0,1))
                self.assertEqual(w.run(0x4a2455),0)
                self.assertEqual(w.get(w.output+4),0)
