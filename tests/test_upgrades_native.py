"""Exercise compiled upgrade adapters and original game instructions in Unicorn."""
import os
import struct
from pathlib import Path
from unittest import TestCase, skipUnless
from support import editor
from test_upgrades import settings
from test_fixes import settings as fixes_settings
from kknd2_editor import fixes_patch, upgrades_patch
try:
    import pefile
    from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
    from unicorn.x86_const import *
except ImportError:
    Uc = None


class Engine:
    frame, stack, unit, state = 0x108000, 0x107000, 0x210000, 0x211000
    def __init__(self, image, values):
        self.cpu = Uc(UC_ARCH_X86, UC_MODE_32)
        for base,size in ((0x400000,0x200000),(0x100000,0x10000),(0x200000,0x100000),(0x700000,0x10000)):
            self.cpu.mem_map(base,size)
        self.cpu.mem_write(0x400000,image)
        self.put(self.unit+0x68,self.state)
        upgrades_patch.validate_memory(self.cpu.mem_read,values)
        plan = fixes_patch.prepare(self.cpu.mem_read,self.cpu.mem_write,lambda n:0x700000,lambda a,n:None,
                                   fixes_settings(),upgrades=values)
        for a,_,b in plan+upgrades_patch.table_plan(values): self.cpu.mem_write(a,b)

    def put(self,a,v): self.cpu.mem_write(a,struct.pack('<I',v & 0xffffffff))
    def get(self,a): return struct.unpack('<I',self.cpu.mem_read(a,4))[0]
    def short(self,a,v): self.cpu.mem_write(a,struct.pack('<h',v))
    def run(self,start,end,**regs):
        c=self.cpu
        c.reg_write(UC_X86_REG_EBP,self.frame); c.reg_write(UC_X86_REG_ESP,self.stack)
        for name,value in dict({"EAX":0,"ECX":0,"EDX":0,"EBX":0x1234,"ESI":0x2345,"EDI":0x3456}, **regs).items():
            c.reg_write(globals()['UC_X86_REG_'+name],value)
        c.emu_start(start,end,count=100000)
        assert c.reg_read(UC_X86_REG_EIP)==end
        assert c.reg_read(UC_X86_REG_ESP)==self.stack
        assert c.reg_read(UC_X86_REG_EBP)==self.frame
        for name,value in (('EBX',0x1234),('ESI',0x2345),('EDI',0x3456)):
            assert c.reg_read(globals()['UC_X86_REG_'+name])==value
        return c.reg_read(UC_X86_REG_EAX)


@skipUnless(Uc and os.environ.get('KKND2_TEST_EXE'), 'Optional unicorn/pefile and KKND2_TEST_EXE required')
class NativeUpgradeTests(TestCase):
    @classmethod
    def setUpClass(cls):
        import hashlib
        from kknd2_editor.game_launcher import SUPPORTED_SHA256
        raw=Path(os.environ['KKND2_TEST_EXE']).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==SUPPORTED_SHA256
        cls.image=pefile.PE(data=raw).get_memory_mapped_image()

    def test_lab_destination_tier_initial_bill_bar_and_saved_game_resume(self):
        values=settings(**{f'lab_upgrade.{i}':1+i*0.2 for i in range(6)})
        e=Engine(self.image,values)
        for i in range(6): e.put(0x51b2c4+i*4,350-i*20)
        for race in range(3):
            for current in range(5):
                for lab_level in range(6):
                    e.put(e.unit+0x5c,99+race);e.short(e.state+0x4a,current)
                    e.put(e.frame-0x10,e.unit)
                    expected=round((350-lab_level*20)*values[f'lab_upgrade.{current+1}'])
                    self.assertEqual(e.run(0x4947cd,0x4947d5,ECX=lab_level),expected)
                    e.put(e.frame-4,e.unit);e.put(e.frame-8,0x23004c);e.short(0x23004a,lab_level)
                    self.assertEqual(e.run(0x494528,0x494536),expected)
                    e.put(e.frame-0x10,0x240000);e.put(0x240010,e.unit)
                    e.run(0x406e8b,0x406e93,EAX=lab_level)
                    self.assertEqual(e.cpu.reg_read(UC_X86_REG_ECX),expected)
        e.put(e.unit+0x5c,84); e.put(e.frame-0x10,e.unit)
        self.assertEqual(e.run(0x4947cd,0x4947d5,ECX=2),310)

    def test_ai_lab_cost_and_time_and_non_lab_unchanged(self):
        e=Engine(self.image,settings(**{'lab_upgrade.5':2}))
        e.put(e.frame-0x34,e.unit);e.put(e.frame-0x38,e.state);e.short(e.state+0x4a,4)
        for id,expected in ((99,(500,40)),(100,(500,40)),(101,(500,40)),(84,(250,20))):
            e.put(e.unit+0x5c,id);e.put(e.frame-0x14,250);e.put(e.frame-8,20)
            e.run(0x419dbc,0x419dc2)
            self.assertEqual((e.get(e.frame-0x14),e.get(e.frame-8)),expected)

    def test_repair_curve_uses_existing_speed_scaling(self):
        values=settings(**{f'repair_rate.{i}':2*(i+1) for i in range(6)})
        e=Engine(self.image,values);e.put(e.frame-4,e.state)
        for level in range(6):
            e.short(e.state+0x4a,level)
            for speed in (256,512,1024,2048):
                e.put(0x51058c,speed)
                e.run(0x4d5a89,0x4d5aa6)
                self.assertEqual(e.cpu.reg_read(UC_X86_REG_ECX),2*(level+1)*256*speed//512)

    def test_maximum_repair_rate_does_not_overflow_at_fast_speed(self):
        e=Engine(self.image,settings(**{'repair_rate.5':32}))
        e.put(e.frame-4,e.state);e.short(e.state+0x4a,5);e.put(0x51058c,2048)
        e.run(0x4d5a89,0x4d5aa6)
        self.assertEqual(e.cpu.reg_read(UC_X86_REG_ECX),128*256)

    def test_oil_yield_native_fixed_point_payout(self):
        e=Engine(self.image,settings(**{'oil_yield.5':3}))
        self.assertEqual(e.run(0x4ac0fe,0x4ac109,EAX=10000,ECX=5),30000)
        self.assertEqual(e.run(0x4ac0fe,0x4ac109,EAX=400,ECX=1),420)

    def test_production_uses_producer_class_tier_and_all_factions(self):
        values=settings(**{f'{row}.{level}':1+idx+level*0.1 for idx,row in enumerate(upgrades_patch.PRODUCTION_ROWS) for level in range(6)})
        e=Engine(self.image,values)
        e.put(e.frame-4,e.unit);e.put(e.frame-0x20,e.state)
        for id in range(72,84):
            for level in range(6):
                e.put(e.unit+0x5c,id);e.short(e.state+0x4a,level)
                factor=values[f'{upgrades_patch.PRODUCTION_ROWS[(id-72)//3]}.{level}']
                e.run(0x419a89,0x419a8f,EAX=100)
                self.assertEqual(e.get(e.state+0x44),round(100*factor))

    def test_ai_shared_construction_queue_uses_highest_tier_of_correct_class(self):
        e=Engine(self.image,settings(**{'outpost_speed.4':2,'armoury_speed.3':3}))
        ai,definition=0x250000,0x240000
        e.put(e.frame-0x3c,ai);e.put(e.frame-0x24,definition);e.put(ai,1)
        for category,id,head,level,expected in ((4,72,0x19e8,4,200),(5,81,0x2974,3,300)):
            e.short(definition+0xe4,category);e.put(e.unit+0x5c,id);e.short(e.state+0x4a,level)
            e.put(ai+head+0x30,e.unit);e.put(e.unit+0x30,ai+head)
            e.run(0x419c6d,0x419c77,EAX=100)
            self.assertEqual(struct.unpack('<h',e.cpu.mem_read(ai+0x4912,2))[0],expected)

    def test_placed_construction_rate_and_saved_bill_use_same_multiplier_once(self):
        values=settings(**{'outpost_speed.4':2,'armoury_speed.3':3})
        for race in range(3):
            for category,first,level,factor in ((4,72,4,2),(5,81,3,3),(6,81,3,3)):
                e=Engine(self.image,values)
                building,definition,record,other=0x240000,0x241000,0x242000,0x243000
                e.put(e.frame-0x28,building);e.put(e.frame-0x30,definition);e.put(e.frame-0x2c,record)
                e.put(building+0x60,definition);e.cpu.mem_write(building+0x2fc,b'\x01')
                e.put(definition+0xc,300);e.put(definition+0x7c,10);e.short(definition+0xe4,category)
                e.put(0x50e904,60)
                e.put(0x5c27d8,e.unit);e.put(e.unit,other);e.put(other,0x5c27d8)
                e.put(e.unit+0x5c,first+race);e.short(e.state+0x4a,level)
                e.cpu.mem_write(e.unit+0x2fc,b'\x01')
                # A higher-tier enemy must not supply our multiplier.
                e.put(other+0x5c,first+race);e.put(other+0x68,0x244000)
                e.short(0x24404a,5);e.cpu.mem_write(other+0x2fc,b'\x02')
                e.run(0x465281,0x4652be)
                rate=128*factor
                self.assertEqual(struct.unpack('<3h',e.cpu.mem_read(record+0xe,6)),(300,300,rate))
                # The existing load path reads the stored adjusted rate, with no
                # second multiplier. Stop at native billing's verified entry.
                e.put(e.frame-8,record);e.short(e.frame-0x14,32767);e.short(record+0xa,1)
                e.cpu.reg_write(UC_X86_REG_EBP,e.frame);e.cpu.reg_write(UC_X86_REG_ESP,e.stack)
                e.cpu.emu_start(0x460876,0x45eb67,count=10000)
                sp=e.cpu.reg_read(UC_X86_REG_ESP)
                self.assertEqual(e.get(sp+4)&65535,300)
                self.assertEqual(e.get(sp+8),rate)
                self.assertEqual(e.cpu.reg_read(UC_X86_REG_EDX),record+0x10)

    def test_player_bill_wrapper_preserves_abi_and_price(self):
        e=Engine(self.image,settings(**{'vehicle_speed.4':2}))
        menu,group=0x230000,0x231000
        e.put(menu+8,group);e.short(group+0x18,123)
        e.put(e.unit+0x5c,79);e.short(e.state+0x4a,4)
        calls=[]
        def hook(cpu,address,size,user):
            if address==0x4c56cf:
                self.assertEqual(cpu.reg_read(UC_X86_REG_ECX)&65535,123)
                sp=cpu.reg_read(UC_X86_REG_ESP)
                cpu.reg_write(UC_X86_REG_EAX,e.unit);cpu.reg_write(UC_X86_REG_EIP,e.get(sp));cpu.reg_write(UC_X86_REG_ESP,sp+4)
            elif address==0x45ee55:
                frame=cpu.reg_read(UC_X86_REG_EBP)
                calls.append((cpu.reg_read(UC_X86_REG_ECX),cpu.reg_read(UC_X86_REG_EDX)&65535,
                              struct.unpack('<6I',cpu.mem_read(frame+8,24))))
                cpu.reg_write(UC_X86_REG_EIP,0x45f0c5)
        e.cpu.hook_add(UC_HOOK_CODE,hook)
        e.cpu.mem_write(e.stack,struct.pack('<7I',0x101000,0x232000,500,100,7,8,9))
        e.cpu.reg_write(UC_X86_REG_ECX,menu);e.cpu.reg_write(UC_X86_REG_EDX,2)
        e.cpu.reg_write(UC_X86_REG_ESP,e.stack);e.cpu.reg_write(UC_X86_REG_EBP,e.frame)
        e.cpu.emu_start(0x45ee4f,0x101000,count=10000)
        self.assertEqual(calls,[(menu,2,(0x232000,500,200,7,8,9))])
        self.assertEqual(e.cpu.reg_read(UC_X86_REG_ESP),e.stack+28)
        self.assertEqual(e.cpu.reg_read(UC_X86_REG_EBP),e.frame)
