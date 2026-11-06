"""Bounded build fingerprints; no hooks, external diff, shells or remote operations."""
import hashlib
import os
from pathlib import Path
import shutil
import subprocess

EXCLUDED={".git",".project-builder",".venv","venv","node_modules","__pycache__",".pytest_cache",".superpowers","dist","build"}
def git_read(root, args):
    executable=shutil.which("git")
    if not executable:
        return None
    env=dict(os.environ)
    for key in tuple(env):
        if key.startswith("GIT_"):
            env.pop(key)
    result=subprocess.run([executable,"-c","core.fsmonitor=false","-c","core.hooksPath=" + os.devnull,
        "-c","submodule.recurse=false","-C",str(root),*args],env=env,capture_output=True,timeout=5,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name=="nt" else 0)
    return result.stdout if result.returncode == 0 else None

def build_id(root: Path):
    head=git_read(root,["rev-parse","--verify","HEAD"])
    files=git_read(root,["ls-files","-m","-o","--exclude-standard","-z"]) if head else None
    staged=git_read(root,["diff","--cached","--name-only","-z","HEAD"]) if head else None
    if files is not None and staged is not None:
        files += staged
    if head and files is not None:
        paths=[root/os.fsdecode(p) for p in files.split(b"\0") if p]
        paths=[p for p in paths if not set(p.relative_to(root).parts)&EXCLUDED]
        if not paths:
            return head.decode().strip()
    else:
        paths=[]
        for folder,dirs,names in os.walk(root,followlinks=False):
            dirs[:]=sorted(d for d in dirs if d not in EXCLUDED and not (Path(folder)/d).is_symlink())
            paths.extend(Path(folder)/name for name in sorted(names))
            if len(paths)>10000:
                raise ValueError("build fingerprint exceeds scope; commit or narrow the project")
    state=hashlib.sha256(head or b"unversioned")
    size=0
    for path in sorted(set(paths)):
        if path.is_symlink() or not path.is_file():
            raise ValueError("unverifiable symlink/deleted file in build; commit changes first")
        size+=path.stat().st_size
        if size>64*1024*1024:
            raise ValueError("dirty build exceeds 64MiB; commit changes first")
        state.update(str(path.relative_to(root)).encode())
        with path.open("rb") as stream:
            for block in iter(lambda:stream.read(65536),b""):
                state.update(block)
    return ("dirty:" if head else "unversioned:")+state.hexdigest()

