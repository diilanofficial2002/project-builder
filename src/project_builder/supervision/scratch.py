"""Owned scratch cleanup. Never accept caller-selected deletion roots."""
from contextlib import contextmanager
import os
from pathlib import Path
import stat
import time

from project_builder.platform_paths import reject_links


@contextmanager
def _pinned(path):
    """Windows rename/delete pin; POSIX cleanup below uses descriptor-relative traversal."""
    if os.name != "nt":
        yield
        return
    from .windows_job import _api
    import ctypes
    api = _api()
    handle = api.CreateFileW(str(path), 0x80, 3, None, 3, 0x02200000, None)
    if handle == ctypes.c_void_p(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        reject_links(path)
        yield
    finally:
        api.CloseHandle(handle)


def remove_scratch(root: Path, path: Path, token: str, max_entries=10000, max_seconds=5.0) -> None:
    """Bounded, no-follow deletion under a dedicated random scratch directory.

    Abort on any reparse/link or changed marker. Windows pins every ancestor and
    traversed directory against replacement; POSIX uses O_NOFOLLOW/openat.
    """
    if path.parent != root or path.name in {"", ".", ".."}:
        raise ValueError("scratch is not a direct child of the supervisor scratch root")
    reject_links(root)
    reject_links(path)
    if not path.exists():
        return
    deadline = time.monotonic() + max_seconds
    entries = [0]

    def budget():
        entries[0] += 1
        if entries[0] > max_entries or time.monotonic() > deadline:
            raise TimeoutError("scratch cleanup exceeded bounded traversal budget")

    def preflight(folder):
        budget()
        reject_links(folder)
        for item in folder.iterdir():
            budget()
            reject_links(item)
            if item.is_dir():
                preflight(item)

    # Preflight avoids a partially removed tree for ordinary detected escapes.
    preflight(path)
    if (path / ".owner").read_text(encoding="utf-8") != token:
        raise ValueError("scratch owner marker mismatch")

    if os.name == "nt":
        from contextlib import ExitStack
        def walk(folder):
            with _pinned(folder):
                for entry in folder.iterdir():
                    budget()
                    reject_links(entry)
                    if entry.is_dir():
                        walk(entry)
                    else:
                        entry.unlink()
            folder.rmdir()  # no recursion after releasing the directory pin
        with ExitStack() as stack:
            for parent in reversed(path.parents):
                stack.enter_context(_pinned(parent))
            walk(path)
    else:
        # Each parent descriptor anchors traversal even if its name is renamed.
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        def walk_at(parent_fd, name, expected_marker=False):
            fd = os.open(name, flags, dir_fd=parent_fd)
            try:
                if expected_marker:
                    marker = os.open(".owner", os.O_RDONLY | os.O_NOFOLLOW, dir_fd=fd)
                    with os.fdopen(marker) as stream:
                        if stream.read(256) != token:
                            raise ValueError("scratch owner marker mismatch")
                for entry in os.listdir(fd):
                    budget()
                    info = os.stat(entry, dir_fd=fd, follow_symlinks=False)
                    if stat.S_ISLNK(info.st_mode):
                        raise ValueError("symlink encountered during cleanup")
                    if stat.S_ISDIR(info.st_mode):
                        walk_at(fd, entry)
                    else:
                        os.unlink(entry, dir_fd=fd)
            finally:
                os.close(fd)
            os.rmdir(name, dir_fd=parent_fd)
        root_fd = os.open(root, flags)
        try:
            walk_at(root_fd, path.name, expected_marker=True)
        finally:
            os.close(root_fd)
