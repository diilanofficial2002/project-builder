"""Read-only preflight composition. No ambient credential discovery."""

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Iterator

from project_builder.git.github_inspector import GitHubInspector
from project_builder.policy.models import EnforcementReport, RemoteIdentity, RepositoryRef

_inspector: ContextVar[GitHubInspector | None] = ContextVar("github_inspector", default=None)


@contextmanager
def use_inspector(inspector: GitHubInspector) -> Iterator[None]:
    """Service composition/test injection; never populate from command payloads."""
    token = _inspector.set(inspector)
    try:
        yield
    finally:
        _inspector.reset(token)


def inspect_enforcement(repo: RepositoryRef, identity: RemoteIdentity) -> EnforcementReport:
    return (_inspector.get() or GitHubInspector()).inspect_enforcement(repo, identity)
