"""Platform locations and non-following path checks; queries never create files."""
import os
from pathlib import Path
import stat
import sys


class PlatformPaths:
    @staticmethod
    def user_state_root() -> Path:
        if sys.platform == "win32":
            base = os.environ.get("LOCALAPPDATA")
            if not base or not Path(base).is_absolute():
                raise RuntimeError("LOCALAPPDATA must be an absolute user directory")
            return Path(base) / "project-builder"
        if sys.platform == "darwin":
            return Path.home() / "Library" / "Application Support" / "project-builder"
        raise RuntimeError("supported platforms are Windows and macOS")


def reject_links(path: Path) -> None:
    """Inspect every existing component, including Windows junction/reparse points."""
    path = path.absolute()
    for part in [*reversed(path.parents), path]:
        try:
            info = part.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise ValueError(f"link/reparse boundary is not trusted: {part}")


def verify_owner(path: Path) -> None:
    reject_links(path)
    if os.name != "nt":
        info = path.stat()
        if info.st_uid != os.getuid() or info.st_mode & 0o022:
            raise PermissionError(f"state must be owned by current user and not externally writable: {path}")
        return
    import ctypes as c
    from ctypes import wintypes as w
    adv = c.WinDLL("advapi32", use_last_error=True)
    kernel = c.WinDLL("kernel32", use_last_error=True)
    adv.GetNamedSecurityInfoW.argtypes = [w.LPWSTR, w.DWORD, w.DWORD, c.POINTER(c.c_void_p), c.c_void_p,
                                         c.c_void_p, c.c_void_p, c.POINTER(c.c_void_p)]
    adv.GetNamedSecurityInfoW.restype = w.DWORD
    adv.OpenProcessToken.argtypes = [w.HANDLE, w.DWORD, c.POINTER(w.HANDLE)]
    adv.GetTokenInformation.argtypes = [w.HANDLE, c.c_int, c.c_void_p, w.DWORD, c.POINTER(w.DWORD)]
    adv.EqualSid.argtypes = [c.c_void_p, c.c_void_p]
    kernel.GetCurrentProcess.restype = w.HANDLE
    kernel.CloseHandle.argtypes = [w.HANDLE]
    kernel.LocalFree.argtypes = [c.c_void_p]
    owner, descriptor, token = c.c_void_p(), c.c_void_p(), w.HANDLE()
    result = adv.GetNamedSecurityInfoW(str(path), 1, 1, c.byref(owner), None, None, None, c.byref(descriptor))
    if result:
        raise c.WinError(result)
    try:
        if not adv.OpenProcessToken(kernel.GetCurrentProcess(), 8, c.byref(token)):
            raise c.WinError(c.get_last_error())
        size = w.DWORD()
        adv.GetTokenInformation(token, 1, None, 0, c.byref(size))
        buffer = c.create_string_buffer(size.value)
        if not adv.GetTokenInformation(token, 1, buffer, size, c.byref(size)):
            raise c.WinError(c.get_last_error())
        user_sid = c.cast(buffer, c.POINTER(c.c_void_p))[0]
        if not adv.EqualSid(owner, user_sid):
            raise PermissionError(f"state owner differs from current user: {path}")
    finally:
        if token:
            kernel.CloseHandle(token)
        kernel.LocalFree(descriptor)
