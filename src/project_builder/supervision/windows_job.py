"""Windows native containment: suspended CreateProcess -> Job assignment -> resume.

No shell, inherited Job handle, breakaway flag, visible console, or output pipe.
Only the NUL standard-stream handle is inherited using an explicit handle list.
"""
import ctypes as c
from ctypes import wintypes as w
import os
import subprocess
import time

import psutil


class STARTUPINFO(c.Structure):
    _fields_ = [("cb", w.DWORD), ("lpReserved", w.LPWSTR), ("lpDesktop", w.LPWSTR),
                ("lpTitle", w.LPWSTR), ("dwX", w.DWORD), ("dwY", w.DWORD),
                ("dwXSize", w.DWORD), ("dwYSize", w.DWORD), ("dwXCountChars", w.DWORD),
                ("dwYCountChars", w.DWORD), ("dwFillAttribute", w.DWORD), ("dwFlags", w.DWORD),
                ("wShowWindow", w.WORD), ("cbReserved2", w.WORD), ("lpReserved2", c.c_void_p),
                ("hStdInput", w.HANDLE), ("hStdOutput", w.HANDLE), ("hStdError", w.HANDLE)]


class STARTUPINFOEX(c.Structure):
    _fields_ = [("StartupInfo", STARTUPINFO), ("lpAttributeList", c.c_void_p)]


class PROCESS_INFORMATION(c.Structure):
    _fields_ = [("hProcess", w.HANDLE), ("hThread", w.HANDLE), ("dwProcessId", w.DWORD), ("dwThreadId", w.DWORD)]


class SECURITY_ATTRIBUTES(c.Structure):
    _fields_ = [("nLength", w.DWORD), ("lpSecurityDescriptor", c.c_void_p), ("bInheritHandle", w.BOOL)]


class BASIC_LIMIT(c.Structure):
    _fields_ = [("PerProcessUserTimeLimit", c.c_longlong), ("PerJobUserTimeLimit", c.c_longlong),
                ("LimitFlags", w.DWORD), ("MinimumWorkingSetSize", c.c_size_t),
                ("MaximumWorkingSetSize", c.c_size_t), ("ActiveProcessLimit", w.DWORD),
                ("Affinity", c.c_size_t), ("PriorityClass", w.DWORD), ("SchedulingClass", w.DWORD)]


class IO_COUNTERS(c.Structure):
    _fields_ = [(name, c.c_ulonglong) for name in ("ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
                                                "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]


class EXTENDED_LIMIT(c.Structure):
    _fields_ = [("BasicLimitInformation", BASIC_LIMIT), ("IoInfo", IO_COUNTERS),
                ("ProcessMemoryLimit", c.c_size_t), ("JobMemoryLimit", c.c_size_t),
                ("PeakProcessMemoryUsed", c.c_size_t), ("PeakJobMemoryUsed", c.c_size_t)]


class ACCOUNTING(c.Structure):
    _fields_ = [("TotalUserTime", c.c_longlong), ("TotalKernelTime", c.c_longlong),
                ("ThisPeriodTotalUserTime", c.c_longlong), ("ThisPeriodTotalKernelTime", c.c_longlong),
                ("TotalPageFaultCount", w.DWORD), ("TotalProcesses", w.DWORD),
                ("ActiveProcesses", w.DWORD), ("TotalTerminatedProcesses", w.DWORD)]


def _api():
    k = c.WinDLL("kernel32", use_last_error=True)
    signatures = {
        "CreateJobObjectW": ([c.c_void_p, w.LPCWSTR], w.HANDLE),
        "SetInformationJobObject": ([w.HANDLE, c.c_int, c.c_void_p, w.DWORD], w.BOOL),
        "QueryInformationJobObject": ([w.HANDLE, c.c_int, c.c_void_p, w.DWORD, c.c_void_p], w.BOOL),
        "AssignProcessToJobObject": ([w.HANDLE, w.HANDLE], w.BOOL),
        "IsProcessInJob": ([w.HANDLE, w.HANDLE, c.POINTER(w.BOOL)], w.BOOL),
        "OpenJobObjectW": ([w.DWORD, w.BOOL, w.LPCWSTR], w.HANDLE),
        "TerminateJobObject": ([w.HANDLE, w.UINT], w.BOOL),
        "TerminateProcess": ([w.HANDLE, w.UINT], w.BOOL),
        "ResumeThread": ([w.HANDLE], w.DWORD),
        "CloseHandle": ([w.HANDLE], w.BOOL),
        "WaitForSingleObject": ([w.HANDLE, w.DWORD], w.DWORD),
        "GetExitCodeProcess": ([w.HANDLE, c.POINTER(w.DWORD)], w.BOOL),
        "CreateFileW": ([w.LPCWSTR, w.DWORD, w.DWORD, c.c_void_p, w.DWORD, w.DWORD, w.HANDLE], w.HANDLE),
        "InitializeProcThreadAttributeList": ([c.c_void_p, w.DWORD, w.DWORD, c.POINTER(c.c_size_t)], w.BOOL),
        "UpdateProcThreadAttribute": ([c.c_void_p, w.DWORD, c.c_size_t, c.c_void_p, c.c_size_t, c.c_void_p, c.c_void_p], w.BOOL),
        "DeleteProcThreadAttributeList": ([c.c_void_p], None),
        "CreateProcessW": ([w.LPCWSTR, w.LPWSTR, c.c_void_p, c.c_void_p, w.BOOL, w.DWORD,
                            c.c_void_p, w.LPCWSTR, c.c_void_p, c.POINTER(PROCESS_INFORMATION)], w.BOOL),
    }
    for name, (args, result) in signatures.items():
        function = getattr(k, name)
        function.argtypes, function.restype = args, result
    return k


def _check(result):
    if not result:
        raise c.WinError(c.get_last_error())
    return result


class WindowsJob:
    """Owns stable kernel handles; construction returns the workload still suspended."""
    def __init__(self, spec, handle_id):
        self.k = _api()
        self.job = self.process = self.thread = None
        self.pid = 0
        self.process_group_id = None
        self.killed = False
        startup, info = STARTUPINFOEX(), PROCESS_INFORMATION()
        startup.StartupInfo.cb = c.sizeof(startup)
        startup.StartupInfo.dwFlags = 0x101  # USESTDHANDLES | USESHOWWINDOW(SW_HIDE)
        attribute_buffer = None
        attribute_initialized = False
        nul = None
        try:
            self.job = _check(self.k.CreateJobObjectW(None, "Local\\project-builder-" + handle_id))
            limits = EXTENDED_LIMIT()
            limits.BasicLimitInformation.LimitFlags = 0x2000  # KILL_ON_JOB_CLOSE only; NO breakaway
            _check(self.k.SetInformationJobObject(self.job, 9, c.byref(limits), c.sizeof(limits)))
            security = SECURITY_ATTRIBUTES(c.sizeof(SECURITY_ATTRIBUTES), None, True)
            nul = self.k.CreateFileW("NUL", 0xC0000000, 3, c.byref(security), 3, 0, None)
            if nul == c.c_void_p(-1).value:
                nul = None
                raise c.WinError(c.get_last_error())
            startup.StartupInfo.hStdInput = startup.StartupInfo.hStdOutput = startup.StartupInfo.hStdError = nul
            size = c.c_size_t()
            self.k.InitializeProcThreadAttributeList(None, 2, 0, c.byref(size))
            attribute_buffer = c.create_string_buffer(size.value)
            startup.lpAttributeList = c.cast(attribute_buffer, c.c_void_p)
            _check(self.k.InitializeProcThreadAttributeList(startup.lpAttributeList, 2, 0, c.byref(size)))
            attribute_initialized = True
            handles = (w.HANDLE * 1)(nul)
            _check(self.k.UpdateProcThreadAttribute(startup.lpAttributeList, 0, 0x20002,
                                                   handles, c.sizeof(handles), None, None))
            jobs = (w.HANDLE * 1)(self.job)
            # Windows 10+: atomic Job assignment at creation also covers a parent
            # crash before any post-CreateProcess user-mode instruction. No fallback.
            _check(self.k.UpdateProcThreadAttribute(startup.lpAttributeList, 0, 0x2000D,
                                                   jobs, c.sizeof(jobs), None, None))
            # list2cmdline is CPython's CRT argv encoding, never shell interpolation.
            command = c.create_unicode_buffer(subprocess.list2cmdline([str(spec.executable), *spec.argv]))
            env = dict(os.environ)
            for key, value in spec.env.items():
                for existing in list(env):
                    if existing.upper() == key.upper():
                        del env[existing]
                env[key] = value
            environment = c.create_unicode_buffer("\0".join(f"{key}={value}" for key, value in sorted(env.items(), key=lambda item: item[0].upper())) + "\0\0")
            flags = 0x4 | 0x8000000 | 0x400 | 0x80000  # SUSPENDED, NO_WINDOW, UNICODE_ENV, EXTENDED_STARTUPINFO
            _check(self.k.CreateProcessW(str(spec.executable), command, None, None, True, flags,
                                        environment, str(spec.cwd), c.byref(startup), c.byref(info)))
            self.process, self.thread, self.pid = info.hProcess, info.hThread, info.dwProcessId
            member = w.BOOL()
            _check(self.k.IsProcessInJob(self.process, self.job, c.byref(member)))
            if not member.value:
                raise RuntimeError("atomic Job assignment could not be verified")
            self.started = psutil.Process(self.pid).create_time()
        except BaseException:
            if self.process:
                # Even failed Job assignment never lets the suspended child execute.
                self.k.TerminateProcess(self.process, 1)
                self.k.WaitForSingleObject(self.process, 5000)
            self.close()
            raise
        finally:
            if attribute_initialized:
                self.k.DeleteProcThreadAttributeList(startup.lpAttributeList)
            if nul:
                self.k.CloseHandle(nul)

    def resume(self):
        if self.k.ResumeThread(self.thread) == 0xFFFFFFFF:
            raise c.WinError(c.get_last_error())
        self.k.CloseHandle(self.thread)
        self.thread = None

    def poll(self):
        if self.k.WaitForSingleObject(self.process, 0) == 0x102:
            return None
        code = w.DWORD()
        _check(self.k.GetExitCodeProcess(self.process, c.byref(code)))
        return code.value

    def active(self):
        accounting = ACCOUNTING()
        _check(self.k.QueryInformationJobObject(self.job, 1, c.byref(accounting), c.sizeof(accounting), None))
        return accounting.ActiveProcesses

    def stop(self, grace_seconds=5.0):
        # Console-less generic executables have no universal safe graceful signal.
        # Give a bounded natural-exit grace, then terminate the owned Job atomically.
        end = time.monotonic() + grace_seconds
        while self.active() and time.monotonic() < end:
            time.sleep(0.02)
        if self.active():
            _check(self.k.TerminateJobObject(self.job, 1))
        end = time.monotonic() + 5
        while self.active() and time.monotonic() < end:
            time.sleep(0.01)
        if self.active():
            raise TimeoutError("owned Job did not become empty")
        self.killed = True

    def close(self):
        for name in ("job", "thread", "process"):
            handle = getattr(self, name)
            if handle:
                self.k.CloseHandle(handle)
                setattr(self, name, None)


def reconcile_job(handle_id):
    """Only after persisted launcher identity is gone: check/empty its named Job."""
    api = _api()
    job = api.OpenJobObjectW(0x4 | 0x8, False, "Local\\project-builder-" + handle_id)
    if not job:
        error = c.get_last_error()
        if error == 2:  # object gone: all handles closed and associated processes exited
            return
        raise c.WinError(error)
    try:
        _check(api.TerminateJobObject(job, 1))
        end = time.monotonic() + 5
        while True:
            accounting = ACCOUNTING()
            _check(api.QueryInformationJobObject(job, 1, c.byref(accounting), c.sizeof(accounting), None))
            if accounting.ActiveProcesses == 0:
                return
            if time.monotonic() >= end:
                raise TimeoutError("crashed launcher's Job still has live processes")
            time.sleep(0.02)
    finally:
        api.CloseHandle(job)
