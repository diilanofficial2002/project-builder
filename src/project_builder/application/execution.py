"""Blocking, bounded recipes. A CLI exit never intentionally leaves a workload running."""
import json
from pathlib import Path
import sqlite3
from contextlib import closing
import sys
import time
from project_builder.contracts import RunIdentity
from project_builder.platform_paths import PlatformPaths, reject_links
from project_builder.supervision.models import ProcessSpec
from project_builder.supervision.supervisor import Supervisor


def pending_resources(project_id):
    path=PlatformPaths.user_state_root()/"resources.sqlite3"
    reject_links(path)
    if not path.exists(): return []
    with closing(sqlite3.connect(path.resolve().as_uri()+"?mode=ro",uri=True,timeout=2)) as db:
        return [row[0] for row in db.execute("SELECT id FROM leases WHERE project=? AND active=1",(project_id,))]


def cleanup_project(project_id):
    if not pending_resources(project_id): return {"status":"CLEANED","receipts":[]}
    with Supervisor() as supervisor:
        receipts=[supervisor.stop(h,0).model_dump(mode="json") for h,_,_ in supervisor.ledger.records() if h.owner.project_id==project_id]
    return {"status":"CLEANED" if not pending_resources(project_id) else "CLEANUP_PENDING","receipts":receipts}


def execute_recipe(workspace,recipe_id):
    doc=workspace._read(); run=doc["run"]; recipes=doc["brief"].get("recipes",[])
    matches=[r for r in recipes if r.get("id")==recipe_id]
    if len(matches)!=1: raise ValueError("recipe ID must uniquely match the reviewed kickoff")
    recipe=matches[0]
    allowed={"id","executable","argv","env","memory_mb","disk_mb","timeout_seconds","cooperative"}
    if set(recipe)-allowed: raise ValueError("unknown recipe fields")
    memory=recipe.get("memory_mb")
    if type(memory) is not int or memory<1: raise ValueError("reviewed memory footprint required")
    cooperative=sys.platform=="darwin" and recipe.get("cooperative") is True
    spec=ProcessSpec.model_validate_json(json.dumps({"executable":recipe["executable"],"argv":recipe.get("argv",[]),
        "env":recipe.get("env",{}),"cwd":str(workspace.root),"timeout_seconds":recipe.get("timeout_seconds",300.0),
        "containment":"cooperative_group" if cooperative else "contained_tree","trusted_recipe_id":recipe_id if cooperative else None,
        "budget":{"project_id":doc["project_id"],"memory_bytes":memory*2**20,"disk_bytes":recipe.get("disk_mb",0)*2**20}}))
    owner=RunIdentity(project_id=doc["project_id"],run_id=run["id"],scope_id=run["id"],stage=run["stage"],contract_revision=1)
    with Supervisor(trusted_group_recipes=frozenset({recipe_id}) if cooperative else frozenset()) as supervisor:
        handle=supervisor.start(spec,owner)
        while (receipt:=supervisor.receipt(handle.id)) is None:
            current=workspace.status()
            if current["run_id"]!=run["id"] or current["status"] in {"PAUSED","CANCELLED"}:
                receipt=supervisor.stop(handle,0); break
            time.sleep(.1)
        return {"status":"EXECUTED" if receipt.status=="CLEANED" and receipt.exit_code==0 else "EXECUTION_STOPPED",
                "recipe_id":recipe_id,"cleanup":receipt.model_dump(mode="json")}
