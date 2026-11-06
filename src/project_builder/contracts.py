"""Strict shared data contracts; validation does not grant execution authority."""

from pathlib import Path
from typing import Annotated, Literal, Self

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator

NonEmptyStr = Annotated[str, Field(min_length=1)]
PositiveInt = Annotated[int, Field(gt=0)]
Stage = Literal["poc", "mvp", "beta", "final"]
RunStatus = Literal[
    "INTAKE", "ASSESSED", "BASELINE_CAPTURE", "BASELINE_FEEDBACK", "REQUIREMENT_REFINEMENT",
    "KICKOFF_REVIEW", "READY", "RUNNING", "VERIFYING", "DEVELOPMENT_COMPLETE",
    "STAGE_FEEDBACK", "FEEDBACK_TRIAGE", "HANDOFF", "COMPLETED", "NEEDS_INPUT",
    "WAITING_FOR_HUMAN", "RESOURCE_WAIT", "PAUSED", "FAILED", "CANCELLED", "CLEANUP_PENDING",
]
CommandIntent = Literal[
    "init", "start", "continue", "status", "help", "doctor", "guide", "change",
    "backlog", "feedback", "pause", "cancel", "cleanup",
]
# Known denied actions remain data for policy decisions, never executable commands.
ActionKind = Literal[
    "bootstrap_ref", "create_stage", "create_feature", "commit", "integrate_feature",
    "integrate_stage", "delete_feature", "open_pr_stage", "open_pr_develop", "open_pr_staging",
    "start_process", "stop_process", "cleanup_owned", "setup_environment", "install_project_tool",
    "merge_staging", "push_main", "push_staging", "open_pr_main", "enable_auto_merge",
    "enqueue_merge", "deploy_prod", "edit_protection", "delete_main", "delete_staging",
]


class StrictModel(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")


class RunIdentity(StrictModel):
    project_id: NonEmptyStr
    run_id: NonEmptyStr
    scope_id: NonEmptyStr
    stage: Stage
    contract_revision: PositiveInt


class StageContract(StrictModel):
    project_id: NonEmptyStr
    scope_id: NonEmptyStr
    stage: Stage
    revision: PositiveInt
    requirements_version: NonEmptyStr
    feature_ids: list[NonEmptyStr]
    allowed_actions: frozenset[NonEmptyStr]
    test_matrix_revision: PositiveInt
    participant_count: Literal[2, 3]
    approved_receipt_id: NonEmptyStr | None

    @field_validator("participant_count", mode="before")
    @classmethod
    def strict_participant_count(cls, value: object) -> object:
        # Literal equality otherwise accepts 2.0 as the integer 2.
        if type(value) is not int:
            raise ValueError("participant_count must be an integer")
        return value


class ApprovalReceipt(StrictModel):
    """Receipt data only; the host approval path must verify source and bindings."""

    id: NonEmptyStr
    contract_digest: NonEmptyStr
    source: NonEmptyStr
    event_binding: NonEmptyStr
    approved_at: AwareDatetime
    expires_at: AwareDatetime | None


class ActionRequest(StrictModel):
    kind: ActionKind
    project_id: NonEmptyStr
    run_id: NonEmptyStr
    source_ref: NonEmptyStr | None
    target_ref: NonEmptyStr | None
    expected_sha: NonEmptyStr | None
    operation_id: NonEmptyStr


class ActionDecision(StrictModel):
    allowed: bool
    code: NonEmptyStr
    reasons: list[str]


class GateResult(StrictModel):
    status: Literal["PASS", "FAIL", "UNVERIFIED"]
    reasons: list[str]
    evidence_ids: list[NonEmptyStr]


class CommandResult(StrictModel):
    status: NonEmptyStr
    summary: str
    next_action: str | None
    data: dict


class ScopeProfile(StrictModel):
    feature_ids: list[NonEmptyStr]
    domains: list[str]
    complexity: Literal["mini", "small", "medium", "large"]
    estimated_work: Annotated[int, Field(ge=0)]


RiskLevel = Literal["low", "medium", "high", "unknown"]


class RiskProfile(StrictModel):
    security: RiskLevel
    privacy: RiskLevel
    reliability: RiskLevel
    data_ai: RiskLevel
    unknowns: list[str]


class TeamBudget(StrictModel):
    max_active_specialists: PositiveInt = 1
    max_heavy_jobs: PositiveInt = 1


class TeamPlan(StrictModel):
    selected_roles: list[str]
    role_responsibilities: dict[str, list[str]]
    max_active_specialists: PositiveInt
    reviewer_strategy: str


class CommandPayload(StrictModel):
    output_format: Literal["text", "json"] = "text"


class ReadPayload(CommandPayload):
    kind: Literal["status", "help", "doctor", "guide", "backlog"]


class InitPayload(CommandPayload):
    kind: Literal["init"]


class StartPayload(CommandPayload):
    kind: Literal["start"]
    description: str | None = None


class ContinuePayload(CommandPayload):
    kind: Literal["continue"]


class ChangePayload(CommandPayload):
    kind: Literal["change"]
    text: NonEmptyStr
    urgency: Literal["normal", "urgent"] = "normal"


class FeedbackPayload(CommandPayload):
    kind: Literal["feedback"]
    feedback_path: Path | None = None


class ControlPayload(CommandPayload):
    kind: Literal["pause", "cancel", "cleanup"]


Payload = Annotated[
    ReadPayload | InitPayload | StartPayload | ContinuePayload | ChangePayload | FeedbackPayload | ControlPayload,
    Field(discriminator="kind"),
]


class CommandEnvelope(StrictModel):
    request_id: NonEmptyStr
    project_root: Path
    run_id: NonEmptyStr | None
    expected_revision: PositiveInt | None
    intent: CommandIntent
    payload: Payload

    @model_validator(mode="after")
    def payload_matches_intent(self) -> Self:
        if self.payload.kind != self.intent:
            raise ValueError("payload kind must match command intent")
        return self
