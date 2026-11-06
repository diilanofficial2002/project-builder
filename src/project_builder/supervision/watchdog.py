"""Independent, bounded macOS watchdog and pre-exec process-group anchor.

The watchdog stays outside the workload group, retains its unreaped session
leader to prevent PGID reuse, and only signals that group. This deliberately
makes no containment guarantee for setsid(), external launchers, or daemonization.
"""
import json
import os
from pathlib import Path
import selectors
import signal
import subprocess
import sys
import time

import psutil


def _same(pid, started):
    try:
        return psutil.Process(pid).create_time() == started
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return False


def _anchor():
    # No workload executes until the owning supervisor persists the handle and
    # sends its bounded start message through the watchdog.
    with selectors.DefaultSelector() as selector:
        selector.register(sys.stdin.buffer, selectors.EVENT_READ)
        if not selector.select(timeout=8):
            return 2
        data = sys.stdin.buffer.readline(65537)
    if not data or len(data) > 65536:
        return 2
    from .models import ProcessSpec
    spec = ProcessSpec.model_validate_json(data)
    os.chdir(spec.cwd)
    env = dict(os.environ)
    env.update(spec.env)
    # stdin is replaced: control pipe is never inherited by the recipe.
    with open(os.devnull, "rb") as null:
        os.dup2(null.fileno(), 0)
    os.execve(spec.executable, [str(spec.executable), *spec.argv], env)


def _group_members(group):
    members = []
    for process in psutil.process_iter(["pid", "status"]):
        try:
            if os.getpgid(process.pid) == group and process.info["status"] != psutil.STATUS_ZOMBIE:
                members.append(process.pid)
        except (ProcessLookupError, PermissionError, psutil.NoSuchProcess):
            pass
    return members


def _watch(parent_pid, parent_started, scratch, token, lifetime):
    anchor = None
    detached = set()
    cleanup_error = None
    grace = 0.5
    exit_code = None
    try:
        prefix=[sys.executable,"--watchdog"] if getattr(sys,"frozen",False) else [sys.executable,"-m","project_builder.supervision.watchdog"]
        anchor = subprocess.Popen([*prefix, "--anchor"], stdin=subprocess.PIPE,
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                  start_new_session=True, bufsize=0)
        anchor_started = psutil.Process(anchor.pid).create_time()
        print(json.dumps({"pid": anchor.pid, "started": anchor_started}), flush=True)
        started = False
        deadline = time.monotonic() + lifetime
        with selectors.DefaultSelector() as selector:
            selector.register(sys.stdin.buffer, selectors.EVENT_READ)
            while time.monotonic() < deadline:
                if not _same(parent_pid, parent_started):
                    break
                try:
                    process = psutil.Process(anchor.pid)
                    if process.status() == psutil.STATUS_ZOMBIE:
                        break  # do not reap; anchor PID/PGID remains reserved through cleanup
                    for child in process.children(recursive=True):
                        try:
                            if os.getpgid(child.pid) != anchor.pid:
                                detached.add((child.pid, child.create_time()))
                        except (ProcessLookupError, psutil.NoSuchProcess):
                            pass
                except psutil.NoSuchProcess:
                    raise RuntimeError("group anchor disappeared before ownership-safe cleanup")
                if detached:
                    break
                if selector.select(timeout=0.1):
                    line = sys.stdin.buffer.readline(65537)
                    if not line:
                        break
                    if len(line) > 65536:
                        raise ValueError("oversized watchdog command")
                    command = json.loads(line)
                    if command.get("command") == "stop":
                        grace = min(30.0, max(0.0, float(command.get("grace", 0.5))))
                        break
                    if command.get("command") != "start" or started:
                        raise ValueError("unexpected watchdog command")
                    encoded = json.dumps(command["spec"]).encode() + b"\n"
                    anchor.stdin.write(encoded)
                    anchor.stdin.flush()
                    anchor.stdin.close()
                    started = True
    except BaseException as error:
        cleanup_error = str(error)
    finally:
        if anchor is not None:
            try:
                # Popen has deliberately not polled/waited yet. Its unreaped child
                # reserves the group leader PID, including after executable exit.
                if not _same(anchor.pid, anchor_started) or os.getpgid(anchor.pid) != anchor.pid:
                    raise RuntimeError("group anchor identity not verified")
                os.killpg(anchor.pid, signal.SIGTERM)
                end = time.monotonic() + grace
                while _group_members(anchor.pid) and time.monotonic() < end:
                    time.sleep(0.02)
                if _group_members(anchor.pid):
                    os.killpg(anchor.pid, signal.SIGKILL)
                end = time.monotonic() + 5
                while _group_members(anchor.pid) and time.monotonic() < end:
                    time.sleep(0.02)
                if _group_members(anchor.pid):
                    raise TimeoutError("group members remain after termination")
            except (OSError, RuntimeError, TimeoutError) as error:
                cleanup_error = str(error)
            finally:
                if anchor.stdin and not anchor.stdin.closed:
                    anchor.stdin.close()
                try:
                    exit_code = anchor.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    cleanup_error = "group anchor failed to exit"
        if detached:
            cleanup_error = "observed detached descendants; cooperative containment violated: " + repr(sorted(detached))
        result = {"token": token, "status": "CLEANUP_PENDING" if cleanup_error else "CLEANED",
                  "reason": cleanup_error or "verified cooperative group empty", "exit_code": exit_code}
        temporary = scratch / "watchdog-result.tmp"
        temporary.write_text(json.dumps(result), encoding="utf-8")
        temporary.replace(scratch / "watchdog-result.json")
    return 1 if cleanup_error else 0


def main():
    if sys.platform != "darwin":
        raise SystemExit("watchdog native driver is macOS only")
    if sys.argv[1:] == ["--anchor"]:
        return _anchor()
    pid, started, scratch, token, lifetime = sys.argv[1:]
    return _watch(int(pid), float(started), Path(scratch), token, min(86400.0, float(lifetime)))


if __name__ == "__main__":
    raise SystemExit(main())
