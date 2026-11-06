"""Typed supervision contracts. See docs/supervision.md for trust boundaries."""
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator

from project_builder.contracts import RunIdentity, StrictModel


class ResourceRequest(StrictModel):
    project_id: str = Field(min_length=1)
    memory_bytes: int | None = Field(default=None, ge=0)
    disk_bytes: int = Field(default=0, ge=0)
    heavy: bool = True
    specialist: bool = True


class MachineSample(StrictModel):
    total_ram_bytes: int = Field(gt=0)
    available_ram_bytes: int = Field(ge=0)
    disk_total_bytes: int = Field(gt=0)
    disk_free_bytes: int = Field(ge=0)

    @property
    def ram_reserve(self) -> int:
        return max(2**30, self.total_ram_bytes // 5)

    @property
    def disk_reserve(self) -> int:
        return max(2**30, min(5 * 2**30, self.disk_total_bytes // 20))

    @property
    def pressured(self) -> bool:
        return self.available_ram_bytes < self.ram_reserve or self.disk_free_bytes < self.disk_reserve


class AdmissionDecision(StrictModel):
    allowed: bool
    code: str
    lease_id: str | None = None


class ProcessSpec(StrictModel):
    executable: Path
    argv: list[str]
    cwd: Path
    env: dict[str, str]
    budget: ResourceRequest
    timeout_seconds: float = Field(default=3600.0, gt=0, le=86400, allow_inf_nan=False)
    containment: Literal["contained_tree", "cooperative_group"] = "contained_tree"
    trusted_recipe_id: str | None = None

    @model_validator(mode="after")
    def safe_arguments(self):
        if not self.executable.is_absolute() or not self.cwd.is_absolute():
            raise ValueError("executable and cwd must be absolute paths")
        if self.executable.suffix.lower() in {".bat", ".cmd", ".ps1"}:
            raise ValueError("shell/batch executables are not supervised recipes")
        if self.executable.name.lower() in {"cmd.exe", "powershell.exe", "pwsh.exe", "sh", "bash", "zsh"}:
            raise ValueError("shell command interpreters require an isolated driver")
        if any("\0" in arg for arg in [str(self.executable), str(self.cwd), *self.argv]):
            raise ValueError("NUL in process arguments")
        if any(not key or "=" in key or "\0" in key or "\0" in value for key, value in self.env.items()):
            raise ValueError("invalid environment key or value")
        return self


class ResourceHandle(StrictModel):
    id: str
    owner: RunIdentity
    pid: int
    process_started_at: float
    process_group_id: int | None
    owned_paths: list[Path]
    lease_id: str
    owner_token: str
    containment: Literal["contained_tree", "cooperative_group"]


class CleanupReceipt(StrictModel):
    handle_id: str
    status: Literal["CLEANED", "OWNERSHIP_UNVERIFIED", "CLEANUP_PENDING"]
    reason: str
    exit_code: int | None = None
    workload_stopped: bool = False
    paths_removed: list[Path] = Field(default_factory=list)
