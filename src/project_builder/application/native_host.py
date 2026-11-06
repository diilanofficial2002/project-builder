"""Host-native execution guidance and team-attested cleanup, never a shell capability."""
from project_builder.policy.authority import DENIED_OPERATIONS

HOSTS = {"codex", "claude", "devin"}


def validate_work_update(previous, current, run_id, *, cleanup_only=False):
    """Retain job identities so replacing a work artifact cannot hide pending jobs."""
    old_jobs=previous.get("native_jobs",[])
    jobs=current.get("native_jobs",[])
    if not isinstance(jobs,list): raise ValueError("native_jobs must be an array")
    indexed={}
    for job in jobs:
        if (not isinstance(job,dict) or not isinstance(job.get("id"),str) or not job["id"].strip()
                or job["id"] in indexed or not isinstance(job.get("host"),str)
                or job["host"] not in HOSTS or job.get("run_id")!=run_id):
            raise ValueError("native jobs need unique identities bound to the current host/run")
        if not isinstance(job.get("status"),str) or job["status"] not in {"ACTIVE","CLEANUP_PENDING","CLEANED","UNKNOWN"}:
            raise ValueError("invalid native job lifecycle status")
        if job["status"]=="CLEANED" and (not isinstance(job.get("cleanup_evidence"),str) or not job["cleanup_evidence"].strip()):
            raise ValueError("cleaned native jobs need actual cleanup evidence")
        indexed[job["id"]]=job
    for old in old_jobs:
        new=indexed.get(old["id"])
        if new is None or any(new.get(k)!=old.get(k) for k in ("host","run_id")):
            raise ValueError("retain all recorded native job identities and cleanup obligations")
        lifecycle_fields={"status","cleanup_evidence"}
        if cleanup_only and {k:v for k,v in new.items() if k not in lifecycle_fields}!={k:v for k,v in old.items() if k not in lifecycle_fields}:
            raise ValueError("cancelled jobs accept lifecycle evidence only")
    if cleanup_only:
        lifecycle={"native_jobs","no_native_jobs_reason"}
        if {k:v for k,v in current.items() if k not in lifecycle}!={k:v for k,v in previous.items() if k not in lifecycle}:
            raise ValueError("cancelled runs accept lifecycle evidence only")
        if any(j.get("status")=="ACTIVE" for j in jobs):
            raise ValueError("cancelled runs cannot start or declare active work; stop/reconcile the owned jobs")


def execution_route(capabilities, *, authorized):
    if not authorized:
        return {"status": "NOT_AUTHORIZED", "reason": "Review an active scope with native_tools permission first."}
    if (not isinstance(capabilities, dict) or not isinstance(capabilities.get("host"),str) or capabilities["host"] not in HOSTS
            or any(not isinstance(capabilities.get(k), str) or not capabilities[k].strip()
                   for k in ("run_tool", "stop_tool", "observed_from"))
            or capabilities.get("bounded_timeout") is not True
            or capabilities.get("owned_cleanup") is not True):
        return {"status": "HOST_CAPABILITY_REQUIRED", "reason": "Inspect real host tools for bounded execution and owned cleanup; do not invent capabilities."}
    return {"status": "HOST_NATIVE", "requires_custom_runner": False,
            "max_active_heavy_jobs": 1, "forbidden_actions": sorted(DENIED_OPERATIONS),
            "host": capabilities["host"], "run_tool": capabilities["run_tool"],
            "stop_tool": capabilities["stop_tool"], "observed_from": capabilities["observed_from"],
            "boundary": "Advisory plan based on host-reported capabilities, not an OS sandbox or an execution grant. Use the host's own permissions and reviewed resource budget. Record actual job identity, timeout, exit and cleanup evidence in work.native_jobs. Git/protected/remote denials still apply."}


def native_jobs_gate(work, run_id):
    """Validate declared lifecycle evidence; JSON cannot authenticate a host session."""
    if not isinstance(work, dict) or not isinstance(work.get("native_jobs"), list):
        return {"status": "UNVERIFIED", "reason": "Record native jobs, or explicitly explain why none ran."}
    jobs = work["native_jobs"]
    if not jobs:
        reason = work.get("no_native_jobs_reason")
        return {"status": "PASS" if isinstance(reason, str) and reason.strip() else "UNVERIFIED",
                "evidence_type": "TEAM_ATTESTATION", "jobs": []}
    ids = set()
    pending = []
    for job in jobs:
        if (not isinstance(job, dict) or not isinstance(job.get("id"), str) or not job["id"].strip()
                or job["id"] in ids or job.get("run_id") != run_id
                or not isinstance(job.get("host"),str) or job["host"] not in HOSTS
                or not isinstance(job.get("status"),str)):
            return {"status": "UNVERIFIED", "reason": "Native job identities must be unique and belong to this host/run."}
        ids.add(job["id"])
        if job.get("status") in {"ACTIVE", "CLEANUP_PENDING"}:
            pending.append(job["id"])
        elif (job.get("status") != "CLEANED" or not isinstance(job.get("cleanup_evidence"), str)
              or not job["cleanup_evidence"].strip()):
            return {"status": "UNVERIFIED", "reason": "Native jobs need observed exit and owned-resource cleanup evidence."}
    return {"status": "CLEANUP_PENDING" if pending else "PASS", "pending": pending,
            "evidence_type": "TEAM_ATTESTATION",
            "next_action": "Inspect and stop only the recorded owned sessions through the original host tools; the runtime does not kill caller-supplied IDs."}
