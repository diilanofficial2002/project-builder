"""Build on the target OS. Never cross-label a Windows executable as macOS."""
from pathlib import Path
import subprocess
import sys

root=Path(__file__).resolve().parents[1]
if sys.platform not in {"win32","darwin"}: raise SystemExit("Build on Windows or macOS")
subprocess.run([sys.executable,"-m","PyInstaller","--noconfirm","--clean","--onedir",
    "--name","project-builder","--paths",str(root/"src"),
    "--distpath",str(root/"build"/"runtime"),"--workpath",str(root/"build"/"pyinstaller"),
    "--specpath",str(root/"build"),"--collect-data","mcp","--copy-metadata","mcp",
    "--hidden-import","project_builder.supervision.watchdog",
    "--hidden-import","project_builder.transport.server",str(root/"scripts"/"runtime_entry.py")],check=True,cwd=root)
