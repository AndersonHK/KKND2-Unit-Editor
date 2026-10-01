"""Exercise cursor, command delivery and Fight's previously unfiltered fallback."""
import os
import struct
from unittest import TestCase, skipUnless
import test_fixes_native as native_tests
from test_fixes_native import World, Uc
from test_fixes import settings
from kknd2_editor import fixes_patch
if Uc:
    from unicorn import UC_HOOK_CODE
    from unicorn.x86_const import UC_X86_REG_ECX, UC_X86_REG_EDX, UC_X86_REG_EBP, UC_X86_REG_ESP, UC_X86_REG_EIP


@skipUnless(Uc and os.environ.get('KKND2_TEST_EXE'), 'Native emulation dependencies required')
class TargetOrderTests(TestCase):
    @classmethod
    def setUpClass(cls):
        native_tests.NativeFixesTests.setUpClass()
        cls.image = native_tests.NativeFixesTests.image

    def link(self, w, *units):
        sentinel = 0x5c27d8
        w.put(sentinel, units[0] if units else sentinel)
        for a, b in zip(units, (*units[1:], sentinel)):
            w.put(a, b)

    def intercept(self, w, name, cleanup=0):
        address = w.get(0x700000 + fixes_patch.load_payload()['exports'][name])
        calls = []
        def hook(cpu, at, size, user):
            if at == address:
                calls.append((cpu.reg_read(UC_X86_REG_ECX), cpu.reg_read(UC_X86_REG_EDX)))
                w.returned(1, cleanup)
        w.cpu.hook_add(UC_HOOK_CODE, hook)
        return calls

    def test_failed_scans_clear_rejected_candidate_even_without_priority(self):
        for opts in (dict(zero_damage_filter=True), dict(acquisition_range=True)):
            for entry in (0x4a1893, 0x4a2039, 0x4a2455):
                w = World(self.image, settings(**opts), damages=(0,0,0,0,0))
                bad = w.add(0, hidden=True)
                self.link(w, w.unit, bad)
                w.cpu.mem_write(w.output, struct.pack('<4I',0,bad,1,0))
                self.assertEqual(w.run(entry), 0)
                self.assertEqual(bytes(w.cpu.mem_read(w.output,16)), bytes(16))

    def test_fight_fallback_filters_every_candidate_and_keeps_sight(self):
        for turret in (False, True):
            for priority in (False, True):
                w = World(self.image, settings(zero_damage_filter=True, damage_priority=priority),
                          damages=(0,20,30,0,0), turret=turret)
                bad = w.add(0, (17,16))
                good = w.add(1, (27,16))
                self.link(w, w.unit, bad, good)
                self.assertEqual(w.run(0x4a2455), 1)
                self.assertEqual(w.get(w.output+4), good)
                w.hidden.add(good)
                self.assertEqual(w.run(0x4a2455), 0)
                self.assertEqual(w.get(w.output+4), 0)
                w.hidden.clear()
                w.put(w.unit+0x1000+0x20, 8)
                self.assertEqual(w.run(0x4a2455), 0)

    def test_fight_prefers_in_range_and_retains_vanilla_sight_fallback(self):
        for acquisition in (False, True):
            w = World(self.image, settings(zero_damage_filter=True, damage_priority=True,
                                          acquisition_range=acquisition))
            close = w.add(0)
            far = w.add(2, (27,16))
            self.link(w, w.unit, far, close)
            self.assertEqual(w.run(0x4a2455), 1)
            self.assertEqual(w.get(w.output+4), close)
        w = World(self.image, settings(zero_damage_filter=True, acquisition_range=True))
        far = w.add(2, (28,16))
        self.link(w, w.unit, far)
        self.assertEqual(w.run(0x4a2455), 1)
        self.assertEqual(w.get(w.output+4), far)

    def test_manual_compatibility_blocks_zero_without_blocking_positive_pursuit(self):
        for turret in (False, True):
            w = World(self.image, settings(zero_damage_filter=True), turret=turret)
            target = w.add(1, (27,16))
            w.cpu.mem_write(w.output, struct.pack('<4I',0,target,1,0))
            self.assertEqual(w.run(0x4a9b40), 1)
            w.set_damage((10,0,30,5,1))
            self.assertEqual(w.run(0x4a9b40), 0)
            # Neither the target descriptor nor another unit's weapon is edited.
            self.assertEqual(w.get(w.output+4), target)

    def test_native_pursuit_branch_abandons_invalid_order(self):
        for zero in (False, True):
            w=World(self.image,settings(zero_damage_filter=True),damages=(10,0 if zero else 20,30,5,1))
            target=w.add(1,(27,16))
            w.cpu.mem_write(w.unit+0x144,struct.pack('<4I',0,target,1,0))
            frame=w.stack
            w.put(frame-8,w.unit)
            w.cpu.reg_write(UC_X86_REG_EBP,frame)
            w.cpu.reg_write(UC_X86_REG_ESP,frame-0x40)
            calls=[]
            def hook(cpu,at,size,user):
                if at in (0x4a39e9,0x47e570):
                    calls.append(at);w.returned(0)
            w.cpu.hook_add(UC_HOOK_CODE,hook)
            w.cpu.emu_start(0x4ce5a0,0x4ce5cc,count=10000)
            self.assertEqual(w.cpu.reg_read(UC_X86_REG_EIP),0x4ce5cc)
            self.assertEqual(calls,[0x4a39e9 if zero else 0x47e570])

    def test_native_fight_caller_cannot_keep_failed_scan_output(self):
        for priority in (False,True):
            w=World(self.image,settings(zero_damage_filter=True,damage_priority=priority),
                    damages=(0,0,0,0,0),turret=True)
            bad=w.add(1)
            self.link(w,w.unit,bad)
            w.cpu.reg_write(UC_X86_REG_ECX,w.unit)
            w.cpu.reg_write(UC_X86_REG_ESP,w.stack)
            w.cpu.emu_start(0x4834a0,0x4836b4,count=300000)
            self.assertEqual(w.cpu.reg_read(UC_X86_REG_EIP),0x4836b4)
            self.assertEqual(bytes(w.cpu.mem_read(w.unit+0x144,16)),bytes(16))

    def test_cursor_and_click_agree_for_single_and_mixed_selection(self):
        w = World(self.image, settings(zero_damage_filter=True), damages=(10,0,0,0,0))
        attacker = w.unit
        bad = w.add(1)
        other = w.add(0, player=1)
        self.link(w, attacker, other, bad)
        w.cpu.mem_write(0x565418, struct.pack('<h',10))
        w.cpu.mem_write(attacker+0x226,struct.pack('<h',10))
        controller=0x260000
        w.put(controller+0x24,bad)
        cursors=self.intercept(w,'original_cursor')
        orders=self.intercept(w,'original_order',4)
        w.unit=controller; w.output=0x1e0
        w.run(0x461a90)
        self.assertEqual(cursors[-1],(controller,0x214))
        w.output=6
        self.assertEqual(w.run(0x46319e,bad),0)
        self.assertEqual(orders,[])
        # Adding a selected, armed unit that can damage vehicles enables attack.
        w.cpu.mem_write(other+0x226,struct.pack('<h',10))
        w.put(other+0x1000+0x64,0x270000)
        w.cpu.mem_write(0x270018,struct.pack('<5h',0,20,0,0,0))
        w.output=0x1e0;w.run(0x461a90)
        self.assertEqual(cursors[-1],(controller,0x1e0))
        w.output=6;self.assertEqual(w.run(0x46319e,bad),1)
        self.assertEqual(len(orders),1)
        # Support units without weapons do not falsely enable the cursor.
        w.put(other+0x1000+0x64,0)
        w.output=0x1e0;w.run(0x461a90)
        self.assertEqual(cursors[-1][1],0x214)
        # Other cursor actions and non-attack orders still reach native code.
        w.output=0x188;w.run(0x461a90)
        self.assertEqual(cursors[-1][1],0x188)
        w.output=0x16;w.run(0x46319e,bad)
        self.assertEqual(len(orders),2)

    def test_group_command_rejects_only_incapable_recipient_and_preserves_shared_order(self):
        for handler in (0x4db808,0x487b0b,0x4af422,0x4ac504):
            w=World(self.image,settings(zero_damage_filter=True),damages=(10,0,30,5,1))
            attacker=w.unit;target=w.add(1)
            script,argument,command=0x260000,0x261000,0x262000
            w.put(attacker+0x58,script);w.put(script+0x34,handler);w.put(script+0x3c,attacker)
            w.put(argument+4,command)
            w.cpu.mem_write(command+0xa,struct.pack('<h',6))
            w.put(command+0x1c,target);w.put(command+0x20,1)
            before=bytes(w.cpu.mem_read(command,0x40))
            calls=self.intercept(w,'original_event',8)
            w.unit=0;w.output=0x30
            self.assertEqual(w.run(0x45bc10,argument,script),0)
            self.assertEqual(calls,[])
            self.assertEqual(bytes(w.cpu.mem_read(command,0x40)),before)
            w.set_damage((10,20,30,5,1))
            self.assertEqual(w.run(0x45bc10,argument,script),1)
            self.assertEqual(len(calls),1)
            # Other events and stale IDs follow native handling, not our damage lookup.
            w.set_damage((10,0,30,5,1));w.output=6
            w.run(0x45bc10,argument,script)
            w.output=0x30;w.put(command+0x20,99)
            w.run(0x45bc10,argument,script)
            self.assertEqual(len(calls),3)
