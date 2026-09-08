"""Launch the verified KWIPv3 build with in-memory limits; never patch disk files."""
from pathlib import Path
import ctypes as C
from ctypes import wintypes as W
import hashlib
import os
import struct
from .building_limits import BUILDINGS, validate

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


def launch_game(executable, values, dry_run=False):
    """Create our own suspended process, verify/patch, and only then resume it.

    dry_run verifies a real suspended process and terminates it without running
    a single game instruction. Used by the integration test, never by the UI.
    """
    if os.name != 'nt':
        raise OSError('The KWIPv3 launcher requires Windows.')
    exe = Path(executable).resolve()
    validate(values)
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
    si, pi = STARTUPINFO(), PROCESS_INFORMATION()
    si.cb = C.sizeof(si)
    # GUI executable: no command processor, shell, or console is involved.
    if not k.CreateProcessW(str(exe), C.create_unicode_buffer('"' + str(exe) + '"'),
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
            count = C.c_size_t()
            if not k.WriteProcessMemory(pi.hProcess, address, C.create_string_buffer(data), len(data), C.byref(count)) or count.value != len(data):
                raise C.WinError(C.get_last_error())

        changed = apply_limits(read, write, values)
        if not dry_run:
            if k.ResumeThread(pi.hThread) == 0xffffffff:
                raise C.WinError(C.get_last_error())
            resumed = True
        return {'pid': pi.dwProcessId, 'patched': changed, 'dry_run': dry_run}
    finally:
        # On any failure, only the child created above is terminated.
        if not resumed:
            k.TerminateProcess(pi.hProcess, 1)
            k.WaitForSingleObject(pi.hProcess, 5000)
        k.CloseHandle(pi.hThread)
        k.CloseHandle(pi.hProcess)
