"""macOS cooperative process-group driver. Not a sandbox for detaching workloads."""
import json
import os
from pathlib import Path
import selectors
import subprocess
import sys
import time

import psutil

from project_builder.platform_paths import reject_links


def verify_completion(scratch: Path, token: str):
    reject_links(scratch / "watchdog-result.json")
    proof = (scratch / "watchdog-result.json").read_bytes()
    if len(proof) > 16384:
        raise ValueError("oversized watchdog completion proof")
    result = json.loads(proof)
    if result.get("token") != token or result.get("status") != "CLEANED":
        raise RuntimeError(result.get("reason", "watchdog did not prove group exit"))
    return result


class MacOSGroup:
    """A separate watchdog owns a session leader anchor before executing a recipe.

    Only Supervisor's configured cooperative recipe allowlist can reach this class.
    Group escape is unsupported; observed escapes produce CLEANUP_PENDING.
    """
    def __init__(self, spec, scratch, token):
        self.spec, self.scratch, self.token = spec, scratch, token
        self.process = None
        self.pid = 0
        self.started = 0.0
        self.process_group_id = None
        self._resumed = False
        prefix=[sys.executable,"--watchdog"] if getattr(sys,"frozen",False) else [sys.executable,"-m","project_builder.supervision.watchdog"]
        args = [*prefix, str(os.getpid()),
                str(psutil.Process().create_time()), str(scratch), token, str(spec.timeout_seconds)]
        try:
            self.process = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                            stderr=subprocess.DEVNULL, start_new_session=True, bufsize=0)
            with selectors.DefaultSelector() as selector:
                selector.register(self.process.stdout, selectors.EVENT_READ)
                if not selector.select(timeout=5):
                    raise TimeoutError("watchdog failed to initialize")
                data = self.process.stdout.readline(4097)
            if len(data) > 4096 or not data.endswith(b"\n"):
                raise RuntimeError("invalid watchdog startup response")
            ready = json.loads(data)
            self.pid, self.started = ready["pid"], ready["started"]
            self.process_group_id = self.pid
            if psutil.Process(self.pid).create_time() != self.started or os.getpgid(self.pid) != self.pid:
                raise RuntimeError("group anchor identity mismatch")
        except BaseException:
            self.close()
            raise

    def _send(self, value):
        message = json.dumps(value).encode() + b"\n"
        if len(message) > 65536:
            raise ValueError("watchdog control message exceeds 64 KiB")
        self.process.stdin.write(message)
        self.process.stdin.flush()

    def resume(self):
        self._send({"command": "start", "spec": self.spec.model_dump(mode="json")})
        self._resumed = True

    def poll(self):
        if self.process.poll() is None:
            return None
        result = verify_completion(self.scratch, self.token)
        return result.get("exit_code", 1)

    def stop(self, grace_seconds=5.0):
        if self.process.poll() is None:
            try:
                self._send({"command": "stop", "grace": grace_seconds})
            except (BrokenPipeError, OSError):
                pass
            try:
                self.process.wait(timeout=grace_seconds + 8)
            except subprocess.TimeoutExpired as error:
                raise TimeoutError("watchdog did not finish group cleanup") from error
        verify_completion(self.scratch, self.token)

    def close(self):
        if self.process is None:
            return
        # Control EOF asks the independent watchdog to clean the group; never kill
        # that watchdog while it is still responsible for live descendants.
        if self.process.stdin and not self.process.stdin.closed:
            self.process.stdin.close()
        try:
            self.process.wait(timeout=10)
        except subprocess.TimeoutExpired as error:
            raise TimeoutError("watchdog remains active; cleanup ownership retained") from error
        finally:
            if self.process.stdout:
                self.process.stdout.close()
