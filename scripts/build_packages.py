"""Generate three host adapters around one native runtime and common workflow."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tomllib
import zipfile

COMMANDS={
    "init":"Use when initializing project-builder for a new project, unfinished takeover or new version.",
    "start":"Use when starting a newly scoped project or feature with project-builder.",
    "continue":"Use when resuming project-builder after a checkpoint, interruption or human review.",
    "status":"Use when inspecting project-builder progress, blockers or the current checkpoint.",
    "help":"Use when the user needs help with project-builder commands or capabilities.",
    "doctor":"Use when a managed project has runtime, environment, dependency or host capability problems.",
    "guide":"Use when the user needs the local setup, run, stop and cleanup guide for a managed Stage.",
    "change":"Use when a new idea or requirement change arrives during an agreed Stage.",
    "backlog":"Use when collecting or reviewing queued ideas for the next project-builder scope.",
    "feedback":"Use when collecting or triaging actual independent user observations for a managed project.",
    "pause":"Use when the user explicitly pauses or stops the current managed-project run.",
    "cancel":"Use when the user explicitly cancels the current managed-project run.",
    "cleanup":"Use when owned temporary workloads need cleanup or crash recovery.",
}

def write_json(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

def package(root,runtime,output,*,platform_name):
    root=Path(root).resolve();runtime=Path(runtime).resolve();output=Path(output).resolve()
    executable="project-builder.exe" if platform_name.startswith("windows-") else "project-builder"
    if not (runtime/executable).is_file(): raise ValueError("native runtime entrypoint is missing")
    if runtime==output or runtime in output.parents: raise ValueError("output cannot be inside the runtime")
    for file in runtime.rglob("*"):
        if not file.resolve().is_relative_to(runtime): raise ValueError("runtime link escapes package")
    version=tomllib.loads((root/"pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    output.mkdir(parents=True,exist_ok=True);archives={}
    for host in ("codex","claude","devin"):
        directory=output/host/"project-builder";directory.mkdir(parents=True,exist_ok=False)
        manifest={"$schema":"https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
            "name":"project-builder","version":version,"description":"Scope-aware AI team for building and continuing software projects.",
            "author":{"name":"project-builder contributors"}}
        interface={"displayName":"Project Builder","shortDescription":"Build projects with an AI team","longDescription":manifest["description"],
            "developerName":"project-builder contributors","category":"Productivity","capabilities":["Read","Write"],
            "defaultPrompt":"Use Project Builder to inspect and start my project."}
        if host=="codex":
            manifest["extensions"]={"com.openai":{"interface":interface,"onboardingSkill":"./skills/init/SKILL.md"}}
            write_json(directory/".codex-plugin"/"plugin.json",{"name":"project-builder","version":version,
                "description":manifest["description"],"skills":"./skills/","mcpServers":"./.mcp.json","interface":interface})
        else:
            write_json(directory/(".claude-plugin" if host=="claude" else ".devin-plugin")/"plugin.json",
                {"name":"project-builder","version":version,"description":manifest["description"]})
        write_json(directory/"plugin.json",manifest)
        config={"command":"${PLUGIN_ROOT}/runtime/"+executable,"args":["mcp"]}
        write_json(directory/"mcp.json",{"$schema":"https://agent-plugins.org/schemas/1.0.0/mcp.schema.json",
            "mcpServers":{"project-builder":{"type":"stdio",**config}}})
        legacy={**config,"command":config["command"].replace("${PLUGIN_ROOT}","${CLAUDE_PLUGIN_ROOT}" if host=="claude" else "${PLUGIN_ROOT}")}
        write_json(directory/".mcp.json",{"mcpServers":{"project-builder":legacy}})
        for name,description in COMMANDS.items():
            path=directory/"skills"/name/"SKILL.md";path.parent.mkdir(parents=True)
            path.write_text(f"---\nname: {name}\ndescription: {description}\n---\n\n# project-builder {name}\n\nRead [the shared coordinator contract](../../references/workflow.md) before acting.\nThe requested intent is `{name}`. Route natural-language arguments to that intent using the local `project_builder` MCP tool. Read status first, respect the current run/revision, and execute the authorized work through the next coherent checkpoint. Never manufacture user approvals, test execution or human feedback. If MCP is unavailable, use the bundled runtime via an absolute path and report the host limitation.\n",encoding="utf-8")
        shutil.copytree(root/"plugin"/"references",directory/"references")
        shutil.copytree(runtime,directory/"runtime",symlinks=False)
        if (root/"docs"/"installation").exists(): shutil.copytree(root/"docs"/"installation",directory/"docs")
        (directory/"README.md").write_text("# Project Builder\n\nAI team workflow for projects managed by Codex, Claude Code or Devin CLI/Desktop.\n\n- [Install and use](docs/README.md)\n- [Artifacts and API](docs/artifacts-and-api.md)\n- [Verification and limitations](docs/verification.md)\n- [Coordinator contract](references/workflow.md)\n\nEditable unapproved input documents are in templates/. A marketplace example is in examples/.\nPublic recipe execution is disabled until an isolated driver can enforce the authority ceiling.\n",encoding="utf-8")
        import importlib.util
        spec=importlib.util.spec_from_file_location("project_builder_templates",root/"scripts"/"create_example.py")
        templates=importlib.util.module_from_spec(spec);spec.loader.exec_module(templates)
        templates.create(directory/"templates")
        (directory/"examples").mkdir()
        shutil.copyfile(root/"examples"/"marketplace.json",directory/"examples"/"marketplace.json")
        if host=="codex":
            write_json(directory.parent/".agents"/"plugins"/"marketplace.json",json.loads((root/"examples"/"marketplace.json").read_text(encoding="utf-8")))
        archive=output/f"project-builder-{version}-{host}-{platform_name}.zip"
        with zipfile.ZipFile(archive,"w",compression=zipfile.ZIP_DEFLATED) as zipped:
            for path in sorted(directory.rglob("*")):
                if path.is_file(): zipped.write(path,"project-builder/"+path.relative_to(directory).as_posix())
        archives[host]=archive
    checksums=[]
    for path in archives.values():
        with path.open("rb") as stream: checksum=hashlib.file_digest(stream,"sha256").hexdigest()
        checksums.append(checksum+"  "+path.name)
    (output/"SHA256SUMS.txt").write_text("\n".join(checksums)+"\n",encoding="utf-8")
    return archives

if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--runtime",type=Path,required=True);parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--platform",choices=("windows-x64","macos-arm64","macos-x64"),required=True)
    args=parser.parse_args()
    for host,path in package(Path(__file__).resolve().parents[1],args.runtime,args.output,platform_name=args.platform).items(): print(host,path)
