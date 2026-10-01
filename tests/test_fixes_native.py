"""Run compiled fixes and the original KWIPv3 selectors in a synthetic world.

Optional: unicorn, pefile, KKND2_TEST_EXE. No game file is modified or launched.
Only external alliance/visibility responses and the original threat score are
substituted; native scan traversal, target IDs, min/max ranges and air checks run.
"""
import os
import struct
from pathlib import Path
from unittest import TestCase, skipUnless
from support import editor
from kknd2_editor import fixes_patch
from test_fixes import settings
try:
    import pefile
    from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
    from unicorn.x86_const import *
except ImportError:
    Uc = None


class World:
    unit, output, stack, stop = 0x210000, 0x202000, 0x108000, 0x101000
    def __init__(self, image, values, damages=(10, 20, 30, 5, 1), turret=False, limits=None):
        self.cpu = Uc(UC_ARCH_X86, UC_MODE_32)
        for base, size in ((0x400000, 0x200000), (0x100000, 0x10000), (0x200000, 0x100000), (0x700000, 0x10000)):
            self.cpu.mem_map(base, size)
        self.cpu.mem_write(0x400000, image)
        self.hidden, self.score, self.counter = set(), {}, 0
        self.put(0x55eb20, 32); self.put(0x55eaf0, 32); self.put(0x55eb24, 0x280000)
        self.put(0x53b0b4, 8); self.put(0x53b0b0, 8); self.put(0x53b2d4, 0x290000)
        self.cpu.mem_write(0x5283dc, bytes([1])*256)
        self.make_unit(self.unit, 0, (16,16), player=1)
        self.put(self.unit+0x1000+0x20, 12)
        self.put(self.unit+0x1000+0x24, 256)
        self.weapon = self.unit+0x3000
        self.put(self.unit+0x1000+0x64, self.weapon)
        self.put(self.weapon+0x34, 8)
        if turret:
            self.put(self.unit+0x64, self.unit+0x4000)
            self.put(self.unit+0x4000+0x10, self.unit+0x5000)
            self.put(self.unit+0x5000+0x1c, self.weapon)
            self.put(self.unit+0x5000+0x2c, 256)
            self.cpu.mem_write(self.unit+0x1000+0xe4, struct.pack('<H', 2))
            self.put(self.unit+0x1000+0x64, 0)
        self.set_damage(damages)
        fixes_patch.validate_memory(self.cpu.mem_read, values, limits)
        self.plan = fixes_patch.prepare(self.cpu.mem_read, self.cpu.mem_write, lambda n: 0x700000,
                                       lambda a,n: None, values, limits)
        for a, _, raw in self.plan: self.cpu.mem_write(a, raw)
        self.cpu.hook_add(UC_HOOK_CODE, self.hook)

    def put(self, address, value): self.cpu.mem_write(address, struct.pack('<I', value & 0xffffffff))
    def get(self, address): return struct.unpack('<I', self.cpu.mem_read(address, 4))[0]
    def set_damage(self, values): self.cpu.mem_write(self.weapon+0x18, struct.pack('<5h', *values))

    def make_unit(self, address, category, position, player=2):
        self.put(address+0x60, address+0x1000)
        self.put(address+0xc4, address+0x2000)
        self.put(address+0x1000+0x9c, category)
        self.put(address+0x1000+0x98, 2)
        self.put(address+0x2000+0x18, position[0]<<13)
        self.put(address+0x2000+0x1c, position[1]<<13)
        self.cpu.mem_write(address+0x212, b'\x01\x00')
        self.cpu.mem_write(address+0x2fc, bytes([player]))

    def add(self, category, position=(17,16), *, player=2, hidden=False, air=False):
        address = 0x220000+self.counter*0x4000
        self.counter += 1
        self.make_unit(address, category, position, player)
        self.score[address] = 100-self.counter
        if hidden: self.hidden.add(address)
        if air:
            self.put(address+0x2000+0x20, 0x10000)
            cell = 0x290000+((position[1]>>2)*8+(position[0]>>2))*4
            node = 0x291000+self.counter*0x20
            self.put(node+8, self.get(cell)); self.put(node+12,address); self.put(cell,node)
        else:
            cell = 0x280000+(position[1]*32+position[0])*44
            slot = next(i for i in range(4) if not self.get(cell+4*i))
            self.put(cell+4*slot,address)
            self.cpu.mem_write(cell+0x20, b'\x01')
        return address

    def returned(self, result, cleanup=0):
        cpu = self.cpu
        sp = cpu.reg_read(UC_X86_REG_ESP)
        cpu.reg_write(UC_X86_REG_EAX,result)
        cpu.reg_write(UC_X86_REG_ESP,sp+4+cleanup)
        cpu.reg_write(UC_X86_REG_EIP,self.get(sp))

    def hook(self, cpu, address, size, user):
        if address == 0x4c61bc:
            unit = cpu.reg_read(UC_X86_REG_EDX)
            self.returned(int(cpu.mem_read(unit+0x2fc,1)[0] != cpu.reg_read(UC_X86_REG_ECX)))
        elif address == 0x451370:
            target = cpu.reg_read(UC_X86_REG_EDX)
            self.returned(int(self.get(target+4) not in self.hidden), 8)
        elif address == 0x4a1fb8:
            self.returned(self.score.get(cpu.reg_read(UC_X86_REG_EDX), 0))

    def run(self, entry, *args):
        cpu = self.cpu
        cpu.mem_write(self.stack, struct.pack('<'+'I'*(1+len(args)), self.stop, *args))
        cpu.reg_write(UC_X86_REG_ECX,self.unit);cpu.reg_write(UC_X86_REG_EDX,self.output)
        cpu.reg_write(UC_X86_REG_ESP,self.stack)
        cpu.reg_write(UC_X86_REG_EBP,0x109000)
        for reg in (UC_X86_REG_EBX, UC_X86_REG_ESI, UC_X86_REG_EDI): cpu.reg_write(reg, 0xabcdef)
        cpu.emu_start(entry,self.stop,count=3000000)
        assert cpu.reg_read(UC_X86_REG_EIP)==self.stop, hex(cpu.reg_read(UC_X86_REG_EIP))
        assert cpu.reg_read(UC_X86_REG_ESP)==self.stack+4+4*len(args)
        assert cpu.reg_read(UC_X86_REG_EBP)==0x109000
        for reg in (UC_X86_REG_EBX, UC_X86_REG_ESI, UC_X86_REG_EDI): assert cpu.reg_read(reg)==0xabcdef
        return cpu.reg_read(UC_X86_REG_EAX)

    def select(self, wide=False):
        result=self.run(0x4a2039 if wide else 0x4a1893)
        return self.get(self.output+4) if result else None

    def validate(self, target, generation=1):
        self.cpu.mem_write(self.output, struct.pack('<4I',0,target,generation,0))
        return self.run(0x4a265e, 0x202100, 8)


@skipUnless(Uc and os.environ.get('KKND2_TEST_EXE'), 'Optional unicorn/pefile and KKND2_TEST_EXE required')
class NativeFixesTests(TestCase):
    def test_acquisition_extra_three_tiles_and_original_firing_range(self):
        for wide in (True,):
            for turret in (False, True):
                w = World(self.image, settings(acquisition_range=True), turret=turret)
                outside = w.add(1, (27,16))
                self.assertEqual(w.select(wide), outside)
                self.assertEqual(w.validate(outside), 1)
                self.assertEqual(w.get(w.unit+0x60), w.unit+0x1000)
                self.assertEqual(w.get(w.unit+0x1000+0x24), 256)
                if turret:
                    self.assertEqual(w.get(w.unit+0x4000+0x10), w.unit+0x5000)
                    self.assertEqual(w.get(w.unit+0x5000+0x2c), 256)
                w = World(self.image, settings(acquisition_range=True), turret=turret)
                w.add(1, (28,16))
                self.assertIsNone(w.select(wide))

    def test_acquisition_in_range_precedes_damage_priority_and_respects_visibility(self):
        for wide in (True,):
            w = World(self.image, settings(acquisition_range=True, damage_priority=True, zero_damage_filter=True))
            close = w.add(0)
            w.add(2, (27,16))
            self.assertEqual(w.select(wide), close)
            w.set_damage((0,20,30,0,0))
            self.assertNotEqual(w.select(wide), close)
            for condition in ('hidden', 'allied', 'sight', 'building'):
                w = World(self.image, settings(acquisition_range=True))
                w.add(2, (27,16), hidden=condition=='hidden', player=1 if condition=='allied' else 2)
                if condition == 'sight': w.put(w.unit+0x1000+0x20, 8)
                if condition == 'building': w.cpu.mem_write(w.unit+0x1000+0xe4, struct.pack('<H', 4))
                self.assertIsNone(w.select(wide), condition)

    @classmethod
    def setUpClass(cls):
        import hashlib
        from kknd2_editor.game_launcher import SUPPORTED_SHA256
        raw=Path(os.environ['KKND2_TEST_EXE']).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==SUPPORTED_SHA256
        cls.image=pefile.PE(data=raw).get_memory_mapped_image()

    def test_damage_order_zero_combinations_and_live_values(self):
        for wide in (False,True):
            for turret in (False,True):
                w=World(self.image,settings(damage_priority=True,zero_damage_filter=True),turret=turret)
                infantry=w.add(0);vehicle=w.add(1);beast=w.add(2)
                self.assertEqual(w.select(wide),beast)
                w.set_damage((10,20,0,5,1));self.assertEqual(w.select(wide),vehicle)
                w.set_damage((10,0,0,5,1));self.assertEqual(w.select(wide),infantry)
                w.set_damage((0,0,0,0,0));self.assertIsNone(w.select(wide))
                w.set_damage((4000,20,30,5,1));self.assertEqual(w.select(wide),infantry)

    def test_native_ties_and_independent_toggles(self):
        for wide in (False,True):
            for priority, zero in ((False,False),(False,True),(True,False),(True,True)):
                w=World(self.image,settings(damage_priority=priority,zero_damage_filter=zero),damages=(0,20,20,0,0))
                infantry=w.add(0);vehicle=w.add(1);w.add(2)
                self.assertEqual(w.select(wide),vehicle if priority or zero else infantry)
                w.set_damage((0,0,0,0,0))
                self.assertEqual(w.select(wide),None if zero else infantry)

    def test_missing_ordinary_weapon_keeps_native_behavior(self):
        for turret in (False, True):
            w=World(self.image, settings(zero_damage_filter=True, damage_priority=True), turret=turret)
            first=w.add(0);w.add(2)
            w.put(w.unit+(0x5000+0x1c if turret else 0x1000+0x64),0)
            self.assertEqual(w.select(),first)

    def test_range_visibility_allies_and_manual_zero_filter(self):
        for wide in (False,True):
            w=World(self.image,settings(damage_priority=True,zero_damage_filter=True))
            good=w.add(0)
            w.add(2, player=1);w.add(2,hidden=True);far=w.add(2,position=(27,16))
            self.assertEqual(w.select(wide),good)
            self.assertEqual(w.validate(far),1) # Native out-of-range, still positive damage.
            w.set_damage((10,20,0,5,1))
            self.assertEqual(w.validate(far),4) # Zero damage prevents pointless pursuit.
            self.assertEqual(w.validate(good),0)
            self.assertEqual(w.validate(good,generation=99),4)
            self.assertEqual(w.select(wide),good) # No class filter leaks outside a scan.

    def test_buildings_air_and_minimum_range(self):
        w=World(self.image,settings(damage_priority=True,zero_damage_filter=True),damages=(10,20,30,40,50))
        infantry=w.add(0);building=w.add(3);air=w.add(4,air=True)
        self.assertEqual(w.select(),air)
        self.assertEqual(w.select(True),building) # Native broad selector searches ground only.
        w.set_damage((10,20,30,40,0));self.assertEqual(w.select(),building)
        w.set_damage((10,20,30,0,0));self.assertEqual(w.select(),infantry)
        self.assertEqual(w.validate(building),4)
        self.assertEqual(w.validate(air),4)
        w.put(w.unit+0x1000+0xa4,64)
        self.assertIsNone(w.select())

    def test_shift_adapter_preserves_registers_and_consumes_click(self):
        for modifiers in (0,0x10,0x20,0x40,0x70):
            w=World(self.image,settings(shift_build=True))
            c=w.cpu;frame=0x109000;stack=0x108000
            w.put(frame-0x88,0x200000);w.put(0x200074,72)
            w.put(0x53f628,0x53f628)
            w.put(frame-0x5c,1);w.put(0x565438,modifiers);w.put(0x5652cc,0x31)
            c.reg_write(UC_X86_REG_EBP,frame);c.reg_write(UC_X86_REG_ESP,stack)
            registers=(UC_X86_REG_EAX,UC_X86_REG_EBX,UC_X86_REG_ECX,UC_X86_REG_EDX,UC_X86_REG_ESI,UC_X86_REG_EDI)
            for r in registers:c.reg_write(r,0x123407)
            c.reg_write(UC_X86_REG_EFLAGS,0x246)
            destination=0x46677e if modifiers & 0x10 else 0x466d07
            c.emu_start(0x466d01,destination,count=1000)
            self.assertEqual(c.reg_read(UC_X86_REG_EIP),destination)
            self.assertEqual(c.reg_read(UC_X86_REG_ESP),stack)
            self.assertEqual(c.reg_read(UC_X86_REG_EBP),frame)
            for r in registers:self.assertEqual(c.reg_read(r),0x123407)
            self.assertEqual(c.reg_read(UC_X86_REG_EFLAGS),0x246)
            self.assertEqual(c.mem_read(0x565508,1),b'\x07')
            self.assertEqual(w.get(frame-0x5c),0 if modifiers & 0x10 else 1)
            self.assertEqual(w.get(0x5652cc),0x21 if modifiers & 0x10 else 0x31)

    def test_ai_income_caps_follow_each_faction_and_preserve_comparison(self):
        from kknd2_editor.building_limits import BUILDINGS
        limits={k:s['default'] for k,s in BUILDINGS.items()}
        for faction,cap in zip(('SURV','MUTE','ROBOT'),(2,8,20)):
            limits[f'UNIT_{faction}_COLLECTOR']=cap
            limits[f'UNIT_{faction}_CONVERTER']=cap+1
        for race,faction in enumerate(('SURV','MUTE','ROBOT')):
            for suffix,site,counter in (('COLLECTOR',0x4277a6,0x94),('CONVERTER',0x4277f4,0x90)):
                cap=limits[f'UNIT_{faction}_{suffix}']
                for count in (0,cap-1,cap,cap+1,100):
                    with self.subTest(race=race,suffix=suffix,count=count):
                        w=World(self.image,settings(),limits=limits);c=w.cpu
                        for k,spec in BUILDINGS.items():c.mem_write(spec['address'],struct.pack('<H',limits[k]))
                        w.put(0x200008,0x505ea8+race*0x74);w.put(0x200000+counter,count)
                        regs=(UC_X86_REG_EAX,UC_X86_REG_EBX,UC_X86_REG_ECX,UC_X86_REG_EDX,UC_X86_REG_ESI,UC_X86_REG_EDI,UC_X86_REG_EBP)
                        for r in regs:c.reg_write(r,0x200000 if r==UC_X86_REG_EAX else 0x123456)
                        c.reg_write(UC_X86_REG_ESP,0x108000)
                        c.emu_start(site,site+7,count=1000)
                        flags=c.reg_read(UC_X86_REG_EFLAGS)&0x8d5
                        for r in regs:self.assertEqual(c.reg_read(r),0x200000 if r==UC_X86_REG_EAX else 0x123456)
                        self.assertEqual(c.reg_read(UC_X86_REG_ESP),0x108000)
                        # Compare to an ordinary CMP with the same custom cap.
                        original=self.image[site-0x400000:site-0x400000+7]
                        c.mem_write(site,original[:-1]+bytes([cap]))
                        c.emu_start(site,site+7,count=1)
                        self.assertEqual(flags,c.reg_read(UC_X86_REG_EFLAGS)&0x8d5)

    def test_shift_reenters_input_loop_and_exits_on_unavailability(self):
        for availability in ('available', 'missing', 'disabled'):
            w=World(self.image,settings(shift_build=True))
            c=w.cpu;frame=0x109000
            w.put(frame-0x88,0x200000);w.put(frame-0x5c,1)
            w.put(0x200074,72);w.put(0x53f628,0x53f628)
            w.put(0x565438,0x10);w.put(0x5652cc,0x10)
            c.mem_write(0x565508,b'\x00')
            c.mem_write(0x203012,struct.pack('<H',6 if availability=='available' else 0))
            calls=[]
            def hook(cpu,address,size,user):
                if address==0x460450:
                    calls.append('build');w.returned(1)
                elif address==0x464df9:
                    calls.append('input');w.returned(1)
                elif address==0x45b2c8:
                    calls.append('availability');w.returned(0 if availability=='missing' else 0x204000)
                elif address==0x459c10:w.returned(0x203000)
            c.hook_add(UC_HOOK_CODE,hook)
            c.reg_write(UC_X86_REG_EBP,frame);c.reg_write(UC_X86_REG_ESP,0x108000)
            end=0x46683d if availability=='available' else 0x466d22
            c.emu_start(0x466cee,end,count=10000)
            self.assertEqual(c.reg_read(UC_X86_REG_EIP),end)
            self.assertEqual(calls,['build','input','availability'])
            self.assertEqual(c.mem_read(0x565508,1),b'\x01')
            self.assertEqual(w.get(0x5652cc),0)
            self.assertEqual(c.reg_read(UC_X86_REG_ESP),0x108000)

    def test_shift_checks_real_native_instance_counts_and_custom_caps(self):
        # Execute the unmodified game's 4078B5/40772A count+1 logic. Only menu
        # rendering/removal is stubbed; availability is NOT a canned response.
        # Completed/in-progress buildings both enter this native count list.
        for building in (72, 73, 74, 90, 91, 92, 93, 94, 95, 102, 108, 112):
            for cap in (1, 4, 8, 20):
                for existing in (max(0, cap-2), cap-1, cap, cap+1):
                    with self.subTest(building=building, cap=cap, existing=existing):
                        w=World(self.image, settings(shift_build=True)); c=w.cpu
                        frame=0x109000; menu_item=0x205000
                        w.put(frame-0x88,0x200000);w.put(frame-0x5c,1)
                        w.put(0x200074,building);w.put(0x565438,0x10)
                        w.put(0x5404d8,menu_item)
                        data=w.get(0x52bed8+building*0x110+0xe0)
                        c.mem_write(data+0x10,struct.pack('<H',cap))
                        w.put(0x53f628,0x206000);w.put(0x206000,0x53f628)
                        w.put(0x206008,building);w.put(0x20600c,existing)
                        removed=[]
                        def menu(cpu,address,size,user):
                            if address==0x459c27: w.returned(0x207000)
                            elif address==0x45ae13:
                                removed.append(cpu.reg_read(UC_X86_REG_EDX)&0xffff)
                                w.returned(0)
                        c.hook_add(UC_HOOK_CODE,menu)
                        c.reg_write(UC_X86_REG_EBP,frame);c.reg_write(UC_X86_REG_ESP,0x108000)
                        end=0x466d07 if existing+1>=cap else 0x46677e
                        c.emu_start(0x466d01,end,count=10000)
                        self.assertEqual(c.reg_read(UC_X86_REG_EIP),end)
                        self.assertEqual(removed,[building] if existing+1>=cap else [])
                        self.assertEqual(w.get(0x5404d8),0 if removed else menu_item)
                        self.assertEqual(w.get(frame-0x5c),1 if removed else 0)
                        self.assertEqual(w.get(0x20600c),existing) # Never forge live counts.
                        self.assertEqual(c.reg_read(UC_X86_REG_ESP),0x108000)
                        if removed:
                            # Native success/cancel cleanup must not dereference
                            # the deleted item or remove it again.
                            for address in (0x40a9f6,0x40aa34):
                                w.put(0x108000,w.stop)
                                c.reg_write(UC_X86_REG_ESP,0x108000)
                                c.emu_start(address,w.stop,count=1000)
                            self.assertEqual(removed,[building])
