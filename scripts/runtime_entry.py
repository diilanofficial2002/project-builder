"""Frozen entrypoint, including the independent macOS watchdog dispatch."""
import sys
from project_builder.cli import main

if __name__=="__main__":
    if sys.argv[1:2]==["--watchdog"]:
        from project_builder.supervision.watchdog import main as watchdog
        sys.argv.pop(1)
        raise SystemExit(watchdog())
    raise SystemExit(main())
