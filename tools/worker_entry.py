"""PyInstaller entry for the optional self-contained Windows anaStruct worker."""
from __future__ import annotations

import importlib.metadata
import sys


def main() -> int:
    if "--check" in sys.argv[1:]:
        import numpy
        from anastruct import SystemElements

        version = importlib.metadata.version("anastruct")
        if version != "1.7.0":
            raise RuntimeError(f"Expected anaStruct 1.7.0, got {version}")
        assert SystemElements is not None and numpy.__version__
        print("anaStruct 1.7.0 OK - GO standalone worker 0.5.5")
        return 0

    from go_anastruct_2d.worker import main as worker_main
    return worker_main()


if __name__ == "__main__":
    raise SystemExit(main())
