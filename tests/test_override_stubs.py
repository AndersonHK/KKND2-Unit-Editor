"""Optional x86 execution tests: install unicorn to run; editor needs only stdlib."""
import struct
from unittest import TestCase, skipUnless
from support import editor
from kknd2_editor.overrides import OVERRIDES
from kknd2_editor import overrides_patch as patch
try:
    from unicorn import Uc, UC_ARCH_X86, UC_MODE_32
    from unicorn.x86_const import (UC_X86_REG_EAX, UC_X86_REG_ECX, UC_X86_REG_EDX,
                                  UC_X86_REG_EBP, UC_X86_REG_ESP)
except ImportError:
    Uc = None


@skipUnless(Uc, 'Optional unicorn emulator is not installed')
class StubTests(TestCase):
    def execute(self, code, *, speed=512, accumulator=0, increment=0, payout=400, index=0):
        cpu = Uc(UC_ARCH_X86, UC_MODE_32)
        for address in (0x100000, 0x200000, 0x300000, 0x510000):
            cpu.mem_map(address, 0x10000)
        def word(address, value):
            cpu.mem_write(address, struct.pack('<I', value))
        frame, stack, unit = 0x208000, 0x207000, 0x300000
        word(0x51058C, speed)
        word(frame - 0x10, unit)
        word(frame - 0x14, unit + 0x1000)
        word(unit + 0x1A8, accumulator)
        word(unit + 0x1000 + 0x1A8, payout)
        word(frame - 8, increment)
        word(frame - 12, index)
        word(stack, 0x101000)
        for register, value in ((UC_X86_REG_EAX, 0x123), (UC_X86_REG_ECX, 0x456),
                                (UC_X86_REG_EDX, 0x789), (UC_X86_REG_EBP, frame), (UC_X86_REG_ESP, stack)):
            cpu.reg_write(register, value)
        cpu.mem_write(0x100000, code)
        cpu.emu_start(0x100000, 0x101000, count=100)
        self.assertEqual(cpu.reg_read(UC_X86_REG_ESP), stack + 4)
        self.assertEqual(cpu.reg_read(UC_X86_REG_EBP), frame)
        return [cpu.reg_read(r) for r in (UC_X86_REG_EAX, UC_X86_REG_ECX, UC_X86_REG_EDX)]

    def test_loading_fractional_capacity_and_wide_multiply(self):
        values = {k: s['default'] for k, s in OVERRIDES.items()}
        values['tanker_capacity'] = 401
        for rate in (1, 32768, 65536, 1048576):
            values['rig_loading_rate'] = rate
            for speed in (128, 512, 1536, 65536, 0x7FFFFFFF):
                for current in (0, 100*256+128, 400*256+250, 401*256):
                    result = self.execute(patch.loading_stub(values), speed=speed, accumulator=current)
                    self.assertEqual(result, [min((speed * rate) >> 16, 401*256-current), 0x456, 0x789])

    def test_fractional_debit_conserves_whole_oil(self):
        for previous, increment in ((0, 128), (128, 128), (255, 1), (511, 129), (400*256, 3*256)):
            result = self.execute(patch.debit_stub(), accumulator=previous+increment, increment=increment)
            self.assertEqual(result, [0x123, 0x456, ((previous+increment)>>8) - (previous>>8)])

    def test_unloading_caps_partial_payout_and_preserves_registers(self):
        values = {k: s['default'] for k, s in OVERRIDES.items()}
        for rate in (512, 4096, 65536, 1048576):
            values['powerplant_unloading_rate'] = rate
            for speed in (128, 512, 1536, 65536, 0x7FFFFFFF):
                for payout in (1, 35, 500, 12500):
                    result = self.execute(patch.unloading_stub(values), speed=speed, payout=payout)
                    self.assertEqual(result, [0x123, min((speed*rate)>>16, payout), 0x789])

    def test_research_steps_all_six_indices_and_zero_step(self):
        for step in (0, 1, 20, 40, 1000):
            for index in range(6):
                self.assertEqual(self.execute(patch.research_step_stub(step), index=index),
                                 [0x123, (5-index)*step, 0x789])
