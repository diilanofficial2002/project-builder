"""Local syntax and honest availability output, with no runtime side effects."""

import argparse
from pathlib import Path
from uuid import uuid4

from pydantic import ValidationError

from project_builder.contracts import CommandEnvelope, CommandResult


def _parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--project", type=Path, default=argparse.SUPPRESS, help="project root (default: current directory)")
    common.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help="render structured output")
    parser = argparse.ArgumentParser(
        prog="project-builder", parents=[common],
        description="Project Builder syntax preview. Runtime services are not yet initialized; commands report unavailable.",
    )
    subparsers = parser.add_subparsers(dest="intent", required=True)
    for intent in ("init", "start", "continue", "status", "help", "doctor", "guide", "change", "backlog", "feedback", "pause", "cancel", "cleanup"):
        aliases = ["stop"] if intent == "pause" else []
        command = subparsers.add_parser(intent, parents=[common], aliases=aliases, help="service unavailable")
        if intent == "start":
            command.add_argument("description", nargs="?")
        elif intent == "change":
            command.add_argument("text")
            command.add_argument("--urgency", choices=("normal", "urgent"), default="normal")
        elif intent == "feedback":
            command.add_argument("--feedback-path", type=Path)
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
    try:
        command = parse_command(argv)
    except SystemExit as result:
        return int(result.code)
    result = CommandResult(
        status="NOT_IMPLEMENTED",
        summary=f"{command.intent}: runtime services are not yet initialized; this command is unavailable.",
        next_action="Use --help to inspect supported command syntax.",
        data={},
    )
    if command.payload.output_format == "json":
        print(result.model_dump_json())
    else:
        print(f"{result.status}: {result.summary}")
        if result.next_action:
            print(result.next_action)
    return 1
