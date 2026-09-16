"""Launch the verified KWIPv3 build with in-memory limits; never patch disk files."""
from pathlib import Path
import ctypes as C
from ctypes import wintypes as W
import hashlib
import os
import struct
from .building_limits import BUILDINGS, validate
from . import overrides_patch
from .overrides import validate as validate_overrides
from . import tech_unlocks, projectiles_patch, fixes_patch
from .fixes import validate as validate_fixes
from .fixes import FIXES
from .projectiles import validate as validate_projectiles
from .campaign import command_line
from . import unit_extensions, upgrades_patch
from .upgrades import validate as validate_upgrades

SUPPORTED_SHA256 = 'ebc91ca929e69c1529de9230d28ddb5c4b1534f13074458dd03b805677817d44'


def patch_plan(values):
    return [(spec['address'], struct.pack('<H', spec['default']), struct.pack('<H', values[key]))
            for key, spec in BUILDINGS.items() if values[key] != spec['default']]


def apply_limits(read, write, values):
    """Validate every original value first, then change only selected two-byte fields."""
    validate(values)
    for spec in BUILDINGS.values():
        if read(spec['address'], 2) != struct.pack('<H', spec['default']):
            raise ValueError('KWIPv3 memory does not match the supported build. No game will be started.')
    plan = patch_plan(values)
    for address, before, after in plan:
        write(address, after)
        if read(address, len(after)) != after:
            raise OSError(f'Building limit verification failed at {address:#x}.')
    return len(plan)


def apply_configuration(read, write, values, overrides, allocate, seal, unlocks=None, projectiles=None, fixes=None, extensions=None, upgrades=None):
    """Validate every feature's original sites before any process memory write."""
    validate(values)
    for spec in BUILDINGS.values():
        if read(spec['address'], 2) != struct.pack('<H', spec['default']):
            raise ValueError('KWIPv3 building data does not match the supported build.')
    plan = patch_plan(values)
    building_count = len(plan)
    if extensions is not None:
        plan.extend(unit_extensions.patch_plan(read, extensions))
    if unlocks is not None:
        tech_unlocks.validate(unlocks)
        tech_unlocks.validate_memory(read)
    if projectiles is not None:
        validate_projectiles(projectiles)
        projectiles_patch.validate_memory(read)
    fixes = fixes if fixes is not None else {k: s['default'] for k, s in FIXES.items()}
    validate_fixes(fixes)
    fixes_patch.validate_memory(read, fixes, values)
    upgrades_patch.validate_memory(read, upgrades, overrides)
    plan.extend(upgrades_patch.table_plan(upgrades))
    if overrides is not None:
        validate_overrides(overrides)
        overrides_patch.validate_memory(read)
        blob, _ = overrides_patch.stub_bundle(overrides)
        address = allocate(len(blob)) if blob else 0
        override_plan = overrides_patch.patch_plan(overrides, address)
        if blob:
            write(address, blob)
            if read(address, len(blob)) != blob:
                raise OSError('Override helper verification failed.')
            seal(address, len(blob))
        if upgrades_patch.changed(upgrades, 'lab_upgrade'):
            override_plan = [item for item in override_plan if item[0] != 0x494528]
        plan.extend(override_plan)
    if unlocks is not None:
        data, _ = tech_unlocks.table_bundle(unlocks)
        if data:
            address = allocate(len(data))
            if not 0 < address <= 0xffffffff - len(data):
                raise ValueError('Tech unlocks require a valid 32-bit allocation.')
            data, unlock_plan = tech_unlocks.table_bundle(unlocks, address)
            write(address, data)
            if read(address, len(data)) != data:
                raise OSError('Tech unlock table verification failed.')
            plan.extend(unlock_plan)
    if projectiles is not None:
        blob = projectiles_patch.lifetime_stub(projectiles)
        address = allocate(len(blob)) if blob else 0
        projectile_plan = projectiles_patch.patch_plan(projectiles, address)
        if blob:
            write(address, blob)
            if read(address, len(blob)) != blob:
                raise OSError('Projectile helper verification failed.')
            seal(address, len(blob))
        plan.extend(projectile_plan)
    plan.extend(fixes_patch.prepare(read, write, allocate, seal, fixes, values, upgrades))
    for address, before, after in plan:
        write(address, after)
        if read(address, len(after)) != after:
            raise OSError(f'Game patch verification failed at {address:#x}.')
    return building_count, len(plan) - building_count


def launch_game(executable, values, dry_run=False, overrides=None, unlocks=None, projectiles=None, fixes=None, campaign_config=None, extensions=None, upgrades=None):
    """Create our own suspended process, verify/patch, and only then resume it.

    dry_run verifies a real suspended process and terminates it without running
    a single game instruction. Used by the integration test, never by the UI.
    """
    if os.name != 'nt':
        raise OSError('The KWIPv3 launcher requires Windows.')
    exe = Path(executable).resolve()
    command = command_line(exe, campaign_config)
    validate(values)
    if overrides is not None:
        validate_overrides(overrides)
    if unlocks is not None:
        tech_unlocks.validate(unlocks)
    if projectiles is not None:
        validate_projectiles(projectiles)
    if fixes is not None:
        validate_fixes(fixes)
    if upgrades is not None:
        validate_upgrades(upgrades)
    if extensions is not None:
        unit_extensions.validate(extensions)
    if hashlib.sha256(exe.read_bytes()).hexdigest() != SUPPORTED_SHA256:
        raise ValueError('Unsupported KWIPv3.exe build. Its SHA-256 does not match the verified version; launch cancelled.')

    class STARTUPINFO(C.Structure):
        _fields_ = [('cb', W.DWORD), ('lpReserved', W.LPWSTR), ('lpDesktop', W.LPWSTR),
                    ('lpTitle', W.LPWSTR), ('dwX', W.DWORD), ('dwY', W.DWORD),
                    ('dwXSize', W.DWORD), ('dwYSize', W.DWORD), ('dwXCountChars', W.DWORD),
                    ('dwYCountChars', W.DWORD), ('dwFillAttribute', W.DWORD),
                    ('dwFlags', W.DWORD), ('wShowWindow', W.WORD), ('cbReserved2', W.WORD),
                    ('lpReserved2', C.POINTER(C.c_byte)), ('hStdInput', W.HANDLE),
                    ('hStdOutput', W.HANDLE), ('hStdError', W.HANDLE)]

    class PROCESS_INFORMATION(C.Structure):
        _fields_ = [('hProcess', W.HANDLE), ('hThread', W.HANDLE),
                    ('dwProcessId', W.DWORD), ('dwThreadId', W.DWORD)]

    k = C.WinDLL('kernel32', use_last_error=True)
    k.CreateProcessW.argtypes = [W.LPCWSTR, W.LPWSTR, C.c_void_p, C.c_void_p, W.BOOL,
                                W.DWORD, C.c_void_p, W.LPCWSTR, C.POINTER(STARTUPINFO), C.POINTER(PROCESS_INFORMATION)]
    k.CreateProcessW.restype = W.BOOL
    for name in ('ReadProcessMemory', 'WriteProcessMemory'):
        fn = getattr(k, name)
        fn.argtypes = [W.HANDLE, C.c_void_p, C.c_void_p, C.c_size_t, C.POINTER(C.c_size_t)]
        fn.restype = W.BOOL
    k.ResumeThread.argtypes, k.ResumeThread.restype = [W.HANDLE], W.DWORD
    k.TerminateProcess.argtypes, k.TerminateProcess.restype = [W.HANDLE, W.UINT], W.BOOL
    k.WaitForSingleObject.argtypes = [W.HANDLE, W.DWORD]
    k.CloseHandle.argtypes = [W.HANDLE]
    k.VirtualProtectEx.argtypes = [W.HANDLE, C.c_void_p, C.c_size_t, W.DWORD, C.POINTER(W.DWORD)]
    k.VirtualProtectEx.restype = W.BOOL
    k.VirtualAllocEx.argtypes = [W.HANDLE, C.c_void_p, C.c_size_t, W.DWORD, W.DWORD]
    k.VirtualAllocEx.restype = C.c_void_p
    k.FlushInstructionCache.argtypes = [W.HANDLE, C.c_void_p, C.c_size_t]
    k.FlushInstructionCache.restype = W.BOOL
    si, pi = STARTUPINFO(), PROCESS_INFORMATION()
    si.cb = C.sizeof(si)
    # GUI executable: no command processor, shell, or console is involved.
    if not k.CreateProcessW(str(exe), C.create_unicode_buffer(command),
                            None, None, False, 0x00000004, None, str(exe.parent), C.byref(si), C.byref(pi)):
        raise C.WinError(C.get_last_error())
    resumed = False
    try:
        def read(address, size):
            buffer, count = C.create_string_buffer(size), C.c_size_t()
            if not k.ReadProcessMemory(pi.hProcess, address, buffer, size, C.byref(count)) or count.value != size:
                raise C.WinError(C.get_last_error())
            return buffer.raw

        def write(address, data):
            count, old = C.c_size_t(), W.DWORD()
            if not k.VirtualProtectEx(pi.hProcess, address, len(data), 0x04, C.byref(old)):
                raise C.WinError(C.get_last_error())
            try:
                if not k.WriteProcessMemory(pi.hProcess, address, C.create_string_buffer(data), len(data), C.byref(count)) or count.value != len(data):
                    raise C.WinError(C.get_last_error())
            finally:
                ignored = W.DWORD()
                if not k.VirtualProtectEx(pi.hProcess, address, len(data), old.value, C.byref(ignored)):
                    raise C.WinError(C.get_last_error())
            if not k.FlushInstructionCache(pi.hProcess, address, len(data)):
                raise C.WinError(C.get_last_error())

        def allocate(size):
            address = k.VirtualAllocEx(pi.hProcess, None, size, 0x3000, 0x04)
            if not address:
                raise C.WinError(C.get_last_error())
            return address

        def seal(address, size):
            old = W.DWORD()
            if not k.VirtualProtectEx(pi.hProcess, address, size, 0x20, C.byref(old)):
                raise C.WinError(C.get_last_error())
            if not k.FlushInstructionCache(pi.hProcess, address, size):
                raise C.WinError(C.get_last_error())

        changed, override_count = apply_configuration(read, write, values, overrides, allocate, seal, unlocks, projectiles, fixes, extensions, upgrades)
        if not dry_run:
            if k.ResumeThread(pi.hThread) == 0xffffffff:
                raise C.WinError(C.get_last_error())
            resumed = True
        return {'pid': pi.dwProcessId, 'patched': changed, 'overrides': override_count, 'dry_run': dry_run}
    finally:
        # On any failure, only the child created above is terminated.
        if not resumed:
            k.TerminateProcess(pi.hProcess, 1)
            k.WaitForSingleObject(pi.hProcess, 5000)
        k.CloseHandle(pi.hThread)
        k.CloseHandle(pi.hProcess)
