# project-builder Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** สร้าง project-builder ให้ทำงานเป็นทีม AI ตาม scope ส่งมอบเป็น Stage และรักษาเพดานอำนาจ/ทรัพยากรบน Windows/macOS ผ่าน Codex, Claude Code และ Devin CLI/Desktop

**Architecture:** Shared Python core คุม workflow/state/policy/environment/resources และให้ host adapters บาง ๆ แปลงการเรียกใช้กับ native delegation แต่ละ host ใช้ local MCP stdio server โดยไม่มี cloud service ของเรา สิทธิ์ repository ที่จำกัดจากภายนอกใช้บังคับเพดานร่วมกับ action layer

**Tech Stack:** CPython 3.14.4; official mcp 2.3.0; pydantic 2.14.3; psutil 7.2.2; httpx 0.28.1; PyYAML 6.0.3; sqlite3 จาก stdlib; pytest 9.2.0; PyInstaller 6.22.3; uv 0.11.20; project-local Playwright/Node เมื่อจำเป็น

**Spec:** [แบบที่ผู้ใช้ยืนยัน v0.4](../specs/2026-11-06-project-builder-design.md)

วันที่: 7 พฤศจิกายน 2026 (Asia/Bangkok)  
สถานะ: ผู้ใช้ยืนยันแผนและเลือก Subagent-driven วันที่ 7 พฤศจิกายน 2026; เริ่ม execution ที่ PoC โดยบันทึกผลจริงแยกจากเป้าหมายรับรอง  
ผู้ใช้ตอบ “โอเค” หลังสรุปแบบ v0.4; บันทึกเป็นการยืนยันแบบ ไม่ใช่การยืนยันว่า capability tests ผ่านแล้ว

## Global Constraints

ข้อกำหนดต่อไปนี้คัดค่าจาก spec และใช้กับทุก task:

- ชื่อ project-builder สำหรับเจ้าของและเพื่อน
- รองรับ Codex, Claude Code, Devin เฉพาะ CLI/Desktop บน Windows และ macOS ในรุ่นแรก
- ใช้แกนกลางเดียว พร้อมตัวเชื่อมต่อแต่ละแพลตฟอร์ม
- มี BA, PM, SA, DL (Development Lead), BE, FE, Data Engineer, AI Engineer, QA(SIT/UAT), UX/UI Designer, DevSecOps
- แยก agent เฉพาะเมื่อจำเป็น จัดและบริหารทีมตาม scope และทรัพยากร
- รองรับงานเริ่มจากศูนย์ รับงานไม่เสร็จ และพัฒนาเวอร์ชันใหม่
- ใช้ Agile/Scrum และแบ่งการทำงานเป็น Stage ของโปรเจ็กต์หรือฟีเจอร์
- ประเมิน PoC/MVP/Beta/Final ทุกครั้ง ใช้ Stage น้อยที่สุดตามฟีเจอร์ที่ใช้งานจริงเทียบกับ requirement
- ตรวจหรือสร้าง main, staging, develop ก่อนเริ่มพัฒนา
- เส้นทางแตก branch คือ develop → Stage branch → feature branch; รวมกลับ feature → Stage → develop
- เก็บ Stage branches และเลิกเก็บ feature branches เมื่อรวมงานครบแล้ว
- Final ต้องผ่าน test cases มากกว่า 95% ตาม matrix ที่ครอบคลุมประเภทการทดสอบที่จำเป็น
- Final ต้องไม่มีปัญหาระดับ High ขึ้นไปค้างอยู่
- ตกลงอำนาจก่อนเริ่มงาน เพดานสูงสุดคือเปิด PR เข้า staging; คำสั่งผู้ใช้เพิ่มเพดานไม่ได้
- ควบคุมทรัพยากรที่รันอยู่ และเก็บกวาดสิ่งชั่วคราวเมื่อเลิกใช้
- มีหรือรู้วิธีใช้ Playwright และ add-on ที่จำเป็นต่อ UX/UI/design/testing
- ทุก Stage มี user guide สำหรับรัน local
- Kickoff ต้องรีวิวครบจาก business level ถึง technical level; การเก็บ requirement ต้องซักให้ได้คำตอบชัดเจน
- มีผู้ใช้จริง 2–3 คนที่ไม่รู้บริบทและไม่รู้จักกัน ให้ feedback อิสระหลังจบทุกรอบพัฒนา Stage และครั้งแรกที่รับโปรเจ็กต์เดิมมาทำต่อ เพื่อค้นหาปัญหา UX/UI และช่วยสร้าง requirement
- ศึกษา Elephant-Goldfish Model เป็นแนวทาง ปรับใช้ได้ ไม่ต้องทำตามทั้งหมด
- รับมือข้อจำกัด runtime/dependency versions ของงานเดิมโดยแยก environment ของโปรเจ็กต์ และมีคำแนะนำตั้งค่าแบบทีละขั้นเมื่อจำเป็น
- มีคำสั่งที่เข้าใจง่าย เช่น init, start, continue, status ภายใต้ชื่อ project-builder
- ไอเดียหรือการเปลี่ยน requirement ที่ไม่เร่งด่วนระหว่างงานให้เก็บ backlog ก่อน ทำ Stage ที่ตกลงไว้ให้จบ แล้วทวนกับผู้ใช้ก่อนเริ่มรอบใหม่

เงื่อนไขเชิงตัวเลข: 3 hosts × 2 surfaces × 2 OS = 12 target combinations; default 1 specialist/1 heavy job; ผู้ทดลอง 2–3 คน; 95.00% ไม่ผ่าน; High/Critical ที่ค้าง = 0; LOCAL_ONLY ไม่ถือว่า release-complete

## Review Focus

- RF1: path ภาษาไทย/ช่องว่าง, metacharacters และ hostile argv ต้องไม่กลายเป็น shell execution หรือ escape ออกจาก ownership — Tests Tasks 4/7/12
- RF2: delayed response, duplicate request และ worker เก่าหลัง pause/rebaseline ต้องไม่เริ่มงาน/เขียน state/เปิด PR ซ้ำ — Tests Tasks 2/10/11/12
- RF3: fake passed artifacts, duplicate cases, retry-only pass และ stale evidence ต้องไม่ทำให้ Final ผ่าน — Tests Task 13
- RF4: parent crash, detached descendants, PID reuse และ partial cleanup ต้องรักษาของผู้ใช้และไม่รายงาน clean แบบไม่มีหลักฐาน — Tests Tasks 4/15/18
- RF5: conflicting runtime pins, incompatible architecture และ venv เก่าต้องไม่เปลี่ยน global environment หรือ auto-upgrade requirement — Tests Task 7

---

## Execution clarification — คำชี้แจงจากผู้ใช้วันที่ 7 พฤศจิกายน 2026

ผู้ใช้แก้ความเข้าใจของผู้สร้าง: เงื่อนไขทดลองโดยผู้ใช้จริง 2–3 คนและ workflow Stage เป็นงานที่ **ตัว project-builder ต้องทำให้โปรเจ็กต์ที่รับผิดชอบ** ไม่ใช่การขอให้เจ้าของจัดหาผู้ทดลอง/เครื่อง Mac ก่อนสร้างปลั๊กอินนี้ให้เสร็จ

คำชี้แจงนี้มีลำดับสูงกว่าข้อความ acceptance ของการสร้างปลั๊กอินในแผนฉบับก่อน:
- ดำเนินการสร้างทั้ง 19 งานต่อเนื่องตาม dependency; PoC/MVP/Final ในแผนนี้เป็นจุดรวมและทดสอบ implementation ไม่เพิ่ม human gate ที่เจ้าของไม่ได้ร้องขอสำหรับงานสร้างตัวปลั๊กอิน
- Human/baseline/stage feedback, >95%, High+=0, guides, resource lifecycle และ authority ceiling ยังคงเป็นพฤติกรรมผลิตภัณฑ์ที่ต้อง implement และทดสอบครบ; ใช้ fixtures ทดสอบพฤติกรรม แต่ห้ามปลอมว่า fixture คือผู้ทดลองจริงในโปรเจ็กต์ที่ปลั๊กอินรับทำ
- งาน T6/T17/T19 ต้องส่งซอฟต์แวร์ ชุดทดสอบ คู่มือติดตั้ง/ใช้งาน และ capability report ตามหลักฐานที่มีจริง ไม่หยุดสร้างเพราะยังไม่ได้จัด native host matrix หรือ real-human trial ของตัวปลั๊กอินเอง
- ทดสอบ Windows ที่มีจริง; สร้าง native macOS test/build automation และคำแนะนำให้ทำซ้ำได้; ผลที่ยังไม่รันรายงาน NOT_RUN/UNVERIFIED ไม่อ้างว่าผ่าน แต่ไม่ถือว่าโค้ดสร้างต่อไม่ได้
- Gate evaluators ของผลิตภัณฑ์ยังต้องปฏิเสธ evidence ที่ไม่ครบในโครงการลูกค้าตาม contract ที่เลือกจริง; ความครบของ implementation ไม่ใช่การประกาศว่าทั้ง 12 native installations ได้รับการรับรองแล้ว
- Beta เพิ่มเฉพาะหากพบ gap ที่ต้องแก้; ถ้าไม่จำเป็นให้บันทึก skipped ไม่สร้างกิจกรรมเปล่า

## 1. Scope, Stage path และสิ่งที่ต้องมีก่อน execution

ส่วนประกอบพึ่ง interface/state/policy ชุดเดียวกัน จึงใช้แผนหลักหนึ่งฉบับ แบ่งเป็น deliverables ที่ตรวจรับแยกกัน ไม่เปิดโครงการอิสระหลายชุดที่กฎอาจต่างกัน

เส้นทางเสนอจากสถานะ repo ที่มีเพียง README กับร่างเอกสาร: **PoC → MVP → Final** โดย **Beta เป็น conditional** เพิ่มเมื่อผล MVP ชี้ว่าต้องทดลองความเสถียร/การติดตั้ง/UX ต่อ PoC จำเป็นเพราะยังไม่พิสูจน์ authority enforcement, process lifecycle และ host invocation ข้าม OS จริง ไม่มี Stage ใดข้าม human feedback/guide ที่จำเป็นได้

ก่อนเริ่มแต่ละ Stage ต้องตกลง scope, allowed lower-level Git actions, setup authority, resource budget และผู้ประสานงานผู้ทดลอง ไม่ใช้ “โอเค” ที่ยืนยันแบบเป็นสิทธิ์ติดตั้ง global tools หรือเปิด PR กับ repo ใดก็ได้

สิ่งที่ต้องเตรียมสำหรับ acceptance:
- เครื่อง Windows และ macOS รวม native architectures ที่จะออก artifact; host/license ที่เปิด CLI/Desktop ของทั้งสามได้
- repository sandbox ที่ระบุชื่อแน่นอน พร้อม AI identity ที่ไม่มีสิทธิ์อัปเดต existing main/staging หรือแก้/bypass protections และมีสิทธิ์ที่อนุญาตเท่านั้น
- read access เพื่อตรวจ identity/rules/workflow ที่เกี่ยวข้อง; ถ้าขาดใช้ LOCAL_ONLY และไม่อ้าง remote-verified
- ผู้ทดลองจริง 2–3 คนต่อ Stage โดยเจ้าของจัดหา; ไม่มีการส่งคำเชิญหรือข้อความโดยไม่ได้รับคำสั่ง
- release/host evidence ไม่สามารถสร้างจาก unit-test fixtures หรือจำลองว่าเกิดขึ้นแล้ว

ตอนวางแผนตรวจพบ python 3.14.4, Node v24.15.0 และ uv 0.11.20 ในเครื่อง Windows นี้ ข้อมูลนี้ไม่ยืนยันว่ามี runtime/host/macOS ที่ใช้รับรองครบแล้ว ไม่ได้ติดตั้ง dependencies ระหว่างเขียนแผน

## 2. Technical choices และ dependency policy

เลือก Python เพราะทำ local process/state tooling ได้โดยไม่เพิ่มอีกภาษาให้ core ใช้ explicit isolated development environment และแพ็ก runtime เพื่อไม่พึ่ง Python ของโปรเจ็กต์ลูกค้า SQLite เป็น runtime database file ขนาดเล็กผ่าน stdlib ไม่ใช่ server; ช่วย transactional state/idempotency และ resource reservations ส่วน artifacts ที่แชร์ยังเป็น Markdown/JSON

Direct pins ใน Tech Stack ตรวจจาก official PyPI metadata วันที่ 7 พฤศจิกายน 2026 ให้สร้าง uv.lock ตอน Task 1 และใช้ --frozen ต่อจากนั้น ไม่ resolve latest ระหว่าง run และไม่เพิ่ม remote LLM API key: delegation ใช้ host ที่ติดตั้งอยู่แล้ว

MCP ใช้ SDK 2.3.0 และ MCPServer จาก mcp.server ไม่ใช้ import FastMCP v1 ที่ล้าสมัย การ validate tool arguments ต้องเกิดใน core เองด้วย ไม่ถือว่า advertised schema เป็น enforcement
Playwright เป็น stack ของโปรเจ็กต์ UI/fixture ไม่ใช่ dependency ที่ติดตั้ง browser ให้ทุกโปรเจ็กต์

Baseline resource policy สำหรับทดลอง/calibration (ค่าที่ผู้ออกแบบเลือก ไม่ใช่ค่าที่ผู้ใช้ยืนยันเป็นสากล):
- max_active_specialists=1, max_heavy_jobs=1; global machine ledger ใช้ร่วมกันทุก project/host
- reserve_ram_bytes=max(1 GiB, 20% physical RAM); disk reserve=max(1 GiB, min(5 GiB, 5% volume size))
- heartbeat interval=2s; lease TTL=15s; graceful shutdown=5s; sample interval=2s
- unknown memory estimate ไม่เริ่ม heavy workload; pressure ต่ำกว่า reserve 2 samples ติดต่อกันหยุดรับงานใหม่และพัก/หยุด workload ของเรา
- สิทธิ์ hard-limit ที่ OS ทำได้กับ monitoring/admission ต้องรายงานแยก ไม่อ้างว่า macOS กับ Windows มี kernel guarantees เหมือนกัน
- ปรับค่าจากผล PoC พร้อมเหตุผลก่อน MVP และบันทึกใน Stage contract; ห้าม calibration ทำให้เครื่องเจ้าของใช้งานไม่ได้

## 3. Repository/branch procedure ที่ใช้กับทุก task

ก่อน execution ตรวจ AGENTS.md ใหม่และอ่าน spec/plan ทั้งคู่ แล้วใช้ using-git-worktrees เมื่อจำเป็นต้องแยก workspace
1. ตรวจ dirty worktree/refs/remote จริง ระบุ baseline SHA ที่ตกลง; รักษา docs ที่มีอยู่และไม่ stash/reset งานคนอื่นเงียบ ๆ
2. สร้าง local develop และ staging จาก main baseline เฉพาะที่ขาด; remote bootstrap ทำเฉพาะสิทธิ์ create-only ที่ตรวจแล้ว ถ้าไม่พร้อมให้ผู้ดูแลเตรียม
3. สร้าง active Stage เช่น stage/pb-v0-1/poc จาก develop
4. ก่อน task สร้าง feature/pb-v0-1/<stage>/<task-slug> จาก active Stage; ไม่ทำ task บน main/develop/Stage branch โดยตรง
5. เมื่อ task ผ่าน verification/review จึงรวม feature → Stage ตามอำนาจ และลบ feature เฉพาะเมื่อไม่มีงานค้าง; เก็บ Stage branch
6. หลัง Stage มี guide+feedback+exit evidence+cleanup แล้ว จึงรวม Stage → develop ตามอำนาจ; Stage ถัดไปเริ่มจาก develop ที่อัปเดตแล้ว
7. Final จบสูงสุดที่ PR develop → staging เมื่อมีอำนาจ; ห้าม merge/auto-merge/enqueue/main/prod

Task 1 commit เอกสาร spec/plan ที่มีอยู่พร้อม foundation บน feature branch เพื่อไม่ commit planning artifacts ลง main ระหว่างเตรียมแผน ตอนเขียนแผนยังไม่สร้าง branch/commit/push ใด

## 4. File map และเจ้าของ interface

- src/project_builder/contracts.py, cli.py และ workflow/models.py: strict cross-module contracts, StageReport schema และ local entry point — T1
- state/: private transactional state, revisions, operations — T2
- policy/ + git/github_inspector.py: immutable ceiling และ enforcement evidence — T3
- supervision/ + platform_paths.py: owned child lifecycle, global budget, native drivers — T4
- transport/, adapters/*/adapter.json, entry skill: MCP/native capability boundary — T5
- quality/poc_gate.py และ PoC docs — T6
- environment/: runtime discovery/isolation/setup recipes — T7
- workflow/intake.py, kickoff.py, requirements.py: business-to-technical discovery — T8
- workflow/stages.py, transitions.py, backlog.py: minimal Stage path และ work state — T9
- team/ + roles/: team selection/assignment/fresh context — T10
- commands/ + changes/: simple intents, cancellation, frozen-scope queue — T11
- git/refs.py, workflow.py, github_actions.py: allowed Git routes/receipts — T12
- quality/models.py, matrix.py, final_gate.py, parsers.py: coverage/results/Final gate — T13
- tools/ + templates/playwright/: optional tools/browser execution — T14
- feedback/, guides/, workflow/handoff.py: human evidence/guide/closure — T15
- packaging/, packaging/render.py, scripts/build_* และ adapter manifests: distributables — T16
- acceptance scenarios และ MVP/Beta/Final evidence: T17–T19

## 5. Data contracts ที่ Tasks ต้องใช้ชื่อให้ตรงกัน

Core contracts (T1):
- Stage = Literal["poc","mvp","beta","final"]; RunStatus = Literal["INTAKE","ASSESSED","BASELINE_CAPTURE","BASELINE_FEEDBACK","REQUIREMENT_REFINEMENT","KICKOFF_REVIEW","READY","RUNNING","VERIFYING","DEVELOPMENT_COMPLETE","STAGE_FEEDBACK","FEEDBACK_TRIAGE","HANDOFF","COMPLETED","NEEDS_INPUT","WAITING_FOR_HUMAN","RESOURCE_WAIT","PAUSED","FAILED","CANCELLED","CLEANUP_PENDING"]
- RunIdentity(project_id: str, run_id: str, scope_id: str, stage: Stage, contract_revision: int)
- StageContract(project_id, scope_id, stage, revision, requirements_version, feature_ids: list[str], allowed_actions: frozenset[str], test_matrix_revision: int, participant_count: Literal[2,3], approved_receipt_id: str | None); ขอบเขต/authority เพิ่มผ่าน approval receipt ไม่ผ่าน model Boolean
- ApprovalReceipt(id: str, contract_digest: str, source: str, event_binding: str, approved_at: datetime, expires_at: datetime | None); source ต้องตรวจจาก host/user-review path ที่ probe แล้ว ไม่รับ caller อ้างเอง
- CommandEnvelope(request_id: str, project_root: Path, run_id: str | None, expected_revision: int | None, intent: CommandIntent, payload: discriminated model)
- ActionRequest(kind: ActionKind, project_id: str, run_id: str, source_ref: str | None, target_ref: str | None, expected_sha: str | None, operation_id: str); ActionKind รวม known forbidden operations เพื่อให้ policy ปฏิเสธได้อย่างชัดเจน แต่ห้าม advertise เป็น executable tools; unknown action/free-form shell ไม่ผ่าน schema
- ActionDecision(allowed: bool, code: str, reasons: list[str]); GateResult(status: Literal["PASS","FAIL","UNVERIFIED"], reasons: list[str], evidence_ids: list[str])
- CommandResult(status: str, summary: str, next_action: str | None, data: dict); text renderer ไม่ต้องแสดง internal data ทั้งหมด
- ScopeProfile(feature_ids, domains, complexity, estimated_work); RiskProfile(security, privacy, reliability, data_ai, unknowns); TeamBudget(max_active_specialists=1, max_heavy_jobs=1); TeamPlan(selected_roles, role_responsibilities, max_active_specialists, reviewer_strategy) เป็น schemas ใน contracts.py (T1), planner implementation เป็น T10
- StageReport(run: RunIdentity, contract_digest: str, commit_sha: str, tree_digest: str, env_fingerprint: str, matrix_revision: int, evidence_ids: list[str], gate_ids: list[str], pending_changes: list[str], status: RunStatus) อยู่ workflow/models.py (T1); ไม่ import service/types ที่ยังไม่สร้าง

Owner-defined models ที่ประกาศใน Interfaces ของ task เป็น output contract ของ task นั้น ต้อง export จาก module ที่ระบุ ไม่สร้าง DTO ชื่อใกล้กันเองใน downstream tasks
RepositoryRef/RemoteIdentity/BuildIdentity/WorkItem/StageReport เป็น models ของ task ที่ใช้ครั้งแรก: RepositoryRef และ RemoteIdentity ใน policy/models.py (T3), BuildIdentity ใน quality/models.py (T13), WorkItem ใน workflow/backlog.py (T9), StageReport ใน workflow/models.py (สร้าง schema ขั้นต่ำใน T1 แล้วเติม service ใน T15)
Task ที่ยังไม่พร้อมให้ core ตอบ NOT_IMPLEMENTED/UNVERIFIED ตามข้อเท็จจริง ไม่ใส่ stub ผ่าน gate

ลำดับ type/service ใช้กฎนี้เพื่อให้แต่ละ task ทดสอบแยกได้:
- state/models.py (T2) เพิ่ม EvidenceRef(id, kind, producer_id, build_digest, contract_digest, content_digest, observed_at, provenance) และ EvidenceIndex(records: dict[str,EvidenceRef]); GateEvidence ใน T3 อ้าง IDs ที่ StateStore ตรวจ digest แล้ว
- transport/models.py (T5) เป็นเจ้าของ HostTarget, HostContext(capabilities, trusted_approval_channel, host_session_id), HostProbeReport และ observed-version/native-evidence records; ห้ามเอา model args มาเติม trusted fields
- quality/poc_gate.py (T6) เป็นเจ้าของ PoCRecords(authority_records, resource_records, host_records, guide_records, participant_records) และ PoCDecision; ใช้ evidence schema ขั้นต่ำนี้ก่อนบริการ feedback เต็มรูปแบบ T15
- workflow/requirements.py (T8) เป็นเจ้าของ RepositoryEvidence, IntakeAssessment, BusinessBrief, DiscoveryQuestion, RequirementSet, FeatureInventory, FeatureEvidenceSet และ MatrixDraft; FeatureEvidenceSet มี requirement/build/evidence IDs กับ VERIFIED/UNKNOWN/FAILED; kickoff.py เป็นเจ้าของ KickoffPackage และรับ TeamPlan schema/draft matrix โดยยังไม่เรียก planners/gates ของ task อนาคต
- workflow/transitions.py (T9) เป็นเจ้าของ WorkflowEvent(kind, request_id, expected_revision, evidence_ids); stages.py เป็นเจ้าของ StagePath; ใช้ EvidenceIndex จาก T2 และรอ gate service ที่ยังไม่มีด้วย UNVERIFIED
- team/assignments.py (T10) เป็นเจ้าของ WorkAssignment, WorkResult, WorkReceipt รวม revision/worker/lease/evidence bindings; team/planner.py ใช้ schemas จาก T1
- commands/router.py (T11) เป็นเจ้าของ Services Protocol: state, policy, supervisor และ registry ของ handlers ที่ implement แล้ว; handler ที่ยังไม่พร้อมไม่ถูก advertise ว่าทำได้ changes/service.py เป็นเจ้าของ ChangeProposal(id, description, urgency, source_event_id), ChangeItem(proposal, run, status, accepted_stage) และ ChangeReviewPacket(items, impact_summary, decision_receipt_ids)
- git/models.py (T12) เป็นเจ้าของ GitReceipt(operation_id, source_sha, target_sha, result, evidence_ids) และ PRPlan(repo, source_ref, source_sha, target_ref, report_digest, operation_id); integration รับ gate receipt ที่ตรวจได้ บริการ T13/T15 ยังไม่พร้อมต้อง block remote handoff ไม่ใช้ fake success
- quality/models.py (T13) เป็นเจ้าของ BuildIdentity/TestMatrix/CaseResult/TestRunEvidence/Defect; tools/registry.py และ tools/playwright.py (T14) เป็นเจ้าของ ToolInventory/ToolPlan/ToolSpec และ BrowserTestRecipe ตามลำดับ
- feedback/service.py และ guides/service.py (T15) เป็นเจ้าของ FeedbackBatch/Receipt/Triage และ GuideArtifact/Verification; complete_stage คืน GateResult เท่านั้น ส่วน WAITING_FOR_HUMAN อยู่ RunSnapshot/CommandResult ที่ service/fixture adapter คืน ไม่เพิ่ม status นี้ลง GateResult
- packaging/render.py (T16) เป็นเจ้าของ RuntimeTarget/RuntimeArtifact/PluginArtifact/ArtifactReport; quality/{mvp_gate,beta_gate,release_gate}.py (T17–T19) เป็นเจ้าของ delivery input/report ของ gate นั้น

ชื่อ helper เช่น matrix(), results(), evidence(), action() และ service fixture ใน test snippets เป็น fixtures/builders ใน conftest ของ task ไม่ใช่ production API และต้องสร้างตัวอย่าง valid ก่อนเปลี่ยนเฉพาะเงื่อนไขที่ต้องการตรวจ

Tests ใช้ fixtures ใน tests/conftest.py และ conftest.py ของ module เจ้าของ task; fixture สร้างข้อมูลสังเคราะห์ได้เฉพาะ automated tests ต้องติด test provenance และไม่มีทางเข้าไปแทน native host/human release evidence

## 6. Task graph

PoC: T1 → T2 → T3/T4 → T5 → T6  
MVP: T7 → T8 → T9 → T10 → T11 → T12 → T13 → T14 → T15 → T16 → T17  
Optional Beta: T18 เมื่อ assessment เลือก  
Final: T19

T3/T4 พัฒนาแยกกันได้เมื่อใช้ interfaces T1/T2 เดียวกัน แต่ค่าเริ่มต้นทำเรียงเพื่อลดเครื่องมือ/context และความเสี่ยง integration การเลือก execution method เป็นของผู้ใช้ ไม่ใช่การเริ่ม delegation อัตโนมัติจากแผนนี้

### Task 1: Contracts, validation และ CLI ที่ไม่เปลี่ยนระบบโดยปริยาย

**Stage:** PoC

**Files:**
- Create: pyproject.toml, uv.lock, .python-version, src/project_builder/__init__.py, src/project_builder/__main__.py
- Create: src/project_builder/contracts.py, src/project_builder/cli.py, src/project_builder/workflow/models.py
- Test: tests/test_contracts.py, tests/conftest.py

**Interfaces:**
- Produces: StageContract, RunIdentity, CommandEnvelope, ActionRequest, ActionDecision, ApprovalReceipt, GateResult, CommandResult, ScopeProfile, RiskProfile, TeamBudget, TeamPlan และ StageReport schema ตาม Data contracts ด้านบน
- Produces: parse_command(argv: list[str]) -> CommandEnvelope; main(argv: list[str] | None = None) -> int
- Consumes: ไม่มี production interface ก่อนหน้า; รับ OS/path/version เป็นข้อมูล ไม่เริ่ม subprocess จาก import

- [x] **Setup 1:** สร้าง metadata พร้อม exact direct pins ใน Tech Stack และ console entry point project-builder = project_builder.cli:main; .python-version เป็น 3.14.4 และ .venv อยู่ในรายการ ignore โดยรักษา entries เดิม
- [x] **Setup 2:** กำหนด pytest pythonpath=['src'] ใน pyproject.toml แล้วรัน uv lock --python 3.14.4 และ uv sync --frozen --no-install-project --python 3.14.4 ใน environment ที่ kickoff อนุญาต ก่อนทำ RED; RED ใช้ --no-sync เพื่อไม่ trigger editable build ก่อนมี package; หลังเพิ่ม src ใช้ uv sync --frozen เพื่อ install เฉพาะโปรเจ็กต์นี้

- [x] **Step 1: เขียน failing tests ใน tests/test_contracts.py, tests/conftest.py** — ประกาศ fixtures ของ task ใน test/conftest เดียวกัน พร้อม assertions ต่อไปนี้และกรณีเพิ่มเติมที่ระบุ

~~~python
def test_rejects_model_claimed_approval(raw_contract):
    with pytest.raises(ValidationError):
        StageContract.model_validate({**raw_contract, "approved": True})
def test_rejects_unknown_action_and_shell_payload():
    with pytest.raises(ValidationError):
        ActionRequest.model_validate({"kind": "run_arbitrary_shell", "argv": "echo ok; deploy"})
def test_status_parse_is_read_only():
    assert parse_command(["status", "--project", "fixture"]).intent == "status"
~~~

- [x] **Step 2: รัน RED**

Run: uv run --frozen --no-sync --python 3.14.4 pytest tests/test_contracts.py -q  
Expected: FAIL เพราะ interface/behavior ที่ task นี้รับผิดชอบยังไม่มี; ไม่ถือ import/dependency failure ที่ไม่เกี่ยวข้องเป็นหลักฐาน RED

- [x] **Step 3: Implement interfaces ในไฟล์เจ้าของ task**

ใช้ Pydantic strict models, extra='forbid', discriminated command payloads และ argparse แยก text output กับ --json; ไม่รับ Boolean จาก model เป็นหลักฐานอนุมัติ



- [x] **Step 4: รัน GREEN และตรวจผลส่งมอบ**

Run: uv run --frozen --python 3.14.4 pytest tests/test_contracts.py -q  
Expected: PASS ทุก test ที่เลือกบน environment ที่ระบุ พร้อมตรวจ receipts/artifacts ตาม task; native/human checks ที่ยังไม่ทำต้องแสดง WAITING/UNVERIFIED ห้ามแทนด้วย unit-test PASS

- [x] **Step 5: Commit บน feature branch ของ task เท่านั้น**

ตรวจ diff เฉพาะไฟล์ task และ evidence ที่แชร์ได้ แล้วใช้ git add กับรายการไฟล์ที่ระบุชัด (ไม่ git add . ที่อาจเก็บข้อมูลผู้ทดลอง/secrets)  
Commit: git commit -m "feat: define strict project contracts and command entry point"  
หลัง review ผ่านจึงรวมกลับ active Stage ตาม procedure; commit ไม่ใช่หลักฐานว่า Stage ผ่านแล้ว


### Task 2: Local state, operation receipts และการกู้จาก crash

**Stage:** PoC

**Files:**
- Create: src/project_builder/state/store.py, src/project_builder/state/migrations/001_initial.sql
- Create: src/project_builder/state/models.py
- Test: tests/state/test_store.py

**Interfaces:**
- Produces: StateStore(path: Path); create_run(contract: StageContract) -> RunIdentity; compare_and_set(run: RunIdentity, expected_revision: int, patch: dict) -> RunSnapshot
- Produces: begin_operation(operation_id: str, fingerprint: str) -> OperationReceipt; complete_operation(operation_id: str, outcome: dict) -> OperationReceipt; read_operation(operation_id: str) -> OperationReceipt | None
- Produces: RunSnapshot(identity, status, revision, contract_digest, pending_changes, evidence_ids); OperationReceipt(id, fingerprint, status, outcome)

- [ ] **Step 1: เขียน failing tests ใน tests/state/test_store.py** — ประกาศ fixtures ของ task ใน test/conftest เดียวกัน พร้อม assertions ต่อไปนี้และกรณีเพิ่มเติมที่ระบุ

~~~python
def test_stale_writer_cannot_overwrite_new_revision(store, ready_run):
    store.compare_and_set(ready_run, 1, {"status": "RUNNING"})
    with pytest.raises(StaleRevision):
        store.compare_and_set(ready_run, 1, {"status": "COMPLETED"})
def test_replayed_operation_returns_same_receipt(store):
    assert store.begin_operation("op-1", "same") == store.begin_operation("op-1", "same")
    with pytest.raises(OperationConflict):
        store.begin_operation("op-1", "different")
~~~

- [ ] **Step 2: รัน RED**

Run: uv run --frozen --python 3.14.4 pytest tests/state/test_store.py -q  
Expected: FAIL เพราะ interface/behavior ที่ task นี้รับผิดชอบยังไม่มี; ไม่ถือ import/dependency failure ที่ไม่เกี่ยวข้องเป็นหลักฐาน RED

- [ ] **Step 3: Implement interfaces ในไฟล์เจ้าของ task**

ใช้ sqlite3 transaction/WAL และ versioned schema; commit operation intent ก่อน side effect, outcome หลังตรวจผล; crash ระหว่าง intent/outcome ให้ UNKNOWN ไม่เดาว่าสำเร็จ; serialize mutation ต่อ run

- เพิ่ม process-level test เปิดสอง connections และ kill writer ก่อน commit: connection ใหม่ต้องอ่าน revision เก่าหรือใหม่ที่สมบูรณ์ ไม่เห็นครึ่ง transaction
- ใช้ user-local runtime storage ตาม PlatformPaths; export artifacts ที่แชร์ได้เป็น JSON/Markdown แทน commit database

- [ ] **Step 4: รัน GREEN และตรวจผลส่งมอบ**

Run: uv run --frozen --python 3.14.4 pytest tests/state/test_store.py -q  
Expected: PASS ทุก test ที่เลือกบน environment ที่ระบุ พร้อมตรวจ receipts/artifacts ตาม task; native/human checks ที่ยังไม่ทำต้องแสดง WAITING/UNVERIFIED ห้ามแทนด้วย unit-test PASS

- [ ] **Step 5: Commit บน feature branch ของ task เท่านั้น**

ตรวจ diff เฉพาะไฟล์ task และ evidence ที่แชร์ได้ แล้วใช้ git add กับรายการไฟล์ที่ระบุชัด (ไม่ git add . ที่อาจเก็บข้อมูลผู้ทดลอง/secrets)  
Commit: git commit -m "feat: persist run state and idempotent operation receipts"  
หลัง review ผ่านจึงรวมกลับ active Stage ตาม procedure; commit ไม่ใช่หลักฐานว่า Stage ผ่านแล้ว


### Task 3: Hard authority ceiling และ GitHub preflight ที่ตรวจได้

**Stage:** PoC

**Files:**
- Create: src/project_builder/policy/authority.py, src/project_builder/policy/preflight.py
- Create: src/project_builder/git/github_inspector.py, src/project_builder/policy/models.py
- Test: tests/policy/test_authority.py, tests/policy/test_preflight.py

**Interfaces:**
- Produces: authorize(action: ActionRequest, contract: StageContract, proof: EnforcementReport, evidence: GateEvidence) -> ActionDecision
- Produces: inspect_enforcement(repo: RepositoryRef, identity: RemoteIdentity) -> EnforcementReport
- Produces: EnforcementReport(mode, repo, actor_id, refs_digest, rules_digest, workflows_digest, checked_at, expires_at, reasons); GateEvidence เป็น IDs/digests จาก StateStore ไม่ใช่ caller-supplied passed flag

- [ ] **Step 1: เขียน failing tests ใน tests/policy/test_authority.py, tests/policy/test_preflight.py** — ประกาศ fixtures ของ task ใน test/conftest เดียวกัน พร้อม assertions ต่อไปนี้และกรณีเพิ่มเติมที่ระบุ

~~~python
@pytest.mark.parametrize("kind", ["merge_staging", "push_main", "open_pr_main",
    "enable_auto_merge", "enqueue_merge", "deploy_prod", "edit_protection"])
def test_ceiling_cannot_be_overridden(kind, contract, verified_proof, evidence):
    assert not authorize(action(kind), contract, verified_proof, evidence).allowed
def test_unknown_bypass_or_workflow_is_local_only(inspector):
    assert inspector.with_unreadable_workflow().report().mode == "LOCAL_ONLY"
def test_preflight_only_uses_read_apis(recording_transport, repo, identity):
    inspect_enforcement(repo, identity)
    assert recording_transport.requests
    assert all(r.method == "GET" for r in recording_transport.requests)
~~~

- [ ] **Step 2: รัน RED**

Run: uv run --frozen --python 3.14.4 pytest tests/policy -q  
Expected: FAIL เพราะ interface/behavior ที่ task นี้รับผิดชอบยังไม่มี; ไม่ถือ import/dependency failure ที่ไม่เกี่ยวข้องเป็นหลักฐาน RED

- [ ] **Step 3: Implement interfaces ในไฟล์เจ้าของ task**

กำหนด deny operations เป็น code constants ไม่มี config override; ตรวจ actor/bypass/ref protections/triggered workflows ด้วย read APIs; binding proof กับ repo/actor/config digest และอายุสูงสุด 300 วินาที ต้อง refresh ก่อน remote mutation เมื่อ refs/config เปลี่ยน

- แยก create-only bootstrap ของ missing main/staging จาก update refs ที่มีอยู่; ไม่มีสิทธิ์ admin หรือ credential สำหรับแก้ protections
- negative tests ใช้ fake HTTP server/transport เท่านั้น ห้ามลอง push/merge/delete main/staging จริงเพื่อดูว่าจะถูกปฏิเสธหรือไม่
- proof ที่ไม่ครบให้ LOCAL_ONLY; ไม่ให้ user prompt หรือ add-on เปลี่ยน mode เป็น VERIFIED; จำกัด provider แรกเป็น github.com และปฏิเสธ remote URL ที่ไม่อยู่ใน onboarding scope

- [ ] **Step 4: รัน GREEN และตรวจผลส่งมอบ**

Run: uv run --frozen --python 3.14.4 pytest tests/policy -q  
Expected: PASS ทุก test ที่เลือกบน environment ที่ระบุ พร้อมตรวจ receipts/artifacts ตาม task; native/human checks ที่ยังไม่ทำต้องแสดง WAITING/UNVERIFIED ห้ามแทนด้วย unit-test PASS

- [ ] **Step 5: Commit บน feature branch ของ task เท่านั้น**

ตรวจ diff เฉพาะไฟล์ task และ evidence ที่แชร์ได้ แล้วใช้ git add กับรายการไฟล์ที่ระบุชัด (ไม่ git add . ที่อาจเก็บข้อมูลผู้ทดลอง/secrets)  
Commit: git commit -m "feat: enforce immutable authority ceiling and remote preflight"  
หลัง review ผ่านจึงรวมกลับ active Stage ตาม procedure; commit ไม่ใช่หลักฐานว่า Stage ผ่านแล้ว


### Task 4: Resource admission, process ownership และ supervisor สอง OS

**Stage:** PoC

**Files:**
- Create: src/project_builder/supervision/models.py, src/project_builder/supervision/ledger.py
- Create: src/project_builder/supervision/supervisor.py, src/project_builder/supervision/watchdog.py
- Create: src/project_builder/supervision/windows_job.py, src/project_builder/supervision/macos_group.py, src/project_builder/platform_paths.py
- Test: tests/supervision/test_admission.py, tests/supervision/test_cleanup.py, tests/fixtures/child_process.py

**Interfaces:**
- Produces: admit(spec: ResourceRequest, sample: MachineSample, ledger: ResourceLedger) -> AdmissionDecision
- Produces: Supervisor.start(spec: ProcessSpec, owner: RunIdentity) -> ResourceHandle; stop(handle: ResourceHandle, grace_seconds: float = 5.0) -> CleanupReceipt
- Produces: ResourceHandle(id, owner, pid, process_started_at, process_group_id, owned_paths, lease_id); PlatformPaths.user_state_root() -> Path
- ProcessSpec ใช้ executable: Path, argv: list[str], cwd: Path, env: dict[str,str], budget; ไม่รับ free-form shell string

- [ ] **Step 1: เขียน failing tests ใน tests/supervision/test_admission.py, tests/supervision/test_cleanup.py, tests/fixtures/child_process.py** — ประกาศ fixtures ของ task ใน test/conftest เดียวกัน พร้อม assertions ต่อไปนี้และกรณีเพิ่มเติมที่ระบุ

~~~python
def test_machine_budget_is_shared_between_projects(ledger, sample):
    assert admit(heavy("p1"), sample, ledger).allowed
    assert not admit(heavy("p2"), sample, ledger).allowed
def test_reused_pid_is_never_killed(supervisor, recycled_handle):
    result = supervisor.stop(recycled_handle)
    assert result.status == "OWNERSHIP_UNVERIFIED"
def test_unicode_path_and_metacharacters_are_literal(supervisor, owned_dir):
    assert run_echo(supervisor, owned_dir / "งาน ทดสอบ", ["a&b", "$(noop)"]) == ["a&b", "$(noop)"]
def test_parent_crash_cleans_descendants_and_preserves_foreign_process(crash_harness):
    result = crash_harness.crash_parent_and_reconcile()
    assert result.owned_live_workloads == 0
    assert result.foreign_process_unchanged
~~~

- [ ] **Step 2: รัน RED**

Run: uv run --frozen --python 3.14.4 pytest tests/supervision -q  
Expected: FAIL เพราะ interface/behavior ที่ task นี้รับผิดชอบยังไม่มี; ไม่ถือ import/dependency failure ที่ไม่เกี่ยวข้องเป็นหลักฐาน RED

- [ ] **Step 3: Implement interfaces ในไฟล์เจ้าของ task**

ใช้ global SQLite resource ledger ต่อเครื่อง, psutil metrics, Windows Job Objects และ macOS process group/watchdog; เริ่ม child พร้อม ownership ก่อนปล่อยทำงาน; cleanup ตรวจ pid+start time+owner ไม่ kill ตามชื่อกว้าง ๆ

- ทดสอบ success/fail/cancel/timeout/parent crash กับ descendants, detached-child fixture, PID reuse, symlink/junction escape และหลาย project แย่งงบ; รัน native ทั้ง Windows/macOS
- Windows ใช้ CreateProcessW แบบ suspended → assign Job Object → resume; ไม่อนุญาต breakaway และใช้ kill-on-close; background console ต้องไม่เปิดหน้าต่างโดยไม่จำเป็น
- macOS ต้องตรวจผล watchdog/descendant cleanup จริง; workload ที่ containment ไม่ผ่านต้องถูกปฏิเสธ admission หรือใช้ isolated driver ที่ทดสอบแล้ว ไม่รายงาน cleanup สำเร็จแบบเดา
- ถ้าข้อมูล ownership หายหรือ cleanup ล้มเหลว ให้ CLEANUP_PENDING พร้อม receipt ไม่ลบของที่ไม่ยืนยันเจ้าของ

- [ ] **Step 4: รัน GREEN และตรวจผลส่งมอบ**

Run: uv run --frozen --python 3.14.4 pytest tests/supervision -q  
Expected: PASS ทุก test ที่เลือกบน environment ที่ระบุ พร้อมตรวจ receipts/artifacts ตาม task; native/human checks ที่ยังไม่ทำต้องแสดง WAITING/UNVERIFIED ห้ามแทนด้วย unit-test PASS

- [ ] **Step 5: Commit บน feature branch ของ task เท่านั้น**

ตรวจ diff เฉพาะไฟล์ task และ evidence ที่แชร์ได้ แล้วใช้ git add กับรายการไฟล์ที่ระบุชัด (ไม่ git add . ที่อาจเก็บข้อมูลผู้ทดลอง/secrets)  
Commit: git commit -m "feat: supervise owned workloads with cross-project resource budgets"  
หลัง review ผ่านจึงรวมกลับ active Stage ตาม procedure; commit ไม่ใช่หลักฐานว่า Stage ผ่านแล้ว


### Task 5: Minimal MCP gateway และตรวจ capability ของทั้งสาม host

**Stage:** PoC

**Files:**
- Create: src/project_builder/transport/mcp_server.py, src/project_builder/transport/dispatcher.py
- Create: adapters/codex/adapter.json, adapters/claude-code/adapter.json, adapters/devin/adapter.json
- Create: skills/project-builder/SKILL.md, scripts/probe_host.py, src/project_builder/transport/models.py
- Test: tests/transport/test_gateway.py, tests/conformance/test_host_contract.py

**Interfaces:**
- Produces: create_server(dispatcher: Dispatcher) -> MCPServer; Dispatcher.dispatch(request: CommandEnvelope, context: HostContext) -> CommandResult
- Produces: HostTarget(host: Literal['codex','claude-code','devin'], surface: Literal['cli','desktop'], os: Literal['windows','macos']); probe_host(target: HostTarget) -> HostProbeReport
- HostContext มี observed capabilities และ approval event binding ที่ host ให้จริง ไม่เชื่อ claimed user identity จาก model args

- [ ] **Step 1: เขียน failing tests ใน tests/transport/test_gateway.py, tests/conformance/test_host_contract.py** — ประกาศ fixtures ของ task ใน test/conftest เดียวกัน พร้อม assertions ต่อไปนี้และกรณีเพิ่มเติมที่ระบุ

~~~python
def test_malformed_tool_arguments_never_reach_dispatcher(server, spy):
    result = call_tool(server, {"intent": "status", "approved": True})
    assert result.is_error and spy.calls == []
def test_duplicate_status_does_not_spawn_children(server, supervisor_spy):
    call_status_twice(server)
    assert supervisor_spy.start_calls == 0
def test_transport_requires_observed_capabilities(host_probe):
    assert host_probe.with_no_fresh_context().fresh_review_supported is False
~~~

- [ ] **Step 2: รัน RED**

Run: uv run --frozen --python 3.14.4 pytest tests/transport tests/conformance/test_host_contract.py -q  
Expected: FAIL เพราะ interface/behavior ที่ task นี้รับผิดชอบยังไม่มี; ไม่ถือ import/dependency failure ที่ไม่เกี่ยวข้องเป็นหลักฐาน RED

- [ ] **Step 3: Implement interfaces ในไฟล์เจ้าของ task**

ใช้ official MCP SDK 2.3.0 MCPServer กับ stdio; validate อีกครั้งที่ Dispatcher แม้ SDK advertise schema แล้ว; logs อยู่ stderr; PoC เปิดเฉพาะ doctor/status/init-preflight ที่ทำได้จริง ส่วน intent อื่นตอบ NOT_IMPLEMENTED อย่างชัดเจน

- ตรวจ SDK negotiation ทั้ง legacy/current clients ใน fixtures แล้วทดลองจริงครบ 12 host/surface/OS พร้อม version และข้อจำกัด ไม่ใช้ mocked probes เป็นผลรับรอง native host
- ตรวจวิธีอนุมัติ contract จากผู้ใช้จริงของ host; ไม่รับ model-generated approved=true ถ้าไม่มีเส้นทางรับคำตอบที่ตรวจแหล่งได้ให้คง NOT_READY และบันทึก prerequisite
- Codex ใช้ skill picker/mention ตามที่รองรับ; Claude/Devin ใช้ namespace เมื่อทดสอบแล้ว; ยังไม่อ้างว่าทั้ง 12 คู่ใช้ literal slash string เดียวกัน

- [ ] **Step 4: รัน GREEN และตรวจผลส่งมอบ**

Run: uv run --frozen --python 3.14.4 pytest tests/transport tests/conformance/test_host_contract.py -q  
Expected: PASS ทุก test ที่เลือกบน environment ที่ระบุ พร้อมตรวจ receipts/artifacts ตาม task; native/human checks ที่ยังไม่ทำต้องแสดง WAITING/UNVERIFIED ห้ามแทนด้วย unit-test PASS

- [ ] **Step 5: Commit บน feature branch ของ task เท่านั้น**

ตรวจ diff เฉพาะไฟล์ task และ evidence ที่แชร์ได้ แล้วใช้ git add กับรายการไฟล์ที่ระบุชัด (ไม่ git add . ที่อาจเก็บข้อมูลผู้ทดลอง/secrets)  
Commit: git commit -m "feat: expose guarded MCP intents and host capability probes"  
หลัง review ผ่านจึงรวมกลับ active Stage ตาม procedure; commit ไม่ใช่หลักฐานว่า Stage ผ่านแล้ว


### Task 6: ปิด PoC ด้วยหลักฐาน คู่มือ local และคนทดลองจริง

**Stage:** PoC

**Files:**
- Create: src/project_builder/quality/poc_gate.py, docs/user-guides/pb-v0-1/poc.md, docs/verification/poc-capabilities.json
- Create: docs/feedback/pb-v0-1/poc-summary.md, docs/acceptance/poc-matrix.json
- Create: src/project_builder/quality/poc_gate.py
- Test: tests/acceptance/test_poc_evidence.py

**Interfaces:**
- Consumes: HostProbeReport, EnforcementReport, CleanupReceipt และ RunSnapshot จาก Tasks 2–5
- Produces: PoCDecision(status: Literal['GO','NO_GO','WAITING_FOR_HUMAN'], evidence_ids, unresolved_capabilities, recommended_next_stage)
- ไม่ส่งคำเชิญหรือจัดหาคนแทนผู้ใช้; raw personal feedback อยู่ local ส่วน summary ที่แชร์ได้อยู่ docs

- [ ] **Step 1: เขียน failing tests ใน tests/acceptance/test_poc_evidence.py** — ประกาศ fixtures ของ task ใน test/conftest เดียวกัน พร้อม assertions ต่อไปนี้และกรณีเพิ่มเติมที่ระบุ

~~~python
def test_poc_needs_native_evidence_and_real_participants(poc_records):
    assert evaluate_poc(poc_records.with_missing_macos()).status == "NO_GO"
    assert evaluate_poc(poc_records.with_participant_count(1)).status == "WAITING_FOR_HUMAN"
    assert evaluate_poc(poc_records.with_synthetic_feedback()).status != "GO"
~~~

- [ ] **Step 2: รัน RED**

Run: uv run --frozen --python 3.14.4 pytest tests/acceptance/test_poc_evidence.py -q  
Expected: FAIL เพราะ interface/behavior ที่ task นี้รับผิดชอบยังไม่มี; ไม่ถือ import/dependency failure ที่ไม่เกี่ยวข้องเป็นหลักฐาน RED

- [ ] **Step 3: Implement interfaces ในไฟล์เจ้าของ task**

เพิ่ม src/project_builder/quality/poc_gate.py: evaluate_poc(records: PoCRecords) -> PoCDecision; กำหนด GO เฉพาะ proof ของ authority/resource/host invocation ที่จำเป็นครบ มีคู่มือที่ทดลองตามได้ และ feedback คนจริง 2–3 คน

- ส่งให้ผู้ทดลองที่ไม่มีบริบทและไม่รู้จักกันลอง doctor/status/init-preflight ตามคู่มือ; บันทึกสิ่งที่ยังเป็น PoC ไม่อ้างว่าเริ่มพัฒนาโปรเจ็กต์ลูกค้าได้ครบแล้ว
- ก่อน GO ตรวจ setup/cleanup บน Windows/macOS จริง; ถ้ายังไม่มี Mac หรือ host/license ที่จำเป็น ให้ระบุ WAITING/NO_GO และไม่ปลอมผลรับรอง
- เมื่อปิด PoC จึงรวม Stage เข้า develop ตามอำนาจที่ตกลงและคง Stage branch; ตัดสินใจต่อ MVP จากหลักฐาน ไม่เดินหน้าฝืนข้อพิสูจน์ที่ล้มเหลว

- [ ] **Step 4: รัน GREEN และตรวจผลส่งมอบ**

Run: uv run --frozen --python 3.14.4 pytest tests/acceptance/test_poc_evidence.py -q  
Expected: PASS ทุก test ที่เลือกบน environment ที่ระบุ พร้อมตรวจ receipts/artifacts ตาม task; native/human checks ที่ยังไม่ทำต้องแสดง WAITING/UNVERIFIED ห้ามแทนด้วย unit-test PASS

- [ ] **Step 5: Commit บน feature branch ของ task เท่านั้น**

ตรวจ diff เฉพาะไฟล์ task และ evidence ที่แชร์ได้ แล้วใช้ git add กับรายการไฟล์ที่ระบุชัด (ไม่ git add . ที่อาจเก็บข้อมูลผู้ทดลอง/secrets)  
Commit: git commit -m "docs: record PoC gates local guide and independent user feedback"  
หลัง review ผ่านจึงรวมกลับ active Stage ตาม procedure; commit ไม่ใช่หลักฐานว่า Stage ผ่านแล้ว


### Task 7: Environment discovery และ runtime isolation

**Stage:** MVP

**Files:**
- Create: src/project_builder/environment/models.py, src/project_builder/environment/discovery.py
- Create: src/project_builder/environment/planner.py, src/project_builder/environment/recipes.py
- Test: tests/environment/test_discovery.py, tests/environment/test_isolation.py, tests/fixtures/runtime-pins/

**Interfaces:**
- Produces: discover_runtime(root: Path) -> RuntimeInventory; plan_runtime(inventory: RuntimeInventory, authority: StageContract) -> RuntimePlan
- Produces: materialize(plan: RuntimePlan, supervisor: Supervisor) -> EnvironmentReceipt
- RuntimePlan(status: Literal['READY','NEEDS_INPUT','REBUILD_REQUIRED'], runtime_constraint, resolved_executable, lock_digest, os, architecture, owned_env_path, approved_setup_actions, manual_steps, fingerprint)

- [ ] **Step 1: เขียน failing tests ใน tests/environment/test_discovery.py, tests/environment/test_isolation.py, tests/fixtures/runtime-pins/** — ประกาศ fixtures ของ task ใน test/conftest เดียวกัน พร้อม assertions ต่อไปนี้และกรณีเพิ่มเติมที่ระบุ

~~~python
def test_conflicting_pins_are_not_silently_upgraded(conflicting_repo):
    assert plan_runtime(discover_runtime(conflicting_repo), contract()).status == "NEEDS_INPUT"
def test_project_setup_preserves_global_environment(runtime_harness):
    before = runtime_harness.global_snapshot()
    runtime_harness.prepare_project("3.10.13")
    assert runtime_harness.global_snapshot() == before
def test_stale_venv_cannot_be_reused(runtime_harness):
    assert runtime_harness.reuse_with_different_lock().status == "REBUILD_REQUIRED"
~~~

- [ ] **Step 2: รัน RED**

Run: uv run --frozen --python 3.14.4 pytest tests/environment -q  
Expected: FAIL เพราะ interface/behavior ที่ task นี้รับผิดชอบยังไม่มี; ไม่ถือ import/dependency failure ที่ไม่เกี่ยวข้องเป็นหลักฐาน RED

- [ ] **Step 3: Implement interfaces ในไฟล์เจ้าของ task**

อ่าน pyproject/lock/.python-version/CI โดยใช้ safe parsers; เลือก existing exact interpreter ก่อน, สร้าง venv ด้วย path ชัด; project setup ผ่าน supervisor; core environment ไม่ถูกนำไปใช้แทนของลูกค้า

- ครอบคลุม macOS pyenv และ Windows pyenv-win แบบ discovery/manual recipe ไม่บังคับ install manager หรือแก้ profile/PATH/global version; การติดตั้ง prerequisites ระดับบัญชี/เครื่องต้องมี setup agreement เฉพาะ
- ทดสอบ path ภาษาไทย/ช่องว่าง, architecture mismatch, permission-denied, unavailable pinned version, system/user-owned env และ env ที่ไม่มี ownership marker
- สร้างคู่มือทีละขั้นทั้ง OS พร้อม expected output/rollback; project toolchain ที่เก็บไว้กับ scratch env ต้องมี lifecycle ต่างกัน

- [ ] **Step 4: รัน GREEN และตรวจผลส่งมอบ**

Run: uv run --frozen --python 3.14.4 pytest tests/environment -q  
Expected: PASS ทุก test ที่เลือกบน environment ที่ระบุ พร้อมตรวจ receipts/artifacts ตาม task; native/human checks ที่ยังไม่ทำต้องแสดง WAITING/UNVERIFIED ห้ามแทนด้วย unit-test PASS

- [ ] **Step 5: Commit บน feature branch ของ task เท่านั้น**

ตรวจ diff เฉพาะไฟล์ task และ evidence ที่แชร์ได้ แล้วใช้ git add กับรายการไฟล์ที่ระบุชัด (ไม่ git add . ที่อาจเก็บข้อมูลผู้ทดลอง/secrets)  
Commit: git commit -m "feat: isolate project runtimes and generate safe setup recipes"  
หลัง review ผ่านจึงรวมกลับ active Stage ตาม procedure; commit ไม่ใช่หลักฐานว่า Stage ผ่านแล้ว


### Task 8: Intake, baseline trial และ kickoff จากธุรกิจถึงเทคนิค

**Stage:** MVP

**Files:**
- Create: src/project_builder/workflow/intake.py, src/project_builder/workflow/kickoff.py
- Create: src/project_builder/workflow/requirements.py, templates/business-brief.md, templates/stage-contract.json
- Test: tests/workflow/test_intake.py, tests/workflow/test_kickoff.py

**Interfaces:**
- Produces: classify_intake(evidence: RepositoryEvidence) -> IntakeAssessment; requirement_gaps(brief: BusinessBrief, inventory: FeatureInventory) -> list[DiscoveryQuestion]
- Produces: evaluate_kickoff(package: KickoffPackage, approval: ApprovalReceipt | None) -> GateResult
- KickoffPackage(business_brief, requirements, acceptance, ux, technical_design, runtime_plan, team_plan, authority, resource_budget, matrix, human_test_window)

- [ ] **Step 1: เขียน failing tests ใน tests/workflow/test_intake.py, tests/workflow/test_kickoff.py** — ประกาศ fixtures ของ task ใน test/conftest เดียวกัน พร้อม assertions ต่อไปนี้และกรณีเพิ่มเติมที่ระบุ

~~~python
def test_takeover_requires_baseline_human_observations(existing_project):
    assert classify_intake(existing_project).next_step == "BASELINE_FEEDBACK"
def test_unknown_business_acceptance_blocks_ready(package):
    assert evaluate_kickoff(package.with_unresolved_acceptance(), approval()).status == "FAIL"
def test_model_assumption_is_not_confirmed_requirement(requirements):
    assert requirements.from_assumption().status == "assumed"
~~~

- [ ] **Step 2: รัน RED**

Run: uv run --frozen --python 3.14.4 pytest tests/workflow/test_intake.py tests/workflow/test_kickoff.py -q  
Expected: FAIL เพราะ interface/behavior ที่ task นี้รับผิดชอบยังไม่มี; ไม่ถือ import/dependency failure ที่ไม่เกี่ยวข้องเป็นหลักฐาน RED

- [ ] **Step 3: Implement interfaces ในไฟล์เจ้าของ task**

แยก new/takeover/new-version; discovery ถามจากหลักฐานและตัวอย่างจริง; สร้าง short discovery access agreement ก่อน baseline trial ของงานเดิม; kickoff ตรวจ business-to-technical traceability และคำตอบที่เปลี่ยน scope/authority

- Observation ID จากผู้ใช้จริงเชื่อม Requirement ID และ acceptance; setup ล้มเหลวเป็น observed baseline ได้แต่ไม่แทน UX ของหน้าที่เข้าไม่ถึง
- ไม่ถามซ้ำเรื่องที่ repo/คำตอบเดิมตอบแล้ว และไม่ READY ด้วยคำกว้างอย่างเร็ว/ง่ายโดยไม่มีเงื่อนไขตรวจรับ
- review documents และ approval digest ต้องตรง revision ปัจจุบัน; การเปลี่ยน requirement หลัง review ทำให้ approval เดิม stale

- [ ] **Step 4: รัน GREEN และตรวจผลส่งมอบ**

Run: uv run --frozen --python 3.14.4 pytest tests/workflow/test_intake.py tests/workflow/test_kickoff.py -q  
Expected: PASS ทุก test ที่เลือกบน environment ที่ระบุ พร้อมตรวจ receipts/artifacts ตาม task; native/human checks ที่ยังไม่ทำต้องแสดง WAITING/UNVERIFIED ห้ามแทนด้วย unit-test PASS

- [ ] **Step 5: Commit บน feature branch ของ task เท่านั้น**

ตรวจ diff เฉพาะไฟล์ task และ evidence ที่แชร์ได้ แล้วใช้ git add กับรายการไฟล์ที่ระบุชัด (ไม่ git add . ที่อาจเก็บข้อมูลผู้ทดลอง/secrets)  
Commit: git commit -m "feat: collect evidence-backed requirements and enforce kickoff readiness"  
หลัง review ผ่านจึงรวมกลับ active Stage ตาม procedure; commit ไม่ใช่หลักฐานว่า Stage ผ่านแล้ว


### Task 9: Stage assessor และวงจรงาน Agile ที่เลือก Stage น้อย

**Stage:** MVP

**Files:**
- Create: src/project_builder/workflow/stages.py, src/project_builder/workflow/transitions.py
- Create: src/project_builder/workflow/backlog.py
- Test: tests/workflow/test_stage_selection.py, tests/workflow/test_transitions.py

**Interfaces:**
- Produces: select_stages(requirements: RequirementSet, evidence: FeatureEvidenceSet, target: Stage) -> StagePath
- Produces: transition(snapshot: RunSnapshot, event: WorkflowEvent, evidence: EvidenceIndex) -> RunSnapshot
- Produces: StagePath(stages, included_reasons, skipped_reasons); WorkItem(id, requirement_ids, acceptance, owner, reviewer, dependencies, status)

- [ ] **Step 1: เขียน failing tests ใน tests/workflow/test_stage_selection.py, tests/workflow/test_transitions.py** — ประกาศ fixtures ของ task ใน test/conftest เดียวกัน พร้อม assertions ต่อไปนี้และกรณีเพิ่มเติมที่ระบุ

~~~python
def test_ready_existing_feature_can_go_directly_to_final(evidence):
    assert select_stages(requirements(), evidence.verified(), "final").stages == ["final"]
def test_technical_uncertainty_adds_only_needed_poc(evidence):
    assert select_stages(requirements(), evidence.with_uncertainty(), "mvp").stages == ["poc", "mvp"]
def test_development_complete_is_not_stage_completed(snapshot):
    assert transition(snapshot, dev_done(), evidence()).status == "DEVELOPMENT_COMPLETE"
~~~

- [ ] **Step 2: รัน RED**

Run: uv run --frozen --python 3.14.4 pytest tests/workflow/test_stage_selection.py tests/workflow/test_transitions.py -q  
Expected: FAIL เพราะ interface/behavior ที่ task นี้รับผิดชอบยังไม่มี; ไม่ถือ import/dependency failure ที่ไม่เกี่ยวข้องเป็นหลักฐาน RED

- [ ] **Step 3: Implement interfaces ในไฟล์เจ้าของ task**

ใช้ deterministic evidence rules สำหรับ inclusion/skipping แล้วให้ model อธิบายเหตุผล; ไม่ใช้ model score อย่างเดียวเป็นตัวข้าม gate; state transitions ตรวจ kickoff, QA ตาม Stage, guide, human feedback และ cleanup

- UNKNOWN feature ไม่เท่ากับ verified; การข้าม Beta ไม่ข้าม human feedback ของ Stage ที่ทำจริง
- ทุก backlog/work item มี Definition of Ready/Done และ dependency guards; sprint ไม่สร้าง maturity Stage ใหม่
- ห้ามปิด Stage ขณะรอ feedback/cleanup และห้ามใช้ acceptance ที่เปลี่ยนแล้วกับผลทดสอบ revision เก่า

- [ ] **Step 4: รัน GREEN และตรวจผลส่งมอบ**

Run: uv run --frozen --python 3.14.4 pytest tests/workflow/test_stage_selection.py tests/workflow/test_transitions.py -q  
Expected: PASS ทุก test ที่เลือกบน environment ที่ระบุ พร้อมตรวจ receipts/artifacts ตาม task; native/human checks ที่ยังไม่ทำต้องแสดง WAITING/UNVERIFIED ห้ามแทนด้วย unit-test PASS

- [ ] **Step 5: Commit บน feature branch ของ task เท่านั้น**

ตรวจ diff เฉพาะไฟล์ task และ evidence ที่แชร์ได้ แล้วใช้ git add กับรายการไฟล์ที่ระบุชัด (ไม่ git add . ที่อาจเก็บข้อมูลผู้ทดลอง/secrets)  
Commit: git commit -m "feat: select minimal stage paths and enforce delivery transitions"  
หลัง review ผ่านจึงรวมกลับ active Stage ตาม procedure; commit ไม่ใช่หลักฐานว่า Stage ผ่านแล้ว


### Task 10: ทีมตามขนาดงาน, Development Lead และ fresh reviews

**Stage:** MVP

**Files:**
- Create: src/project_builder/team/planner.py, src/project_builder/team/assignments.py
- Create: roles/ba.md, roles/pm.md, roles/sa.md, roles/development-lead.md, roles/backend.md, roles/frontend.md
- Create: roles/data-engineer.md, roles/ai-engineer.md, roles/qa.md, roles/ux-ui.md, roles/devsecops.md, roles/fresh-reviewer.md
- Test: tests/team/test_planner.py, tests/team/test_assignments.py

**Interfaces:**
- Produces: plan_team(scope: ScopeProfile, risks: RiskProfile, capabilities: HostProbeReport, budget: TeamBudget) -> TeamPlan
- Produces: claim_work(work_item: WorkItem, run: RunIdentity, worker_id: str) -> WorkAssignment; report_work(assignment: WorkAssignment, result: WorkResult) -> WorkReceipt
- WorkAssignment ผูก contract revision, allowed files/tools, inputs/outputs, owner/reviewer และ resource lease

- [ ] **Step 1: เขียน failing tests ใน tests/team/test_planner.py, tests/team/test_assignments.py** — ประกาศ fixtures ของ task ใน test/conftest เดียวกัน พร้อม assertions ต่อไปนี้และกรณีเพิ่มเติมที่ระบุ

~~~python
def test_mini_project_does_not_spawn_full_role_catalog():
    plan = plan_team(mini_scope(), low_risk(), capable_host(), budget())
    assert plan.max_active_specialists == 1
    assert "ai-engineer" not in plan.selected_roles
def test_final_qa_cannot_self_review_without_disclosed_limitation():
    assert final_review(author="a", reviewer="a").status != "PASS"
def test_stale_worker_cannot_report_success_after_rebaseline(assignments):
    assert assignments.report_old_revision().status == "STALE_ASSIGNMENT"
~~~

- [ ] **Step 2: รัน RED**

Run: uv run --frozen --python 3.14.4 pytest tests/team -q  
Expected: FAIL เพราะ interface/behavior ที่ task นี้รับผิดชอบยังไม่มี; ไม่ถือ import/dependency failure ที่ไม่เกี่ยวข้องเป็นหลักฐาน RED

- [ ] **Step 3: Implement interfaces ในไฟล์เจ้าของ task**

โหลด role prompts เมื่อเลือกจริง; coordinator รวมหน้าที่วางแผนได้ แต่ DL คือ Development Lead; delegation ใช้ host-native capability ที่ probe แล้ว ไม่เพิ่ม API key หรือเรียก LLM ภายนอกเอง

- Fresh reviewer ได้ artifact/references เท่านั้น และต้องประกาศ UNVERIFIED ถ้า host แยก context ไม่ได้; ไม่จำลอง reviewer ใน session ผู้เขียน
- ค่าเริ่มต้น 1 specialist/1 heavy job; ทีมที่มากขึ้นต้องมีงานอิสระและ budget; จำนวน role metadata ไม่เท่าจำนวน agent ที่เปิด
- ผลตอบของ subagent เป็นข้อเสนอ ต้องตรวจ evidence และ revision ก่อนปิด work item

- [ ] **Step 4: รัน GREEN และตรวจผลส่งมอบ**

Run: uv run --frozen --python 3.14.4 pytest tests/team -q  
Expected: PASS ทุก test ที่เลือกบน environment ที่ระบุ พร้อมตรวจ receipts/artifacts ตาม task; native/human checks ที่ยังไม่ทำต้องแสดง WAITING/UNVERIFIED ห้ามแทนด้วย unit-test PASS

- [ ] **Step 5: Commit บน feature branch ของ task เท่านั้น**

ตรวจ diff เฉพาะไฟล์ task และ evidence ที่แชร์ได้ แล้วใช้ git add กับรายการไฟล์ที่ระบุชัด (ไม่ git add . ที่อาจเก็บข้อมูลผู้ทดลอง/secrets)  
Commit: git commit -m "feat: plan lean specialist teams and isolate required reviews"  
หลัง review ผ่านจึงรวมกลับ active Stage ตาม procedure; commit ไม่ใช่หลักฐานว่า Stage ผ่านแล้ว


### Task 11: Command router, pause/cancel และ Stage-level change backlog

**Stage:** MVP

**Files:**
- Modify: src/project_builder/transport/dispatcher.py, src/project_builder/cli.py
- Create: src/project_builder/commands/router.py, src/project_builder/commands/render.py, src/project_builder/changes/service.py
- Test: tests/commands/test_commands.py, tests/changes/test_queue.py

**Interfaces:**
- Produces: route(envelope: CommandEnvelope, context: HostContext, services: Services) -> CommandResult
- Produces: queue_change(run: RunIdentity, proposal: ChangeProposal) -> ChangeItem; review_stage_changes(run: RunIdentity) -> ChangeReviewPacket
- Produces: pause_run(run: RunIdentity) -> RunSnapshot; cancel_run(run: RunIdentity) -> RunSnapshot; rebaseline(run: RunIdentity, contract: StageContract, approval: ApprovalReceipt) -> RunSnapshot

- [ ] **Step 1: เขียน failing tests ใน tests/commands/test_commands.py, tests/changes/test_queue.py** — ประกาศ fixtures ของ task ใน test/conftest เดียวกัน พร้อม assertions ต่อไปนี้และกรณีเพิ่มเติมที่ระบุ

~~~python
def test_nonurgent_change_does_not_modify_active_contract(service, running_run):
    digest = service.contract_digest(running_run)
    item = service.queue_change(running_run, idea())
    assert item.status == "queued"
    assert service.contract_digest(running_run) == digest
def test_explicit_stop_is_not_queued_until_stage_end(service, running_run):
    assert service.route(stop_request(running_run)).status == "PAUSED"
def test_duplicate_start_does_not_create_second_run(service):
    assert service.start_twice_same_request().created_runs == 1
~~~

- [ ] **Step 2: รัน RED**

Run: uv run --frozen --python 3.14.4 pytest tests/commands tests/changes -q  
Expected: FAIL เพราะ interface/behavior ที่ task นี้รับผิดชอบยังไม่มี; ไม่ถือ import/dependency failure ที่ไม่เกี่ยวข้องเป็นหลักฐาน RED

- [ ] **Step 3: Implement interfaces ในไฟล์เจ้าของ task**

รองรับ main intents init/start/continue/status และ secondary help/doctor/guide/change/backlog/feedback/pause/cancel/cleanup; stop alias pause; ภาษาธรรมดาใช้ intent schema เดียว; status/help read-only

- เก็บ change ทันทีแต่ทวนหลัง COMPLETED ของ Stage เดิม; ระหว่าง WAITING_FOR_HUMAN ก็ยังไม่แทรก scope ใหม่
- urgent rebaseline และ explicit cancellation invalidate worker leases/approvals/evidence ที่ได้รับผลก่อนเดินต่อ; ถ้าข้อความกำกวมเฉพาะการหยุดให้ถามผลที่ต้องการก่อน mutation
- คำตอบผิด run, delayed confirmation, simultaneous continue และ cancel ต้องตรวจ correlation/revision; ไม่ถือ transcript จาก repo เป็นคำสั่งผู้ใช้

- [ ] **Step 4: รัน GREEN และตรวจผลส่งมอบ**

Run: uv run --frozen --python 3.14.4 pytest tests/commands tests/changes -q  
Expected: PASS ทุก test ที่เลือกบน environment ที่ระบุ พร้อมตรวจ receipts/artifacts ตาม task; native/human checks ที่ยังไม่ทำต้องแสดง WAITING/UNVERIFIED ห้ามแทนด้วย unit-test PASS

- [ ] **Step 5: Commit บน feature branch ของ task เท่านั้น**

ตรวจ diff เฉพาะไฟล์ task และ evidence ที่แชร์ได้ แล้วใช้ git add กับรายการไฟล์ที่ระบุชัด (ไม่ git add . ที่อาจเก็บข้อมูลผู้ทดลอง/secrets)  
Commit: git commit -m "feat: route simple commands and queue changes until stage completion"  
หลัง review ผ่านจึงรวมกลับ active Stage ตาม procedure; commit ไม่ใช่หลักฐานว่า Stage ผ่านแล้ว


### Task 12: Git lifecycle แบบ develop → Stage → feature และ PR สูงสุด staging

**Stage:** MVP

**Files:**
- Create: src/project_builder/git/refs.py, src/project_builder/git/workflow.py, src/project_builder/git/github_actions.py, src/project_builder/git/models.py
- Test: tests/git/test_routes.py, tests/git/test_receipts.py, tests/git/test_feature_cleanup.py

**Interfaces:**
- Produces: bootstrap_refs(repo: RepositoryRef, baseline_sha: str, grant: ApprovalReceipt) -> list[GitReceipt]
- Produces: create_stage(repo: RepositoryRef, scope_id: str, stage: Stage, base_sha: str) -> GitReceipt; create_feature(stage_ref: str, work_item_id: str) -> GitReceipt
- Produces: integrate_feature(source: str, stage_ref: str, evidence: WorkReceipt) -> GitReceipt; integrate_stage(stage_ref: str, evidence: StageReport) -> GitReceipt
- Produces: prepare_staging_pr(repo: RepositoryRef, report: StageReport) -> PRPlan; open_staging_pr(plan: PRPlan, proof: EnforcementReport) -> GitReceipt

- [ ] **Step 1: เขียน failing tests ใน tests/git/test_routes.py, tests/git/test_receipts.py, tests/git/test_feature_cleanup.py** — ประกาศ fixtures ของ task ใน test/conftest เดียวกัน พร้อม assertions ต่อไปนี้และกรณีเพิ่มเติมที่ระบุ

~~~python
def test_feature_must_start_at_active_stage(git_fixture):
    assert git_fixture.create_feature_from("develop").status == "DENIED"
def test_squash_receipt_and_new_commits_control_branch_deletion(git_fixture):
    assert git_fixture.feature_with_new_unmerged_commit().can_delete is False
def test_unknown_pr_response_is_reconciled_before_retry(github_fake):
    assert github_fake.timeout_then_retry_same_operation().created_pr_count == 1
def test_target_is_always_staging_and_auto_merge_disabled(github_fake):
    assert github_fake.last_pr.base == "staging"
    assert github_fake.last_pr.auto_merge_enabled is False
def test_forbidden_remote_write_never_reaches_provider(git_service, github_fake):
    before = list(github_fake.mutations)
    result = git_service.request_forbidden_staging_merge()
    assert result.status == "DENIED"
    assert github_fake.mutations == before
~~~

- [ ] **Step 2: รัน RED**

Run: uv run --frozen --python 3.14.4 pytest tests/git -q  
Expected: FAIL เพราะ interface/behavior ที่ task นี้รับผิดชอบยังไม่มี; ไม่ถือ import/dependency failure ที่ไม่เกี่ยวข้องเป็นหลักฐาน RED

- [ ] **Step 3: Implement interfaces ในไฟล์เจ้าของ task**

ใช้ subprocess argv สำหรับ Git และ HTTPX สำหรับ GitHub; mutation ทุกตัวผ่าน Task 3 authorize และ Task 2 operation receipt; inspect/fetch refs ใหม่ก่อนตัดสินใจ; source/target/commit pins ผูก evidence

- ไม่ reset branch ที่มี ไม่แก้ dirty user worktree ไม่ force push/delete Stage branches; branch names ใช้ git check-ref-format และ scope IDs ที่ sanitize แล้ว
- เปิด PR เข้า staging จาก develop เฉพาะ Final report/feedback ที่ตรงกับ build ปัจจุบัน; develop มีงานอื่นที่ยังไม่ตรวจให้ขอ scope decision ไม่ส่งปน
- ก่อนลบ feature ตรวจ owner, merge/squash receipt และ head ว่าไม่เปลี่ยนหลังรวม; cleanup worktree ไม่ลบไฟล์ untracked ของผู้ใช้

- [ ] **Step 4: รัน GREEN และตรวจผลส่งมอบ**

Run: uv run --frozen --python 3.14.4 pytest tests/git -q  
Expected: PASS ทุก test ที่เลือกบน environment ที่ระบุ พร้อมตรวจ receipts/artifacts ตาม task; native/human checks ที่ยังไม่ทำต้องแสดง WAITING/UNVERIFIED ห้ามแทนด้วย unit-test PASS

- [ ] **Step 5: Commit บน feature branch ของ task เท่านั้น**

ตรวจ diff เฉพาะไฟล์ task และ evidence ที่แชร์ได้ แล้วใช้ git add กับรายการไฟล์ที่ระบุชัด (ไม่ git add . ที่อาจเก็บข้อมูลผู้ทดลอง/secrets)  
Commit: git commit -m "feat: enforce stage branch integration and safe feature retirement"  
หลัง review ผ่านจึงรวมกลับ active Stage ตาม procedure; commit ไม่ใช่หลักฐานว่า Stage ผ่านแล้ว


### Task 13: Test matrix, evidence provenance และ Final gate แบบ >95%

**Stage:** MVP

**Files:**
- Create: src/project_builder/quality/models.py, src/project_builder/quality/matrix.py, src/project_builder/quality/final_gate.py
- Create: src/project_builder/quality/parsers.py
- Test: tests/quality/test_final_gate.py, tests/quality/test_provenance.py

**Interfaces:**
- Produces: evaluate_final(matrix: TestMatrix, results: TestRunEvidence, defects: list[Defect], build: BuildIdentity) -> GateResult
- Produces: ingest_test_result(source: Path, producer: ResourceHandle, expected_build: BuildIdentity) -> TestRunEvidence
- Produces: score_matrix(matrix: TestMatrix, results: TestRunEvidence) -> tuple[int,int] ใน quality/matrix.py; คืน passed_unique กับ applicable_total ไม่รวม tag ซ้ำ
- TestMatrix(revision, approved_digest, case_ids, applicability, tags); CaseResult(case_id, status, attempts); Defect(id, severity, status); BuildIdentity(commit_sha, tree_digest, env_fingerprint)

- [ ] **Step 1: เขียน failing tests ใน tests/quality/test_final_gate.py, tests/quality/test_provenance.py** — ประกาศ fixtures ของ task ใน test/conftest เดียวกัน พร้อม assertions ต่อไปนี้และกรณีเพิ่มเติมที่ระบุ

~~~python
def test_strictly_more_than_95_percent():
    assert evaluate_final(matrix(100), results(passed=95), [], build()).status == "FAIL"
    assert evaluate_final(matrix(100), results(passed=96), [], build()).status == "PASS"
def test_high_defect_blocks_even_99_percent():
    assert evaluate_final(matrix(100), results(passed=99), [high_defect()], build()).status == "FAIL"
def test_duplicate_tags_and_not_run_cannot_inflate_ratio():
    assert score_matrix(matrix_with_tagged_cases(), results_with_one_pass_and_one_not_run()) == (1, 2)
def test_zero_or_stale_matrix_is_unverified():
    assert evaluate_final(matrix(0), results(0), [], build()).status == "UNVERIFIED"
def test_forged_or_retry_only_evidence_cannot_pass(quality_harness):
    assert quality_harness.gate_with_forged_producer().status != "PASS"
    assert quality_harness.gate_with_unaccepted_retry_only_passes().status != "PASS"
~~~

- [ ] **Step 2: รัน RED**

Run: uv run --frozen --python 3.14.4 pytest tests/quality -q  
Expected: FAIL เพราะ interface/behavior ที่ task นี้รับผิดชอบยังไม่มี; ไม่ถือ import/dependency failure ที่ไม่เกี่ยวข้องเป็นหลักฐาน RED

- [ ] **Step 3: Implement interfaces ในไฟล์เจ้าของ task**

ตัดสินอัตราด้วย integer comparison 100*passed > 95*applicable_total; zero denominator/stale build ให้ UNVERIFIED; case IDs unique; skipped/blocked/not-run/xfail อยู่ denominator เมื่อ applicable; unknown severity ไม่แอบนับเป็น Low

- test params ครอบคลุม critical/high, missing evidence, fake passed JSON ที่ไม่มี authorized producer receipt, changed acceptance, retry-only pass และ N/A edits หลังรัน
- matrix revision ถูกอนุมัติก่อนรัน; การเพิ่ม/ตัด cases มีเหตุผลและ approval ไม่ลดความครอบคลุมเพื่อคะแนน
- เชื่อม Requirement → Acceptance → Case → Result → Defect และทำ gap report ทุก test category ที่จำเป็น ไม่ใช้จำนวน unit tests แทนความพร้อม UX/security

- [ ] **Step 4: รัน GREEN และตรวจผลส่งมอบ**

Run: uv run --frozen --python 3.14.4 pytest tests/quality -q  
Expected: PASS ทุก test ที่เลือกบน environment ที่ระบุ พร้อมตรวจ receipts/artifacts ตาม task; native/human checks ที่ยังไม่ทำต้องแสดง WAITING/UNVERIFIED ห้ามแทนด้วย unit-test PASS

- [ ] **Step 5: Commit บน feature branch ของ task เท่านั้น**

ตรวจ diff เฉพาะไฟล์ task และ evidence ที่แชร์ได้ แล้วใช้ git add กับรายการไฟล์ที่ระบุชัด (ไม่ git add . ที่อาจเก็บข้อมูลผู้ทดลอง/secrets)  
Commit: git commit -m "feat: verify test provenance and strict Final quality gates"  
หลัง review ผ่านจึงรวมกลับ active Stage ตาม procedure; commit ไม่ใช่หลักฐานว่า Stage ผ่านแล้ว


### Task 14: Tool registry และ Playwright ที่คุม browser/worker/หลักฐาน

**Stage:** MVP

**Files:**
- Create: src/project_builder/tools/registry.py, src/project_builder/tools/playwright.py
- Create: templates/playwright/playwright.config.ts, templates/playwright/example.spec.ts
- Test: tests/tools/test_registry.py, tests/tools/test_playwright.py, tests/fixtures/ui-app/

**Interfaces:**
- Produces: select_tools(scope: ScopeProfile, existing: ToolInventory) -> ToolPlan; run_browser_tests(recipe: BrowserTestRecipe, owner: RunIdentity) -> TestRunEvidence
- BrowserTestRecipe(project_root, config_path, node_executable, runner_entry, workers=1, approved_baseline_digest, output_dir, timeout_seconds)
- ToolSpec(name, version, permissions, install_footprint, cleanup_recipe, evidence_parser)

- [ ] **Step 1: เขียน failing tests ใน tests/tools/test_registry.py, tests/tools/test_playwright.py, tests/fixtures/ui-app/** — ประกาศ fixtures ของ task ใน test/conftest เดียวกัน พร้อม assertions ต่อไปนี้และกรณีเพิ่มเติมที่ระบุ

~~~python
def test_non_ui_project_does_not_install_browsers(tool_selector):
    assert "playwright" not in tool_selector.for_cli_only().install
def test_browser_workers_obey_supervisor_budget(browser_runner):
    assert browser_runner.config.workers == 1
def test_visual_failure_does_not_update_baseline(browser_runner):
    assert "--update-snapshots" not in browser_runner.argv
def test_browser_crash_tears_down_owned_contexts(browser_runner):
    assert browser_runner.run_crashing_fixture().cleanup_verified is True
~~~

- [ ] **Step 2: รัน RED**

Run: uv run --frozen --python 3.14.4 pytest tests/tools -q  
Expected: FAIL เพราะ interface/behavior ที่ task นี้รับผิดชอบยังไม่มี; ไม่ถือ import/dependency failure ที่ไม่เกี่ยวข้องเป็นหลักฐาน RED

- [ ] **Step 3: Implement interfaces ในไฟล์เจ้าของ task**

ใช้ project-local Playwright Test ผ่าน Node executable/runner path ที่ตรวจพบ; ไม่ใช้ browser profile ส่วนตัว; output ผ่าน Task 13 parser กับ supervisor receipt; add-ons เลือกเมื่อจำเป็น

- E2E fixture ต้องทดสอบ functional journey, viewport/keyboard, visual diff และ accessibility adapter ตาม scope; browser automation ไม่แทน usability ของคนจริง
- Node/Playwright versions ของ fixture pin ใน package-lock.json ตอนสร้าง fixture ใช้ stable release ที่ตรวจได้และบันทึก lock digest; ไม่อัปเดต dependencies ของ repo ลูกค้าเพื่อให้ test runner ของเราใช้ได้
- เลือก capture on failure และ trace ตาม test strategy; ไม่เปิด video/ทุก browser/ทุก worker โดยปริยาย; guide ระบุภาพ baseline, environment และวิธีเปิด report ที่ปลอดภัยต่อข้อมูล

- [ ] **Step 4: รัน GREEN และตรวจผลส่งมอบ**

Run: uv run --frozen --python 3.14.4 pytest tests/tools -q  
Expected: PASS ทุก test ที่เลือกบน environment ที่ระบุ พร้อมตรวจ receipts/artifacts ตาม task; native/human checks ที่ยังไม่ทำต้องแสดง WAITING/UNVERIFIED ห้ามแทนด้วย unit-test PASS

- [ ] **Step 5: Commit บน feature branch ของ task เท่านั้น**

ตรวจ diff เฉพาะไฟล์ task และ evidence ที่แชร์ได้ แล้วใช้ git add กับรายการไฟล์ที่ระบุชัด (ไม่ git add . ที่อาจเก็บข้อมูลผู้ทดลอง/secrets)  
Commit: git commit -m "feat: run scoped Playwright checks under resource supervision"  
หลัง review ผ่านจึงรวมกลับ active Stage ตาม procedure; commit ไม่ใช่หลักฐานว่า Stage ผ่านแล้ว


### Task 15: Human feedback, local guides และ Stage handoff

**Stage:** MVP

**Files:**
- Create: src/project_builder/feedback/service.py, src/project_builder/guides/service.py, src/project_builder/workflow/handoff.py
- Create: templates/user-guide.md, templates/participant-task-pack.md, templates/feedback-form.json
- Test: tests/feedback/test_independent_rounds.py, tests/guides/test_local_guide.py, tests/workflow/test_handoff.py

**Interfaces:**
- Produces: register_feedback(run: RunIdentity, batch: FeedbackBatch) -> FeedbackReceipt; triage_feedback(receipt: FeedbackReceipt) -> FeedbackTriage
- Produces: render_guide(contract: StageContract, runtime: RuntimePlan, report: StageReport) -> GuideArtifact; verify_guide(guide: GuideArtifact, owner: RunIdentity) -> GuideVerification
- Produces: build_handoff(run: RunIdentity) -> StageReport; complete_stage(report: StageReport) -> GateResult

- [ ] **Step 1: เขียน failing tests ใน tests/feedback/test_independent_rounds.py, tests/guides/test_local_guide.py, tests/workflow/test_handoff.py** — ประกาศ fixtures ของ task ใน test/conftest เดียวกัน พร้อม assertions ต่อไปนี้และกรณีเพิ่มเติมที่ระบุ

~~~python
def test_stage_needs_two_or_three_real_independent_people(service):
    assert service.complete_with_people(1).status == "WAITING_FOR_HUMAN"
    assert service.complete_with_synthetic_feedback(3).status != "PASS"
def test_guide_is_bound_to_stage_build_and_has_stop_commands(guide):
    assert guide.build_sha == stage_build().commit_sha and guide.stop_steps
def test_waiting_for_people_does_not_keep_preview_running(service):
    assert service.wait_for_feedback().owned_live_workloads == 0
~~~

- [ ] **Step 2: รัน RED**

Run: uv run --frozen --python 3.14.4 pytest tests/feedback tests/guides tests/workflow/test_handoff.py -q  
Expected: FAIL เพราะ interface/behavior ที่ task นี้รับผิดชอบยังไม่มี; ไม่ถือ import/dependency failure ที่ไม่เกี่ยวข้องเป็นหลักฐาน RED

- [ ] **Step 3: Implement interfaces ในไฟล์เจ้าของ task**

เก็บ P1/P2/P3 แยก raw ที่ได้รับอนุญาตกับ shared summary; ไม่สร้างคนหรือ feedback แทนจริง; guide ตรวจ run steps ผ่าน supervisor-owned clean workspace และข้อมูลทดสอบ

- baseline trial ของ takeover/new-version มาก่อน kickoff และหลัง DEVELOPMENT_COMPLETE ต้องมี Stage feedback ทุก Stage; retest flow ที่แก้เมื่อผลเก่าใช้ไม่ได้
- fresh/returning, build/guide/task versions และ assistance ถูกบันทึก; ไม่ส่ง invite/message จนได้คำสั่งเฉพาะ
- High จากคนจริง invalidate Final gate; suggestion ใหม่ไป backlog ไม่ถูกนับเป็น test case โดยอัตโนมัติ; COMPLETED ต้องมี guide/QA/feedback/cleanup ที่จำเป็นครบ

- [ ] **Step 4: รัน GREEN และตรวจผลส่งมอบ**

Run: uv run --frozen --python 3.14.4 pytest tests/feedback tests/guides tests/workflow/test_handoff.py -q  
Expected: PASS ทุก test ที่เลือกบน environment ที่ระบุ พร้อมตรวจ receipts/artifacts ตาม task; native/human checks ที่ยังไม่ทำต้องแสดง WAITING/UNVERIFIED ห้ามแทนด้วย unit-test PASS

- [ ] **Step 5: Commit บน feature branch ของ task เท่านั้น**

ตรวจ diff เฉพาะไฟล์ task และ evidence ที่แชร์ได้ แล้วใช้ git add กับรายการไฟล์ที่ระบุชัด (ไม่ git add . ที่อาจเก็บข้อมูลผู้ทดลอง/secrets)  
Commit: git commit -m "feat: close stages with verified local guides and real user feedback"  
หลัง review ผ่านจึงรวมกลับ active Stage ตาม procedure; commit ไม่ใช่หลักฐานว่า Stage ผ่านแล้ว


### Task 16: แพ็ก shared runtime และสร้าง adapters สำหรับติดตั้งในเครื่อง

**Stage:** MVP

**Files:**
- Create: packaging/project-builder.spec, scripts/build_runtime.py, src/project_builder/packaging/render.py
- Create: adapters/codex/plugin.template.json, adapters/claude-code/plugin.template.json, adapters/devin/plugin.template.json
- Create: adapters/codex/mcp.template.json, adapters/claude-code/mcp.template.json, adapters/devin/mcp.template.json
- Create: scripts/build_plugins.py, templates/install/windows.md, templates/install/macos.md, THIRD_PARTY_NOTICES.md
- Test: tests/packaging/test_packages.py, tests/packaging/test_installation.py

**Interfaces:**
- Produces: build_runtime(target: RuntimeTarget, output: Path) -> RuntimeArtifact; RuntimeTarget(os, architecture, python_version)
- Produces: render_plugin(target: HostTarget, runtime_path: Path, output: Path) -> PluginArtifact
- Produces: verify_artifact(artifact: PluginArtifact) -> ArtifactReport (manifest/schema/references/identity/version/checksums)
- RuntimeArtifact(target, release_version, core_source_digest, runtime_digest, path); PluginArtifact(host_target, runtime_target, release_version, core_source_digest, runtime_digest, path); ไฟล์ binary คนละ OS/architecture มี digest ต่างกันได้

- [ ] **Step 1: เขียน failing tests ใน tests/packaging/test_packages.py, tests/packaging/test_installation.py** — ประกาศ fixtures ของ task ใน test/conftest เดียวกัน พร้อม assertions ต่อไปนี้และกรณีเพิ่มเติมที่ระบุ

~~~python
def test_host_packages_share_core_release_and_target_runtime(packages):
    assert len({(p.release_version, p.core_source_digest) for p in packages}) == 1
    for target in {p.runtime_target for p in packages}:
        same_target = [p for p in packages if p.runtime_target == target]
        assert len({p.runtime_digest for p in same_target}) == 1
def test_install_does_not_modify_global_python_or_path(installer):
    assert installer.after.global_environment == installer.before.global_environment
def test_missing_binary_or_manifest_reference_fails_package_gate(package):
    assert verify_artifact(package.with_missing_runtime()).status == "FAIL"
def test_uninstall_preserves_projects_and_stage_branches(installer):
    assert installer.uninstall().project_files_unchanged is True
~~~

- [ ] **Step 2: รัน RED**

Run: uv run --frozen --python 3.14.4 pytest tests/packaging -q  
Expected: FAIL เพราะ interface/behavior ที่ task นี้รับผิดชอบยังไม่มี; ไม่ถือ import/dependency failure ที่ไม่เกี่ยวข้องเป็นหลักฐาน RED

- [ ] **Step 3: Implement interfaces ในไฟล์เจ้าของ task**

ใช้ PyInstaller 6.22.3 แบบ onedir; build บน OS/architecture จริง; core binary/runtime อยู่ user-local versioned location ร่วมกันเมื่อใช้หลาย host; render host-specific manifest ไปยังพื้นที่ plugin ของเราโดยรักษา config เดิม

- artifact เริ่มต้น Windows x64, macOS arm64/x64; บันทึก OS/architecture/version ที่ทดลองจริงและ reject hardware ที่ยังไม่รับรอง ไม่อ้างว่าทุก Windows/macOS version ผ่านแล้ว
- ใช้ checksums และ release version เดียวกัน; private/repo distribution ไม่ upload/publish/install ให้เพื่อนเอง; ผู้ใช้เลือกและติดตั้งตามคู่มือของ host
- stdio command ต้องชี้ binary ของรุ่นที่ตรวจ ไม่พึ่ง python ใน PATH หรือ cache path ของเครื่องผู้สร้าง; เอกสาร guide ระบุขั้น trust/permissions/doctor/uninstall
- ทำ empty-machine/isolated-user install smoke บน OS จริง; เก็บผล signature/notarization/trust prompts ตามวิธีแจกที่ใช้ ไม่อ้างว่า build Windows รับรอง Mac ได้

- [ ] **Step 4: รัน GREEN และตรวจผลส่งมอบ**

Run: uv run --frozen --python 3.14.4 pytest tests/packaging -q  
Expected: PASS ทุก test ที่เลือกบน environment ที่ระบุ พร้อมตรวจ receipts/artifacts ตาม task; native/human checks ที่ยังไม่ทำต้องแสดง WAITING/UNVERIFIED ห้ามแทนด้วย unit-test PASS

- [ ] **Step 5: Commit บน feature branch ของ task เท่านั้น**

ตรวจ diff เฉพาะไฟล์ task และ evidence ที่แชร์ได้ แล้วใช้ git add กับรายการไฟล์ที่ระบุชัด (ไม่ git add . ที่อาจเก็บข้อมูลผู้ทดลอง/secrets)  
Commit: git commit -m "build: package a shared local runtime with three host adapters"  
หลัง review ผ่านจึงรวมกลับ active Stage ตาม procedure; commit ไม่ใช่หลักฐานว่า Stage ผ่านแล้ว


### Task 17: MVP vertical slice และปิด Stage พร้อม feedback

**Stage:** MVP

**Files:**
- Create: src/project_builder/quality/mvp_gate.py, tests/acceptance/test_mvp_delivery.py, tests/fixtures/new-project/, tests/fixtures/takeover-project/, tests/fixtures/new-version-project/
- Create: docs/user-guides/pb-v0-1/mvp.md, docs/acceptance/mvp-matrix.json, docs/feedback/pb-v0-1/mvp-summary.md
- Create: src/project_builder/quality/mvp_gate.py

**Interfaces:**
- Consumes: CommandResult, RuntimePlan, StagePath, TeamPlan, StageReport และ PluginArtifact ที่สร้างแล้ว
- Produces: MVPDeliveryReport(scenarios, native_host_evidence, guide_verification, human_feedback, unresolved_defects, beta_recommendation)
- เพิ่ม src/project_builder/quality/mvp_gate.py: evaluate_mvp(report: MVPDeliveryReport) -> GateResult

- [ ] **Step 1: เขียน failing tests ใน ** — ประกาศ fixtures ของ task ใน test/conftest เดียวกัน พร้อม assertions ต่อไปนี้และกรณีเพิ่มเติมที่ระบุ

~~~python
def test_new_takeover_and_next_version_finish_scoped_work(end_to_end):
    for scenario in ["new", "takeover", "new-version"]:
        assert end_to_end.run(scenario).stage_status == "COMPLETED"
def test_midstage_idea_survives_resume_without_entering_active_scope(end_to_end):
    report = end_to_end.queue_then_resume()
    assert report.idea_in_backlog and not report.idea_implemented
def test_explicit_stop_and_failed_guide_are_not_reported_complete(end_to_end):
    assert end_to_end.cancel_midway().stage_status == "CANCELLED"
    assert end_to_end.bad_guide().stage_status != "COMPLETED"
~~~

- [ ] **Step 2: รัน RED**

Run: uv run --frozen --python 3.14.4 pytest tests/acceptance/test_mvp_delivery.py -q  
Expected: FAIL เพราะ interface/behavior ที่ task นี้รับผิดชอบยังไม่มี; ไม่ถือ import/dependency failure ที่ไม่เกี่ยวข้องเป็นหลักฐาน RED

- [ ] **Step 3: Implement interfaces ในไฟล์เจ้าของ task**

fixtures ใช้ local fake provider สำหรับ unsafe-negative cases; live path ตรวจผ่าน read-only prerequisites และทำเฉพาะ operations ที่ได้รับอำนาจกับ sandbox repo ที่ระบุชื่อไว้จริง; ไม่ทดลอง forbidden writes บน repo จริง

- MVP ต้องทดลอง installed package ของทั้ง 12 คู่ด้วย scenario set เดียวกัน โดยแยก automated simulator กับ native host evidence; ไม่มีเครื่อง/สิทธิ์ให้ WAITING ไม่ tick ผ่าน
- user guide สำหรับ nontechnical users ระบุ main commands, local setup/stop, state/backlog และ known limitations; คนจริง 2–3 คนทดลองโดยไม่เห็น feedback กัน
- ตัดสินใจ skip Beta เมื่อ scenarios/installation/native behavior และ feedback ที่จำเป็นครบและไม่พบประเด็นต้องทดลองเพิ่ม; บันทึกเหตุผล ถ้าต้อง Beta ให้กำหนด scope เฉพาะช่องว่าง

- [ ] **Step 4: รัน GREEN และตรวจผลส่งมอบ**

Run: uv run --frozen --python 3.14.4 pytest tests/acceptance/test_mvp_delivery.py -q  
Expected: PASS ทุก test ที่เลือกบน environment ที่ระบุ พร้อมตรวจ receipts/artifacts ตาม task; native/human checks ที่ยังไม่ทำต้องแสดง WAITING/UNVERIFIED ห้ามแทนด้วย unit-test PASS

- [ ] **Step 5: Commit บน feature branch ของ task เท่านั้น**

ตรวจ diff เฉพาะไฟล์ task และ evidence ที่แชร์ได้ แล้วใช้ git add กับรายการไฟล์ที่ระบุชัด (ไม่ git add . ที่อาจเก็บข้อมูลผู้ทดลอง/secrets)  
Commit: git commit -m "test: validate the MVP workflow and collect independent user feedback"  
หลัง review ผ่านจึงรวมกลับ active Stage ตาม procedure; commit ไม่ใช่หลักฐานว่า Stage ผ่านแล้ว


### Task 18: ทดลองความเสถียร/การใช้งานเพิ่มเฉพาะเมื่อผล MVP ต้องการ

**Stage:** Beta (conditional)

**Files:**
- Create if selected: src/project_builder/quality/beta_gate.py, tests/acceptance/test_beta_resilience.py, docs/acceptance/beta-matrix.json
- Create if selected: docs/user-guides/pb-v0-1/beta.md, docs/feedback/pb-v0-1/beta-summary.md
- Modify if needed: modules เจ้าของ defect จาก MVP โดยแตก feature จาก active Beta Stage
- Create if selected: src/project_builder/quality/beta_gate.py

**Interfaces:**
- Consumes: MVPDeliveryReport.beta_recommendation พร้อม unresolved gap IDs; ไม่เพิ่ม Beta เพียงเพื่อให้ครบชื่อ
- Produces: BetaDeliveryReport(gap_ids, resilience_results, native_host_records, real_feedback_ids, cleanup_receipts); evaluate_beta(report: BetaDeliveryReport) -> GateResult ใน src/project_builder/quality/beta_gate.py

- [ ] **Step 1: เขียน failing tests ใน ** — ประกาศ fixtures ของ task ใน test/conftest เดียวกัน พร้อม assertions ต่อไปนี้และกรณีเพิ่มเติมที่ระบุ

~~~python
def test_pressure_or_crash_preserves_user_machine_and_checkpoint(beta_harness):
    report = beta_harness.run_selected_failure_case()
    assert report.foreign_resources_untouched
    assert report.resume_is_consistent
    assert report.owned_workloads_remaining == 0
~~~

- [ ] **Step 2: รัน RED**

Run: uv run --frozen --python 3.14.4 pytest tests/acceptance/test_beta_resilience.py -q  
Expected: FAIL เพราะ interface/behavior ที่ task นี้รับผิดชอบยังไม่มี; ไม่ถือ import/dependency failure ที่ไม่เกี่ยวข้องเป็นหลักฐาน RED

- [ ] **Step 3: Implement interfaces ในไฟล์เจ้าของ task**

เลือกเฉพาะ workload/host/UX gaps ที่ MVP พบ; เพิ่ม load/soak/failure cases ตาม scope; ไม่มี Beta ให้บันทึก skipped reason และไม่สร้าง branch/guide ปลอม

- ถ้าเลือก Beta ต้องมี kickoff/Stage branch/คู่มือ local/คนจริง 2–3 คนหลังรอบพัฒนาเหมือน Stage อื่น
- กำหนด duration/resource budget ก่อน soak; ห้ามรันทดสอบความกดดันจนทำให้เครื่องเจ้าของเสียการใช้งาน
- ไม่มีผลด้าน reliability ที่อ้างข้าม OS/host โดยไม่ได้ทดสอบ

- [ ] **Step 4: รัน GREEN และตรวจผลส่งมอบ**

Run: uv run --frozen --python 3.14.4 pytest tests/acceptance/test_beta_resilience.py -q  
Expected: PASS ทุก test ที่เลือกบน environment ที่ระบุ พร้อมตรวจ receipts/artifacts ตาม task; native/human checks ที่ยังไม่ทำต้องแสดง WAITING/UNVERIFIED ห้ามแทนด้วย unit-test PASS

- [ ] **Step 5: Commit บน feature branch ของ task เท่านั้น**

ตรวจ diff เฉพาะไฟล์ task และ evidence ที่แชร์ได้ แล้วใช้ git add กับรายการไฟล์ที่ระบุชัด (ไม่ git add . ที่อาจเก็บข้อมูลผู้ทดลอง/secrets)  
Commit: git commit -m "test: close selected Beta gaps with bounded resilience trials"  
หลัง review ผ่านจึงรวมกลับ active Stage ตาม procedure; commit ไม่ใช่หลักฐานว่า Stage ผ่านแล้ว


### Task 19: Final acceptance, handoff และเปิด PR เข้า staging ตามอำนาจ

**Stage:** Final

**Files:**
- Create: docs/user-guides/pb-v0-1/final.md, docs/acceptance/final-matrix.json, docs/acceptance/host-matrix.json
- Create: docs/feedback/pb-v0-1/final-summary.md, docs/releases/0.1.0-handoff.md
- Modify: README.md โดยตรวจ encoding เดิมก่อนแก้, package/version metadata และ docs/installation/ ที่ออกจาก Task 16
- Create: src/project_builder/quality/release_gate.py
- Create: src/project_builder/quality/release_gate.py
- Test: tests/acceptance/test_final_release.py

**Interfaces:**
- Consumes: StageReport ของ Final, complete native host matrix, verified package digests, quality/guide/feedback/cleanup evidence และ EnforcementReport ที่ยังใช้ได้
- Produces: ReleaseHandoff(version, tested_platforms, evidence_index, known_issues, package_paths, optional_staging_pr_url)
- เพิ่ม src/project_builder/quality/release_gate.py: evaluate_release(report: ReleaseHandoffInput) -> GateResult; ไม่สร้าง deploy/merge capability

- [ ] **Step 1: เขียน failing tests ใน tests/acceptance/test_final_release.py** — ประกาศ fixtures ของ task ใน test/conftest เดียวกัน พร้อม assertions ต่อไปนี้และกรณีเพิ่มเติมที่ระบุ

~~~python
def test_release_requires_real_platform_evidence_and_final_gate(release):
    assert evaluate_release(release.missing_one_native_target()).status != "PASS"
    assert evaluate_release(release.with_pass_rate(95)).status == "FAIL"
    assert evaluate_release(release.with_open_high()).status == "FAIL"
def test_last_action_is_optional_staging_pr_only(release_runner):
    receipt = release_runner.finish_authorized_stage()
    assert receipt.target == "staging" and not receipt.auto_merge
    assert release_runner.calls_after_pr == []
~~~

- [ ] **Step 2: รัน RED**

Run: uv run --frozen --python 3.14.4 pytest tests/acceptance/test_final_release.py -q  
Expected: FAIL เพราะ interface/behavior ที่ task นี้รับผิดชอบยังไม่มี; ไม่ถือ import/dependency failure ที่ไม่เกี่ยวข้องเป็นหลักฐาน RED

- [ ] **Step 3: Implement interfaces ในไฟล์เจ้าของ task**

freeze Final matrix ก่อนรัน; Final >95% และ High+ = 0 ใช้ evidence ของ build ที่จะส่งจริง รวม security/regression/E2E/UX/performance/operations ที่ applicable; issue สูงต้องแก้และ retest ไม่ waiver

- หลัง DEVELOPMENT_COMPLETE เก็บ feedback คนจริง 2–3 คนและแก้สิ่งที่บล็อก Final; verify คู่มือและ cleanup ก่อน COMPLETED
- ตรวจทั้ง Windows/macOS × CLI/Desktop × 3 hosts พร้อม exact versions และ subset hardware ที่รับรอง; ข้อมูล missing ไม่ใช้ simulated tests แทน
- รวม feature → Final Stage → develop ตามอำนาจและ revalidate aggregate build; ถ้าอนุญาตเปิด PR ให้เปิด develop → staging แล้วจบ ไม่ merge/auto-merge/enqueue/main/prod
- ส่ง local artifacts/installation guides/checksums/known issues โดยไม่ publish หรือส่งข้อความให้เพื่อนโดยไม่มีคำสั่ง; ถ้าขาด remote setup ส่ง local handoff พร้อม blocked reason ไม่อ้างว่ารุ่นแรกครบแล้ว

- [ ] **Step 4: รัน GREEN และตรวจผลส่งมอบ**

Run: uv run --frozen --python 3.14.4 pytest tests/acceptance/test_final_release.py -q  
Expected: PASS ทุก test ที่เลือกบน environment ที่ระบุ พร้อมตรวจ receipts/artifacts ตาม task; native/human checks ที่ยังไม่ทำต้องแสดง WAITING/UNVERIFIED ห้ามแทนด้วย unit-test PASS

- [ ] **Step 5: Commit บน feature branch ของ task เท่านั้น**

ตรวจ diff เฉพาะไฟล์ task และ evidence ที่แชร์ได้ แล้วใช้ git add กับรายการไฟล์ที่ระบุชัด (ไม่ git add . ที่อาจเก็บข้อมูลผู้ทดลอง/secrets)  
Commit: git commit -m "release: finalize verified artifacts and hand off at the staging PR ceiling"  
หลัง review ผ่านจึงรวมกลับ active Stage ตาม procedure; commit ไม่ใช่หลักฐานว่า Stage ผ่านแล้ว

## 7. Requirement coverage และเกณฑ์รวมงาน

| Spec | Tasks ที่รับผิดชอบ |
| --- | --- |
| C01 ชื่อ/การแจกใช้กับเพื่อน | T1, T16, T19 |
| C02 Windows/macOS × CLI/Desktop × 3 hosts | T4–T6, T16–T19 |
| C03 shared core/adapters | T1–T5, T16 |
| C04 roles รวม DL/UX/UI/DevSecOps | T10 |
| C05 lean team/resource awareness | T4, T10 |
| C06 new/takeover/new-version | T8, T17 |
| C07 Agile/Scrum/work state | T9 |
| C08 minimal Stage assessment | T9, T17, T18 |
| C09 bootstrap main/staging/develop | T3, T12 และ procedure ข้อ 3 |
| C10 branch route | T12 |
| C11 retained Stage/retired feature | T12 |
| C12 >95% matrix และ C13 High+ = 0 | T13, T19 |
| C14 ceiling PR staging | T3, T5, T12, T19 |
| C15 owned resources/cleanup | T4, T7, T14–T19 |
| C16 Playwright/add-ons | T14 |
| C17 local guides ทุก Stage | T6, T15, T17–T19 |
| C18 business-to-technical kickoff | T8 |
| C19 คนจริง baseline+หลังทุก Stage | T6, T8, T15, T17–T19 |
| C20 EGM inspiration/fresh review | T10 |
| C21 runtime isolation/setup | T7, T16 |
| C22 simple command intents | T1, T5, T11, T16 |
| C23 changes queued until Stage end | T2, T9, T11, T17 |

Spec sections 1–5 → scope/stack/T1–T5; 6–12 → T8–T11; 13–15 → T3/T12; 16–20 → T6/T13–T15/T17–T19; 21–25 → T2/T4/T11; 26–29 → T16–T19; 30–32 → T7/T11; section 33 → sources ที่ใช้ตรวจ API/packaging ในแผนนี้

## 8. Verification commands และหลักฐานที่ต้องส่ง

Development suite หลัง task ของ Stage ที่เกี่ยวข้องพร้อม:
- uv run --frozen --python 3.14.4 pytest tests -q
- uv run --frozen --python 3.14.4 python -m compileall -q src
- uv run --frozen --python 3.14.4 python -m project_builder status --project <approved-fixture-root> --json
- uv run --frozen --python 3.14.4 python scripts/build_runtime.py --target <native-target> --out <owned-build-dir>
- uv run --frozen --python 3.14.4 python scripts/build_plugins.py --host <host> --runtime <verified-runtime-path> --out <owned-package-dir>

scripts/build_runtime.py และ build_plugins.py เป็น thin entry points ให้ signatures ใน T16 ไม่ได้เริ่มใช้งานได้ก่อน task นั้นเสร็จ
Compile/unit tests ไม่แทน native host/resource/human evidence; tests ที่ OS ปัจจุบันทดสอบไม่ได้ต้องอยู่ใน target report เป็น PENDING ไม่ tick ผ่าน Final
ภายใน Task 14/17 ให้รัน Playwright tests ด้วย explicit Node/runner ที่ตรวจพบและ workers=1 ตาม budget ไม่มี generic shell interpolation จาก repo content

ทุก Stage handoff ต้องมี branch/commit, requirement/contract revision, matrix/build/env digests, test results, human feedback summary (raw ที่มีสิทธิ์อยู่ local), local guide verification, ownership/cleanup receipts, known issues และ next-stage decision
Test completion ของ Final ใช้ applicable matrix ของผลิตภัณฑ์จริง ไม่เอาจำนวน task checkboxes หรือแผนที่เขียนเสร็จไปนับเป็นผลทดสอบ

## 9. ขอบเขตที่ยังต้องพิสูจน์และวิธีรับมือ

- ขาดเครื่อง macOS/host/license: ทำ development ที่ไม่อาศัยเครื่องนั้นได้ แต่ native target ยัง PENDING และห้ามรับรอง v1 ครบ 12 คู่
- host ไม่ให้ trusted user approval/fresh context: บันทึก capability ที่ขาด คง NOT_READY สำหรับ flow ที่ต้องใช้ และออกแบบ integration ที่ host รองรับก่อนถือว่า adapter ครบ
- remote protections/actor/workflows ตรวจไม่ได้: LOCAL_ONLY ไม่มีการเพิ่ม privilege เพื่อแก้; คู่มือ onboarding บอก prerequisite ที่ชัด
- native supervision ไม่ผ่าน crash/detached-child/ownership tests: ไม่รับ workload นั้นจนมี driver ที่พิสูจน์แล้ว และไม่เปลี่ยน failures เป็น success เพื่อปิด PoC
- package/build/dependency incompatibility: แก้เฉพาะ isolated toolchain พร้อม lock/version change ที่ review แล้ว ไม่แก้ global Python ของผู้ใช้
- ต้องติดต่อคนจริงหรือทำ admin setup: ส่ง task pack/ขั้นตอนให้เจ้าของดำเนินการตามอำนาจ ไม่ส่งข้อความหรือเปลี่ยนระบบแทนโดยไม่มีคำสั่ง

## 10. Self-review ของแผน (เอกสาร ไม่ใช่ test results)

- Spec coverage: C01–C23 และทุกหมวดของ spec มี task owner ตามตารางข้างต้น
- Step scan: ทุก task มี output/interfaces, failing assertions, คำสั่ง RED/GREEN และขอบเขต commit; setup/docs รวมกับ deliverable ที่ต้องใช้
- Type consistency: เพิ่ม schema ที่ต้องใช้ก่อน service (TeamPlan/StageReport), ระบุ DTO owners และแยก GateResult ออกจาก wait status; แก้ score_matrix signature และตรวจ runtime digest ต่อ OS/architecture; ไม่มีการเชื่อ passed/approved flags จาก caller
- Review Focus: RF1–RF5 มี negative tests อยู่กับผู้รับผิดชอบ ไม่ใช้การอ่าน policy แทนการตรวจพฤติกรรม
- Proportion: แผนระบุ interfaces/assertions/gates และมอบ body ของแต่ละ function ให้ implementer; ไม่มี production implementation ในเอกสารนี้
- ไม่มี checkbox implementation ใดถูกทำเครื่องหมายเสร็จ และยังไม่มี test/build/installation/human trial ตามแผนนี้ถูกรัน

## 11. แหล่งอ้างอิงและการเลือกที่ต้องทบทวนเมื่อเริ่มสร้าง

- [Official MCP Python SDK installation](https://github.com/modelcontextprotocol/python-sdk/blob/main/docs/get-started/installation.md) และ [v2 API changes](https://github.com/modelcontextprotocol/python-sdk/blob/main/docs/whats-new.md): เลือก MCPServer/stdio และ strict core validation; ตรวจ API ของ exact pinned SDK ขณะลงมือ
- [PyInstaller operating model](https://pyinstaller.org/en/stable/operating-mode.html): bundle interpreter ได้ และ output ต้อง build/test ตาม OS ที่ใช้จริง
- [Python sqlite3](https://docs.python.org/3/library/sqlite3.html): local transactional state โดยไม่เปิด database server
- Direct versions ตรวจจาก official PyPI JSON endpoints ของ mcp, pydantic, psutil, httpx, PyYAML, pytest และ pyinstaller วันที่ 7 พฤศจิกายน 2026; ต้องเก็บ uv.lock/hashes และตรวจ dependency findings ก่อนรับรอง Final
- เอกสาร host, Playwright, Python environment และ Git rules ใช้ source list ใน spec; ผู้สร้างตรวจ version-specific behavior อีกครั้งจาก official sources เมื่อทดลอง native target

