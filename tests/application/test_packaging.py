import importlib.util
import json
import zipfile
from pathlib import Path


def test_host_packages_include_runtime_and_resolve_portable_paths(tmp_path):
    root=Path(__file__).resolve().parents[2]
    spec=importlib.util.spec_from_file_location("builder",root/"scripts"/"build_packages.py")
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    runtime=tmp_path/"runtime"; runtime.mkdir(); (runtime/"project-builder.exe").write_bytes(b"fixture-not-an-executable")
    archives=module.package(root,runtime,tmp_path/"output",platform_name="windows-x64")
    assert set(archives)=={"codex","claude","devin"}
    for host,path in archives.items():
        with zipfile.ZipFile(path) as archive:
            names=set(archive.namelist()); manifest=json.loads(archive.read("project-builder/plugin.json"))
            assert manifest["name"]=="project-builder"
            assert "project-builder/runtime/project-builder.exe" in names
            assert "project-builder/skills/continue/SKILL.md" in names
            assert not any(".venv/" in p or p.endswith(".sqlite3") for p in names)
            config=json.loads(archive.read("project-builder/mcp.json"))
            command=config["mcpServers"]["project-builder"]["command"].replace("${PLUGIN_ROOT}/", "project-builder/")
            assert command in names
            if host=="claude": assert "project-builder/.claude-plugin/plugin.json" in names
            if host=="devin": assert "project-builder/.devin-plugin/plugin.json" in names
