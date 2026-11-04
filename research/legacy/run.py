"""Convenience entry point: python run.py --synthetic, or python run.py download ..."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from regime_backtester.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
