"""Small real fixtures; each workload has a hard 25 second upper bound."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

mode, output, *args = sys.argv[1:]
if mode == "echo":
    Path(output).write_text(json.dumps(args), encoding="utf-8")
elif mode == "fail":
    sys.exit(7)
elif mode in {"tree", "detached"}:
    flags = subprocess.DETACHED_PROCESS if os.name == "nt" and mode == "detached" else 0
    child = subprocess.Popen([sys.executable, __file__, "sleep", output], creationflags=flags,
                             start_new_session=os.name != "nt" and mode == "detached")
    Path(output).write_text(json.dumps([os.getpid(), child.pid]), encoding="utf-8")
    time.sleep(25)
else:
    time.sleep(25)
