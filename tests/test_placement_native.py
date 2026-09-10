"""Execute the actual placement routine against a small synthetic world."""
import os, struct
from unittest import TestCase, skipUnless
from support import editor
from pathlib import Path
try:
    import pefile
    from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
    from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_ECX, UC_X86_REG_EDX, UC_X86_REG_ESP, UC_X86_REG_EIP
except ImportError:
    Uc = None
from kknd2_editor.overrides import OVERRIDES
from kknd2_editor.overrides_patch import patch_plan
from kknd2_editor.unlock_data import UNLOCKS
image = None
checks=0
def execute(reach,delta,owned=True,terrain=True,unit='UNIT_SURV_OUTPOST',origin=64):
 global checks
 cpu=Uc(UC_ARCH_X86, UC_MODE_32)
 cpu.mem_map(0x400000,0x200000);cpu.mem_write(0x400000,image)
 cpu.mem_map(0x100000,0x10000);cpu.mem_map(0x200000,0x10000)
 def put(a,v):cpu.mem_write(a,struct.pack('<I',v))
 values={k:s['default'] for k,s in OVERRIDES.items()};values['building_placement_range']=reach
 for a,_,after in patch_plan(values):cpu.mem_write(a,after)
 # 1x1 preview footprint, one qualifying friendly base tile.
 enum=UNLOCKS[unit]['enum']
 definition=0x52bed8+enum*0x110
 build=struct.unpack('<I',cpu.mem_read(definition+0xe0,4))[0]
 put(build+0x14,0xffffffff)
 put(0x200000,0x201000);put(0x201070,0x202000)
 put(0x203060,0x204000);put(0x204098,0x80)
 put(0x55eb20,128);put(0x55eaf0,128)
 funcs={0x444850,0x40393c,0x44f99b,0x4447ac,0x47d9d6,0x4672f2}
 def hook(cpu,address,size,_):
  if address not in funcs:return
  result,cleanup=0,0
  if address==0x444850:
   x=cpu.reg_read(UC_X86_REG_ECX);y=cpu.reg_read(UC_X86_REG_EDX)
   result=0x203000 if (x,y)==(origin+delta,origin) else 0
  elif address==0x44f99b:result=int(owned)
  elif address in (0x4447ac,0x47d9d6):result=int(terrain);cleanup=4
  sp=cpu.reg_read(UC_X86_REG_ESP);ret=struct.unpack('<I',cpu.mem_read(sp,4))[0]
  cpu.reg_write(UC_X86_REG_EAX,result);cpu.reg_write(UC_X86_REG_ESP,sp+4+cleanup);cpu.reg_write(UC_X86_REG_EIP,ret)
 cpu.hook_add(UC_HOOK_CODE,hook)
 stack=0x108000
 cpu.mem_write(stack,struct.pack('<6I',0x101000,origin<<13,1,1,enum,0))
 cpu.reg_write(UC_X86_REG_ESP,stack);cpu.reg_write(UC_X86_REG_ECX,0x200000);cpu.reg_write(UC_X86_REG_EDX,origin<<13)
 cpu.emu_start(0x466e17,0x101000,count=2000000)
 result=cpu.reg_read(UC_X86_REG_EAX)
 assert cpu.reg_read(UC_X86_REG_EIP)==0x101000
 checks+=1
 return result
@skipUnless(Uc and os.environ.get('KKND2_TEST_EXE'), 'Optional pefile/unicorn and KKND2_TEST_EXE required')
class NativePlacementTests(TestCase):
    def test_real_routine_boundaries_ownership_and_terrain(self):
        global image
        exe = pefile.PE(os.environ['KKND2_TEST_EXE'])
        import hashlib
        from kknd2_editor.game_launcher import SUPPORTED_SHA256
        self.assertEqual(hashlib.sha256(Path(os.environ['KKND2_TEST_EXE']).read_bytes()).hexdigest(), SUPPORTED_SHA256)
        image = exe.get_memory_mapped_image()
        for unit in ('UNIT_SURV_OUTPOST','UNIT_SURV_TOWER1','UNIT_ROBOT_TOWER3'):
         for reach in (1,5,10,32):
          for sign in (-1,1):
           assert execute(reach,sign*reach,unit=unit)==1,(unit,reach,sign)
           assert execute(reach,sign*(reach+1),unit=unit)==0,(unit,reach,sign)
          assert execute(reach,reach,owned=False,unit=unit)==0
          assert execute(reach,reach,terrain=False,unit=unit)==0
