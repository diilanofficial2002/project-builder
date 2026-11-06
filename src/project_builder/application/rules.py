"""Deterministic rules for projects managed by the plugin.

Pure evaluations are proposals until the composition root binds the evidence and
the user's review receipt. Caller flags are never execution authority.
"""
import hashlib
import json

STAGES = ("poc", "mvp", "beta", "final")
TEST_FAMILIES=("functional","regression","unit","integration-sit","uat","end-to-end","ux-ui",
               "accessibility","compatibility","load-performance","security","privacy",
               "data-quality","ai-evaluation","resilience-recovery","installation-cleanup")

def matrix_check(matrix,requirement_ids):
    try:
        if set(matrix["requirements"])!=set(requirement_ids) or not requirement_ids:
            return "Matrix must cover every requirement in the frozen scope"
        families=matrix["families"]
        if set(families)!=set(TEST_FAMILIES): return "Decide applicability for every test family"
        for name,decision in families.items():
            if type(decision.get("applicable")) is not bool or not decision.get("reason"):
                return "Every family needs applicability and a scope/risk reason"
            if decision["applicable"] and not any(c.get("family")==name and c.get("applicable",True) for c in matrix["cases"]):
                return "Applicable family has no test cases: "+name
        if not families["functional"]["applicable"]: return "Functional acceptance is required"
        if any(c.get("family") not in families for c in matrix["cases"]): return "Unknown case family"
        if not matrix["cases"] or len({c["id"] for c in matrix["cases"]})!=len(matrix["cases"]): return "Unique test cases required"
        covered={r for c in matrix["cases"] if c.get("applicable",True) for r in c["requirement_ids"]}
        if not set(requirement_ids)<=covered: return "Requirement has no applicable test"
        return None
    except (KeyError,TypeError,AttributeError): return "Malformed matrix"
ROLES = {
    "ba": "Business discovery, requirements and traceability",
    "pm": "Backlog, scope, dependencies and delivery communication",
    "sa": "System architecture, interfaces and technical decisions",
    "development-lead": "Implementation coordination and technical review",
    "backend": "Backend services and integration",
    "frontend": "Frontend implementation",
    "data-engineer": "Data contracts, pipelines and quality",
    "ai-engineer": "AI integration, evaluation and failure behavior",
    "qa": "Independent SIT/UAT strategy, matrix and evidence",
    "ux-ui-designer": "User journeys, interaction, accessibility and visual design",
    "devsecops": "Security, build, environment and operational controls",
}
DISCOVERY = {
    "business_goal": "What problem and measurable business outcome should this solve?",
    "users": "Who uses it, and what are their main journeys?",
    "scope": "Which features are included and excluded in this round?",
    "acceptance": "What concrete examples and measurable outcomes mean the work is accepted?",
    "business_rules": "Which business rules, failure cases and permissions matter?",
    "ux": "What user journeys, accessibility and design constraints apply?",
    "data": "What data, privacy, retention and integration constraints apply (or none)?",
    "architecture": "What architecture/interfaces must be kept or changed?",
    "runtime": "Which runtime/dependency versions and local setup are required?",
    "quality": "Which functional, regression, UX, load, security and other checks are applicable?",
    "authority": "Which local/Git/tool actions may the plugin take, within its immutable ceiling?",
    "resource_budget": "What machine, concurrency, time and storage budget is available?",
    "human_feedback": "Who coordinates the independent real-user feedback required by this project?",
    "delivery": "What deliverables, local guide, deadline and support expectations apply?",
}

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
        ensure_ascii=False, allow_nan=False).encode("utf-8")).hexdigest()

def select_stages(target, *, feasibility_unknown=False, first_slice_needed=False, pilot_needed=False):
    if target not in STAGES:
        raise ValueError("unknown target stage")
    needed = [s for s, flag in (("poc", feasibility_unknown), ("mvp", first_slice_needed),
                               ("beta", pilot_needed)) if flag and STAGES.index(s) < STAGES.index(target)]
    return needed + [target]

def intake_step(kind):
    if kind not in {"new", "takeover", "new-version"}:
        raise ValueError("unknown intake kind")
    return "DISCOVERY" if kind == "new" else "BASELINE_FEEDBACK"

def discovery_questions(answers):
    return [{"field": key, "question": question} for key, question in DISCOVERY.items()
            if not answers.get(key) or str(answers[key]).strip().lower() in {"unknown", "tbd", "todo", "fast", "easy"}]

def plan_team(domains, complexity="mini", risks=(), max_active=1):
    if type(max_active) is not int or max_active < 1:
        raise ValueError("positive specialist budget required")
    selected = ["ba", "development-lead", "qa"]
    if complexity not in {"mini", "small"}:
        selected += ["pm", "sa"]
    for domain, role in [("frontend","frontend"),("ui","frontend"),("backend","backend"),
                         ("data","data-engineer"),("ai","ai-engineer")]:
        if domain in domains and role not in selected:
            selected.append(role)
    if {"frontend", "ui"} & set(domains):
        selected.append("ux-ui-designer")
    if {"security", "privacy", "deployment", "operations"} & set(risks):
        selected.append("devsecops")
    return {"selected_roles": selected, "max_active_specialists": max_active,
            "responsibilities": {r: ROLES[r] for r in selected},
            "combined_roles": {"ba": ["pm"]} if complexity in {"mini","small"} else {},
            "review": "Use a fresh context for independent QA/review; disclose unavailable host capabilities."}

def feedback_check(people):
    if not isinstance(people,list) or any(not isinstance(p,dict) or not isinstance(p.get("id"),str) for p in people):
        return {"status":"WAITING_FOR_HUMAN","requires_owner_attestation":True,"reason":"Malformed participant evidence"}
    ids = [p.get("id") for p in people]
    valid = len(people) in (2,3) and len(set(ids)) == len(ids) and all(
        isinstance(p.get("id"), str) and p["id"].strip()
        and p.get("real_user") is True and p.get("independent") is True
        and p.get("unfamiliar") is True and isinstance(p.get("source"), str)
        and p["source"].strip() and not any(word in p["source"].lower() for word in ("synthetic","simulated","agent"))
        for p in people)
    return {"status": "PASS" if valid else "WAITING_FOR_HUMAN",
            "requires_owner_attestation": True,
            "reason": "Independent real-user observations need an owner review bound to this batch."}

def evaluate_quality(matrix, evidence, defects, build_sha):
    result = {"status": "UNVERIFIED", "passed": 0, "total": 0, "reasons": []}
    def finish(status, reason):
        return result | {"status": status, "reasons": [reason]}
    try:
        if type(matrix.get("revision")) is not int or matrix["revision"] < 1:
            return finish("UNVERIFIED", "Invalid matrix revision")
        if evidence.get("matrix_digest") != digest(matrix) or evidence.get("build_sha") != build_sha:
            return finish("UNVERIFIED", "Matrix/build changed or evidence is stale")
        cases = matrix["cases"]
        ids = [case["id"] for case in cases]
        if not all(type(cid) is str and cid.strip() for cid in ids) or len(set(ids)) != len(ids):
            return finish("UNVERIFIED", "Case IDs must be unique and nonempty")
        applicable = []
        for case in cases:
            if type(case.get("applicable", True)) is not bool:
                return finish("UNVERIFIED", "Invalid applicability")
            if case.get("applicable", True):
                applicable.append(case)
            elif not case.get("na_reason"):
                return finish("UNVERIFIED", "N/A cases require an approved matrix reason")
        result["total"] = len(applicable)
        covered = {r for case in applicable for r in case["requirement_ids"]}
        if not applicable or not set(matrix["requirements"]) <= covered:
            return finish("UNVERIFIED", "Empty or incomplete requirement coverage")
        rows = evidence["results"]
        if len({r["case_id"] for r in rows}) != len(rows) or any(r["case_id"] not in ids for r in rows):
            return finish("UNVERIFIED", "Duplicate or foreign results")
        indexed = {r["case_id"]: r for r in rows}
        for row in rows:
            if row["status"] not in {"passed","failed","skipped","blocked","not-run","xfail"}:
                return finish("UNVERIFIED", "Unknown result status")
            if type(row.get("attempts",1)) is not int or row.get("attempts",1) < 1:
                return finish("UNVERIFIED", "Invalid attempt count")
        for case in applicable:
            row = indexed.get(case["id"], {})
            passed = row.get("status") == "passed" and (row.get("attempts",1) == 1 or matrix.get("accept_retry_pass") is True)
            result["passed"] += int(passed)
            if case.get("critical") and not passed:
                return finish("FAIL", "Required critical case did not pass")
        for defect in defects:
            if defect.get("status") in {"closed","resolved","false-positive"}:
                if defect.get("status") == "false-positive" and not defect.get("review_evidence"):
                    return finish("UNVERIFIED", "False positive lacks review evidence")
                if defect.get("status") in {"closed","resolved"} and not (defect.get("fix_evidence") and defect.get("retest_evidence")):
                    return finish("UNVERIFIED", "Resolved finding lacks fix and retest evidence")
                continue
            severity = str(defect.get("severity","unknown")).lower()
            if severity not in {"low","medium","high","critical"}:
                return finish("UNVERIFIED", "Unknown defect severity")
            if severity in {"high","critical"}:
                return finish("FAIL", "Open High/Critical defect")
        if 100 * result["passed"] <= 95 * result["total"]:
            return finish("FAIL", "Pass rate must be strictly greater than 95%")
        return finish("PASS", "Applicable matrix exceeds 95%; no open High/Critical")
    except (KeyError, TypeError, ValueError, UnicodeError, AttributeError):
        return finish("UNVERIFIED", "Malformed quality evidence")

