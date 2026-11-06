"""Single narrow dispatcher shared by CLI and MCP. No approval booleans or shell tools."""
from pathlib import Path
import json
from project_builder.application.workspace import Workspace
from project_builder.application.environment import environment_plan
from project_builder.application.git_service import LocalGit
from project_builder.application.rules import DISCOVERY, discovery_questions
from project_builder.application.execution import cleanup_project, pending_resources

READS={"status","help","doctor","guide","backlog","discovery","artifacts","review-packet","operations","native-plan"}
FIELDS={"init":{"kind"},"start":{"description"},"continue":set(),"pause":set(),"cancel":set(),
        "change":{"text","urgent"},"submit":{"kind","data"},"feedback":{"data"},"cleanup":set(),
        "qa-review":{"subject","digest","notes"},"review-packet":{"subject"},
        "git":{"operation","name","stage","source","target"},"execute":{"recipe_id"},
        "native-plan":{"capabilities"}}


def _cleanup(workspace,project_id):
    result=cleanup_project(project_id)
    native=workspace.native_resources()
    if native["status"]!="PASS": result["status"]="CLEANUP_PENDING"
    return result|{"native_resources":native}

def invoke(root,intent,payload=None,*,request_id=None,expected_revision=None,run_id=None):
    payload={} if payload is None else payload
    if not isinstance(payload,dict) or intent not in READS|FIELDS.keys(): raise ValueError("unknown command/payload")
    if set(payload)-FIELDS.get(intent,set()): raise ValueError("unknown command fields; caller approval is never accepted")
    if not Path(root).is_absolute(): raise ValueError("project_root must be an absolute path")
    if len(json.dumps(payload,allow_nan=False).encode("utf-8"))>2**20: raise ValueError("payload exceeds 1MiB")
    if intent=="change" and "urgent" in payload and type(payload["urgent"]) is not bool: raise ValueError("urgent must be boolean")
    workspace=Workspace(Path(root))
    if intent=="status": return workspace.status()|{"native_resources":workspace.native_resources()}
    if intent=="help": return {"status":"READY","commands":sorted(READS|FIELDS.keys()),"next_action":"Start with init, start, discovery; review kickoff before scoped work."}
    if intent=="doctor": return environment_plan(root)
    if intent=="guide":
        doc=workspace._read() or {}
        selected=doc if run_id is None or run_id==(doc.get("run") or {}).get("id") else next((a for a in doc.get("archive",[]) if a["run"]["id"]==run_id),{})
        return {"status":"READY","guide":selected.get("artifacts",{}).get("guide"),"environment":environment_plan(root)}
    if intent=="backlog": return workspace.backlog()|{"status":"READY"}
    if intent=="artifacts": return {"status":"READY","artifacts":workspace.artifacts(),"build_sha":workspace.build_id()}
    if intent=="discovery":
        doc=workspace._read()
        return {"status":"READY","questions":discovery_questions((doc or {}).get("brief",{}).get("answers",{}) if (doc or {}).get("brief") else {}),"fields":list(DISCOVERY)}
    if intent=="review-packet": return workspace.review_packet(payload["subject"])|{"status":"REVIEW_PACKET"}
    if intent=="operations": return {"status":"READY","operations":(workspace._read() or {}).get("actions",{})}
    if intent=="native-plan":
        from project_builder.application.native_host import execution_route
        doc=workspace._read() or {};run=doc.get("run") or {}
        if run_id is not None and run_id!=run.get("id"): raise ValueError("stale run ID")
        authorized=bool(run.get("contract_digest") and run.get("status") not in {"PAUSED","CANCELLED","COMPLETED"}
                        and "native_tools" in (doc.get("brief") or {}).get("permissions",[]))
        return execution_route(payload.get("capabilities"),authorized=authorized)|{"run_id":run.get("id"),"revision":doc.get("revision")}
    if intent=="init":
        result=workspace.init(payload.get("kind","new"))
        try: result["git"]=LocalGit(root).bootstrap()
        except ValueError as error: result["git"]={"status":"NEEDS_ATTENTION","reason":str(error)}
        return result
    if not request_id or type(expected_revision) is not int:
        raise ValueError("mutations require request_id and expected_revision from current status")
    current=workspace.status()
    if run_id is not None and run_id!=current.get("run_id"): raise ValueError("stale run ID")
    if intent=="execute":
        return {"status":"ISOLATION_REQUIRED","reason":"Public recipe execution is disabled: process lifetime supervision does not isolate Git, credentials, filesystem or network authority. No user approval can bypass this capability limit."}
    if intent in {"git","execute","qa-review","cleanup"}:
        if current.get("revision")!=expected_revision: raise ValueError("stale workspace revision")
        if intent=="qa-review": return workspace.record_agent_review(payload["subject"],payload["digest"],payload["notes"])
        if intent=="cleanup": return _cleanup(workspace,current["project_id"])
        doc=workspace._read()
        permission="local_git" if intent=="git" else "execute_recipes"
        if not current.get("contract_digest") or current["status"] in {"PAUSED","CANCELLED","COMPLETED"} or permission not in doc["brief"].get("permissions",[]):
            raise ValueError("this action is outside the reviewed active scope")
        workspace._command("_claim_action",{"operation_id":request_id,"description":{"intent":intent,"payload":payload}},expected_revision=expected_revision)
        try:
            if intent=="git":
                service=LocalGit(root); operation=payload.get("operation")
                if operation=="bootstrap": result=service.bootstrap()
                elif operation=="stage": result={"status":"CREATED_LOCAL","branch":service.stage(payload["name"])}
                elif operation=="feature": result={"status":"CREATED_LOCAL","branch":service.feature(payload["stage"],payload["name"])}
                elif operation=="integrate": result=service.integrate(payload["source"],payload["target"])
                elif operation=="delete-feature": result=service.delete_feature(payload["source"],payload["stage"])
                else: raise ValueError("unsupported Git operation; remote/protected writes are disabled")
        except Exception as error:
            result={"status":"ACTION_STOPPED","reason":str(error)}
        workspace._command("_finish_action",{"operation_id":request_id,"result":result})
        return result
    if intent=="feedback": payload={"kind":"feedback","data":payload["data"]}; intent="submit"
    if intent in {"pause","cancel"}:
        result=workspace.command(intent,payload,request_id=request_id,expected_revision=expected_revision)
        return result|{"cleanup":_cleanup(workspace,current["project_id"])}
    return workspace.command(intent,payload,request_id=request_id,expected_revision=expected_revision)
