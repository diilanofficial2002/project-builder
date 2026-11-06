"""Local operator CLI and native-host helper commands."""

import argparse
from pathlib import Path
from uuid import uuid4
import json
import sys

from pydantic import ValidationError

from project_builder.contracts import CommandEnvelope, CommandResult


def _parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--project", type=Path, default=argparse.SUPPRESS, help="project root (default: current directory)")
    common.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help="render structured output")
    parser = argparse.ArgumentParser(
        prog="project-builder", parents=[common],
        description="Project Builder: scoped delivery, evidence and safe local tools.",
    )
    subparsers = parser.add_subparsers(dest="intent", required=True)
    for intent in ("init", "start", "continue", "status", "help", "doctor", "guide", "change", "backlog", "feedback", "pause", "cancel", "cleanup"):
        aliases = ["stop"] if intent == "pause" else []
        command = subparsers.add_parser(intent, parents=[common], aliases=aliases)
        command.add_argument("--request-id")
        command.add_argument("--expected-revision",type=int)
        command.add_argument("--run-id")
        if intent == "init":
            command.add_argument("--kind",choices=("new","takeover","new-version"),default="new")
        if intent == "start":
            command.add_argument("description", nargs="?")
        elif intent == "change":
            command.add_argument("text")
            command.add_argument("--urgency", choices=("normal", "urgent"), default="normal")
        elif intent == "feedback":
            command.add_argument("--feedback-path", type=Path)
    for intent in ("submit","review-packet","review","qa-review","git","execute","discovery","artifacts","operations","native-plan"):
        command=subparsers.add_parser(intent,parents=[common])
        command.add_argument("--request-id")
        command.add_argument("--expected-revision",type=int)
        command.add_argument("--run-id")
        if intent=="submit":
            command.add_argument("kind",choices=("brief","matrix","results","defects","guide","feedback","baseline","work"))
            command.add_argument("file",type=Path)
        elif intent in {"review","review-packet","qa-review"}:
            command.add_argument("subject",choices=("kickoff","matrix","quality","guide","feedback","baseline","handoff","recovery"))
            if intent!="review-packet": command.add_argument("--digest",required=True)
            if intent=="qa-review": command.add_argument("--notes",required=True)
        elif intent=="git":
            command.add_argument("operation",choices=("bootstrap","stage","feature","integrate","delete-feature"))
            for key in ("name","stage","source","target"): command.add_argument("--"+key)
        elif intent=="execute": command.add_argument("recipe_id")
        elif intent=="native-plan": command.add_argument("capabilities_file",type=Path)
    subparsers.add_parser("mcp",help="run the local stdio MCP server")
    return parser


def parse_command(argv: list[str]) -> CommandEnvelope:
    parser = _parser()
    args = parser.parse_args(argv)
    intent = "pause" if args.intent == "stop" else args.intent
    payload = {"kind": intent, "output_format": "json" if getattr(args, "json", False) else "text"}
    if intent == "start":
        payload["description"] = args.description
    elif intent == "change":
        payload.update(text=args.text, urgency=args.urgency)
    elif intent == "feedback":
        payload["feedback_path"] = args.feedback_path
    try:
        return CommandEnvelope(
            request_id=str(uuid4()), project_root=getattr(args, "project", Path.cwd()),
            run_id=None, expected_revision=None, intent=intent, payload=payload,
        )
    except ValidationError as error:
        parser.error(str(error))


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        import sys
        argv = sys.argv[1:]
    parser=_parser()
    try: args=parser.parse_args(argv)
    except SystemExit as result: return int(result.code)
    if args.intent=="mcp":
        from project_builder.transport.server import main as serve
        serve(); return 0
    from project_builder.application.workspace import Workspace
    from project_builder.transport.api import invoke, READS
    root=Path(getattr(args,"project",Path.cwd())).absolute(); intent="pause" if args.intent=="stop" else args.intent
    payload={}; code=0
    try:
        if intent=="init": payload={"kind":args.kind}
        elif intent=="start": payload={"description":args.description or ""}
        elif intent=="change": payload={"text":args.text,"urgent":args.urgency=="urgent"}
        elif intent in {"feedback","submit"}:
            path=args.feedback_path if intent=="feedback" else args.file
            if not path: raise ValueError("supply --feedback-path with actual observations")
            if path.stat().st_size>2**20: raise ValueError("artifact exceeds 1MiB")
            payload={"data":json.loads(path.read_text(encoding="utf-8-sig"))}
            if intent=="submit": payload["kind"]=args.kind
        elif intent in {"review","review-packet","qa-review"}:
            payload={"subject":args.subject}
            if intent=="qa-review": payload.update(digest=args.digest,notes=args.notes)
        elif intent=="git":
            payload={k:getattr(args,k) for k in ("operation","name","stage","source","target") if getattr(args,k) is not None}
        elif intent=="execute": payload={"recipe_id":args.recipe_id}
        elif intent=="native-plan":
            if args.capabilities_file.stat().st_size>2**20: raise ValueError("capabilities exceed 1MiB")
            payload={"capabilities":json.loads(args.capabilities_file.read_text(encoding="utf-8-sig"))}
        if intent=="review":
            if not sys.stdin.isatty() or not sys.stdout.isatty():
                raise ValueError("human review requires a separate interactive terminal; redirected/model-supplied approval is refused")
            def human(packet):
                print(json.dumps(packet,ensure_ascii=False,indent=2))
                return input("Review the packet above. Type its full digest to approve, or Enter to decline: ").strip()==packet["digest"]
            data=Workspace(root,reviewer=human).record_review(args.subject,args.digest)
        else:
            revision=getattr(args,"expected_revision",None)
            if intent not in READS|{"init"} and revision is None:
                revision=Workspace(root).status().get("revision")
            data=invoke(root,intent,payload,request_id=getattr(args,"request_id",None) or str(uuid4()),
                        expected_revision=revision,run_id=getattr(args,"run_id",None))
        status=data.get("status","READY")
        code=1 if status in {"REJECTED","ACTION_STOPPED","CLEANUP_PENDING","EXECUTION_STOPPED","CONFLICT","ISOLATION_REQUIRED"} else 0
        result=CommandResult(status=status,summary=f"{intent}: {status}",next_action=data.get("next_action"),data=data)
    except (ValueError,OSError,KeyError,TypeError,RuntimeError) as error:
        code=1; result=CommandResult(status="REJECTED",summary=str(error),next_action="Inspect status/doctor and correct the input; completed work is preserved.",data={})
    if getattr(args,"json",False): print(result.model_dump_json())
    else:
        print(f"{result.status}: {result.summary}")
        if intent in READS and result.data: print(json.dumps(result.data,ensure_ascii=False,indent=2))
        elif result.next_action: print(result.next_action)
    return code
