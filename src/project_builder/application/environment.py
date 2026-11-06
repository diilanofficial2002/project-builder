"""Inspect version constraints and give project-local instructions; never install globally."""
import platform
import re
import shutil
import sys
import tomllib
from pathlib import Path


def environment_plan(root, *, system=None):
    root=Path(root); system=system or platform.system(); pins={}; constraints=[]
    for name in (".python-version","runtime.txt"):
        path=root/name
        if path.is_file() and not path.is_symlink():
            value=path.read_text(encoding="utf-8").strip().removeprefix("python-")
            if re.fullmatch(r"\d+\.\d+\.\d+",value): pins[name]=value
            else: constraints.append({"source":name,"constraint":value})
    project=root/"pyproject.toml"
    if project.is_file() and not project.is_symlink():
        value=tomllib.loads(project.read_text(encoding="utf-8")).get("project",{}).get("requires-python")
        if value:
            constraints.append({"source":"pyproject.toml","constraint":value})
            if re.fullmatch(r"==\d+\.\d+\.\d+",value): pins["pyproject.toml"]=value[2:]
    unique=set(pins.values()); version=next(iter(unique)) if len(unique)==1 else None
    manager="pyenv-win" if system=="Windows" else "pyenv"
    steps=["Review the project's version and lockfile constraints before installing anything.",
           "If a matching runtime already exists, use its absolute executable path.",
           f"Otherwise install/configure {manager} separately following its official instructions; review any PATH/profile edits yourself."]
    if version:
        steps += [f"Check available builds: pyenv install --list; then pyenv install {version}",
                  f"In the project directory: pyenv local {version}",
                  "Verify: python --version; python -m venv .venv",
                  r"Windows: .venv\Scripts\python.exe -m pip install -r requirements.txt (only when this file is the project's install contract)." if system=="Windows" else
                  "macOS: .venv/bin/python -m pip install -r requirements.txt (only when this file is the project's install contract)."]
    else:
        steps.append("Resolve the supported runtime from the recorded constraints; do not guess or overwrite a pin.")
    steps += ["Use the project's existing package manager and frozen lockfile; never global pip/npm installs.",
              "For Node use an existing per-project version manager and lockfile; containers are optional only with an agreed memory/disk budget.",
              "Keep a reusable project environment separate from temporary test/server/browser resources; stop temporary resources after use."]
    return {"status":"CONFLICT" if len(unique)>1 else "PLAN_ONLY","python_version":version,
            "pins":pins,"constraints":constraints,"manager":manager,"steps":steps,
            "observed_plugin_python":sys.version.split()[0],"project_runtime_verified":False,
            "tools":{name:shutil.which(name) for name in ("git","node","uv","pyenv","codex","claude","devin")}}
