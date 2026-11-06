"""Application workflow. Managed-project stages are data, not plugin build phases."""
import copy
import json
from pathlib import Path
from uuid import uuid4
from datetime import datetime, timezone
from .persistence import Documents
from .rules import digest, discovery_questions, evaluate_quality, feedback_check, intake_step, plan_team, select_stages, matrix_check
from .builds import build_id
from project_builder.platform_paths import reject_links

ARTIFACTS={"brief","matrix","results","defects","guide","feedback","baseline","work"}
TERMINAL={"COMPLETED","CANCELLED"}
class Workspace:
    def __init__(self, root: Path, *, reviewer=None):
        self.root=Path(root).absolute()
        self.meta=self.root/".project-builder"
        self.reviewer=reviewer

    def _paths(self):
        if not self.root.is_dir():
            raise ValueError("project directory does not exist")
        reject_links(self.meta)
        reject_links(self.meta/"state.sqlite3")
        reject_links(self.meta/".owner")
        for suffix in ("-wal","-shm","-journal"):
            reject_links(self.meta/("state.sqlite3"+suffix))
        return Documents(self.meta/"state.sqlite3")

    def _read(self):
        store=self._paths()
        doc=store.read()
        if doc and (self.meta/".owner").read_text(encoding="utf-8") != doc["project_id"]:
            raise ValueError("workspace ownership marker differs")
        return doc

    def _view(self, doc):
        run=doc.get("run") or {}
        return {"status":run.get("status","INITIALIZED"),"project_id":doc["project_id"],
                "run_id":run.get("id"),"stage":run.get("stage"),"stages":run.get("stages",[]),
                "contract_digest":run.get("contract_digest"),"revision":doc["revision"],
                "backlog_count":len(doc["backlog"]),"next_action":run.get("next_action","Use start to describe your project.")}

    def status(self):
        doc=self._read()
        return self._view(doc) if doc else {"status":"NOT_INITIALIZED","next_action":"Run init first."}

    def init(self, kind="new"):
        intake_step(kind)
        store=self._paths()
        if store.path.exists():
            return self.status()
        project_id=str(uuid4())
        if self.meta.exists():
            marker=self.meta/".owner"
            if not marker.is_file():
                raise ValueError("existing metadata directory has no ownership marker")
            project_id=marker.read_text(encoding="utf-8")
        else:
            self.meta.mkdir(mode=0o700)
            (self.meta/".owner").write_text(project_id,encoding="utf-8")
        doc={"schema_version":1,"project_id":project_id,"kind":kind,"revision":1,"run":None,
             "brief":None,"artifacts":{},"reviews":{},"backlog":[],"history":[]}
        return self._view(store.initialize(doc))

    def build_id(self):
        return build_id(self.root)

    def command(self,intent,payload,*,request_id=None,expected_revision=None):
        if intent.startswith("_"):
            raise ValueError("internal review actions are not public commands")
        return self._command(intent,payload,request_id=request_id,expected_revision=expected_revision)

    def _command(self,intent,payload,*,request_id=None,expected_revision=None):
        doc=self._read()
        if not doc:
            raise ValueError("workspace is not initialized")
        def transform(data):
            return self._dispatch(data,intent,payload)
        return self._paths().mutate(intent,payload,transform,request_id=request_id,expected_revision=expected_revision)

    def start(self, description):
        return self.command("start",{"description":description})
    def continue_run(self):
        return self.command("continue",{})
    def pause(self):
        return self.command("pause",{})
    def cancel(self):
        return self.command("cancel",{})
    def change(self,text,urgent=False):
        return self.command("change",{"text":text,"urgent":urgent})
    def submit(self,kind,data):
        return self.command("submit",{"kind":kind,"data":data})
    def backlog(self):
        doc=self._read()
        return {"items":doc["backlog"] if doc else [],"review_ready":bool(doc and doc["run"] and doc["run"]["status"] in TERMINAL)}
    def artifacts(self):
        doc=self._read()
        return copy.deepcopy(doc["artifacts"]) if doc else {}

    def _packet(self,doc,subject):
        run=doc.get("run")
        if not run:
            return {"ready":False,"subject":subject,"reason":"Start a project first"}
        artifacts=doc["artifacts"]
        if subject=="kickoff":
            brief=doc.get("brief")
            if not brief or discovery_questions(brief.get("answers",{})):
                return {"ready":False,"subject":subject,"reason":"Resolve discovery questions"}
            if doc["kind"]!="new" and not doc.get("baseline_review"):
                return {"ready":False,"subject":subject,"reason":"Baseline human observations/review required"}
            content=copy.deepcopy(brief)
            content["stages"]=select_stages(brief.get("target","final"),**brief.get("stage_options",{}))
            content["team"]=plan_team(brief.get("domains",[]),brief.get("complexity","mini"),brief.get("risks",[]))
            content["project_root"]=str(self.root.resolve())
        elif subject=="quality":
            if not all(k in artifacts for k in ("matrix","results","defects")) or not self._reviewed(doc,"matrix"):
                return {"ready":False,"subject":subject,"reason":"Approved matrix and current results/defects required"}
            content={k:artifacts[k] for k in ("matrix","results","defects")}
            content["build_sha"]=self.build_id()
            assessment=evaluate_quality(content["matrix"],content["results"],content["defects"],content["build_sha"])
            if assessment["status"]!="PASS":
                return {"ready":False,"subject":subject,"reason":assessment["reasons"],"assessment":assessment}
        elif subject in {"matrix","guide","feedback","baseline"}:
            if subject not in artifacts:
                return {"ready":False,"subject":subject,"reason":"Submit this artifact first"}
            content=copy.deepcopy(artifacts[subject])
            if subject=="matrix":
                if not run.get("contract_digest"):
                    return {"ready":False,"subject":subject,"reason":"Freeze kickoff scope first"}
                problem=matrix_check(content,[r["id"] for r in doc["brief"]["requirements"]])
                if problem: return {"ready":False,"subject":subject,"reason":problem}
            if subject in {"feedback","baseline"}:
                if feedback_check(content.get("participants",[]))["status"]!="PASS":
                    return {"ready":False,"subject":subject,"reason":"Need 2–3 real independent participants and sources"}
            if subject in {"guide","feedback","baseline"} and content.get("build_sha")!=self.build_id():
                return {"ready":False,"subject":subject,"reason":"Artifact build is stale"}
            if subject=="guide" and not all(content.get(k) for k in ("setup_steps","run_steps","stop_steps","cleanup_steps")):
                return {"ready":False,"subject":subject,"reason":"Guide needs setup/run/stop/cleanup verification"}
        elif subject=="handoff":
            from .execution import pending_resources
            if pending_resources(doc["project_id"]) or any(a["status"]=="UNKNOWN" for a in doc.get("actions",{}).values()):
                return {"ready":False,"subject":subject,"reason":"Clean owned workloads/reconcile unknown actions first"}
            if not all(self._reviewed(doc,s) for s in ("quality","guide","feedback")):
                return {"ready":False,"subject":subject,"reason":"Current quality, guide and human feedback reviews required"}
            if self._high_feedback(doc):
                return {"ready":False,"subject":subject,"reason":"High/unknown feedback defects require triage and retest"}
            content={"run_id":run["id"],"stage":run["stage"],"build_sha":self.build_id(),
                     "artifacts":copy.deepcopy(artifacts),"reviews":{k:copy.deepcopy(v) for k,v in doc["reviews"].items() if k!="handoff"},"backlog":copy.deepcopy(doc["backlog"])}
        elif subject=="recovery":
            from .execution import pending_resources
            unknown={k:copy.deepcopy(a) for k,a in doc.get("actions",{}).items() if a["status"]=="UNKNOWN"}
            if not unknown or pending_resources(doc["project_id"]):
                return {"ready":False,"subject":subject,"reason":"Need unknown actions and proof that owned workloads are stopped"}
            content={"unknown_actions":unknown,"build_sha":self.build_id(),"project_root":str(self.root),
                     "warning":"Inspect actual side effects before acknowledging. This closes the unknown action without asserting success; retest/review all affected work. Never blindly replay."}
        else:
            raise ValueError("unknown review subject")
        return {"ready":True,"subject":subject,"content":content,"digest":digest(content),"run_id":run["id"]}

    def review_packet(self,subject):
        doc=self._read()
        if not doc:
            return {"ready":False,"reason":"Initialize first"}
        return self._packet(doc,subject)

    def _reviewed(self,doc,subject):
        receipt=doc["reviews"].get(subject)
        if not receipt:
            return False
        packet=self._packet(doc,subject)
        return bool(packet.get("ready") and packet["digest"]==receipt["digest"] and receipt["run_id"]==doc["run"]["id"])

    def record_review(self,subject,expected_digest):
        if self.reviewer is None:
            raise ValueError("trusted user review channel is unavailable")
        packet=self.review_packet(subject)
        if not packet.get("ready") or packet["digest"]!=expected_digest:
            raise ValueError("review packet is incomplete or stale")
        if self.reviewer(copy.deepcopy(packet)) is not True:
            return {"status":"REVIEW_DECLINED"}
        # The callback is injected by a trusted TTY/MCP composition root, never JSON arguments.
        return self._command("_record_review",{"subject":subject,"digest":expected_digest})

    def record_agent_review(self,subject,expected_digest,notes):
        """QA evidence attestation; this grants no user or remote execution authority."""
        if subject not in {"matrix","quality","guide"}:
            raise ValueError("this subject requires the user's review channel")
        if not isinstance(notes,str) or not notes.strip():
            raise ValueError("independent review findings/provenance are required")
        return self._command("_record_review",{"subject":subject,"digest":expected_digest,"notes":notes})

    def _high_feedback(self,doc):
        return any(str(o.get("severity","unknown")).lower() not in {"info","low","medium"}
                   and o.get("status","open") not in {"resolved","closed"}
                   for o in doc["artifacts"].get("feedback",{}).get("observations",[]))

    def _dispatch(self,doc,intent,payload):
        run=doc["run"]
        if intent=="start":
            if run and run["status"] not in TERMINAL:
                return self._view(doc)
            if run:
                doc["brief"]=None  # Reassess the next scope; never mechanically repeat a Stage ladder.
            doc["run"]={"id":str(uuid4()),"status":intake_step(doc["kind"]),"stage":None,"stages":[],
                        "description":str(payload.get("description","")),"contract_digest":None,"next_action":"Collect discovery evidence and review the business-to-technical brief."}
            doc["artifacts"]={};doc["reviews"]={}
        elif intent=="change":
            text=payload.get("text")
            if not isinstance(text,str) or not text.strip():
                raise ValueError("change description is required")
            item={"id":str(uuid4()),"text":text,"status":"queued","run_id":run["id"] if run else None}
            doc["backlog"].append(item)
            if payload.get("urgent") and run and run["status"] not in TERMINAL:
                run["resume_status"]=run["status"];run["status"]="PAUSED"
            return {"status":"QUEUED","change_id":item["id"],"next_action":"Review after the agreed Stage; urgent change pauses for rebaseline."}
        elif not run:
            raise ValueError("start a project first")
        elif intent in {"pause","cancel"}:
            if run["status"] not in TERMINAL:
                run["resume_status"]=run["status"]
                run["status"]="PAUSED" if intent=="pause" else "CANCELLED"
                run["next_action"]="Checkpoint kept. Close owned workloads; continue revalidates the run."
        elif intent=="submit":
            kind,data=payload["kind"],copy.deepcopy(payload["data"])
            if kind not in ARTIFACTS:
                raise ValueError("unknown artifact kind")
            if kind=="brief":
                allowed={"answers","requirements","target","stage_options","domains","complexity","risks","permissions","recipes"}
                if type(data) is not dict or set(data)-allowed:
                    raise ValueError("unknown brief fields; approval flags are not accepted")
                requirements=data.get("requirements",[])
                if not isinstance(requirements,list) or not requirements or any(not isinstance(r,dict) or not isinstance(r.get("id"),str) or not r.get("acceptance") or not r.get("summary") for r in requirements) or len({r["id"] for r in requirements})!=len(requirements):
                    raise ValueError("unique requirements with acceptance examples are required")
                if not set(data.get("permissions",[])) <= {"local_git","execute_recipes"}:
                    raise ValueError("unsupported authority; immutable ceiling cannot be raised")
                if run["contract_digest"] is not None and run["status"] not in TERMINAL:
                    return self._dispatch(doc,"change",{"text":"Proposed requirement revision: "+json.dumps(data,ensure_ascii=False)})
                select_stages(data.get("target","final"),**data.get("stage_options",{}))
                doc["brief"]=data
            else:
                if (kind=="defects" and type(data) is not list) or (kind!="defects" and type(data) is not dict):
                    raise ValueError("invalid artifact document type")
                if run["status"] in TERMINAL:
                    raise ValueError("completed evidence is immutable; start a new run")
                if kind=="matrix" and run["status"] in TERMINAL:
                    raise ValueError("completed Stage evidence is immutable; start a new run")
                doc["artifacts"][kind]=data
                # Digest comparisons invalidate dependent reviews without trusting caller flags.
        elif intent=="_record_review":
            packet=self._packet(doc,payload["subject"])
            if not packet.get("ready") or packet["digest"]!=payload["digest"]:
                raise ValueError("review changed before recording")
            doc["reviews"][payload["subject"]]={"id":str(uuid4()),"digest":packet["digest"],
                "run_id":run["id"],"reviewed_at":datetime.now(timezone.utc).isoformat(),"notes":payload.get("notes")}
            if payload["subject"]=="baseline":
                doc["baseline_review"]=copy.deepcopy(doc["reviews"]["baseline"])
            if payload["subject"]=="recovery":
                for action in doc.get("actions",{}).values():
                    if action["status"]=="UNKNOWN":
                        action.update(status="RECONCILED_UNVERIFIED",result={"status":"NOT_VERIFIED","receipt":doc["reviews"]["recovery"]["id"]})
        elif intent=="_claim_action":
            actions=doc.setdefault("actions",{})
            operation=payload["operation_id"]
            if operation in actions:
                raise ValueError("operation already attempted; inspect its receipt, never replay an unknown mutation")
            if any(a["status"]=="UNKNOWN" for a in actions.values()):
                raise ValueError("an earlier action has no completion proof; reconcile it first")
            actions[operation]={"status":"UNKNOWN","run_id":run["id"],"description":payload["description"]}
        elif intent=="_finish_action":
            action=doc["actions"][payload["operation_id"]]
            action.update(status="COMPLETED",result=payload["result"])
        elif intent=="continue":
            if run["status"] in TERMINAL:
                return self._view(doc)
            if run["status"]=="PAUSED":
                run["status"]=run.pop("resume_status","DISCOVERY")
            if not run["contract_digest"]:
                if doc["kind"]!="new" and not doc.get("baseline_review"):
                    run["status"]="BASELINE_FEEDBACK";run["next_action"]="Collect and review independent baseline observations."
                elif not doc.get("brief") or discovery_questions(doc["brief"].get("answers",{})):
                    run["status"]="DISCOVERY";run["next_action"]="Answer the unresolved discovery questions."
                elif not self._reviewed(doc,"kickoff"):
                    run["status"]="KICKOFF_REVIEW";run["next_action"]="Review business-to-technical kickoff packet."
                else:
                    packet=self._packet(doc,"kickoff")
                    run.update(contract_digest=packet["digest"],stages=packet["content"]["stages"],
                               stage=packet["content"]["stages"][0],status="RUNNING",
                               next_action="Implement scoped work, record independent review and current test evidence.")
            else:
                if not self._reviewed(doc,"quality"):
                    run["status"]="VERIFYING";run["next_action"]="Run approved matrix and review current results/defects."
                elif not self._reviewed(doc,"guide"):
                    run["status"]="VERIFYING";run["next_action"]="Generate and verify local setup/run/stop/cleanup guide."
                elif "feedback" not in doc["artifacts"]:
                    run["status"]="STAGE_FEEDBACK";run["next_action"]="Development complete; obtain 2–3 independent real-user observations."
                elif not self._reviewed(doc,"feedback"):
                    run["status"]="WAITING_FOR_HUMAN";run["next_action"]="Review the real-user feedback batch."
                elif self._high_feedback(doc):
                    run["status"]="FEEDBACK_TRIAGE";run["next_action"]="Resolve High/unknown observations and retest affected work."
                elif not self._reviewed(doc,"handoff"):
                    run["status"]="HANDOFF";run["next_action"]="Review Stage handoff and cleanup evidence."
                else:
                    run["status"]="COMPLETED";run["next_action"]="Review queued backlog and choose the next scoped round."
                    doc["history"].append(copy.deepcopy(run))
        else:
            raise ValueError("unknown workspace action")
        return self._view(doc)

