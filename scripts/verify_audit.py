"""Source-checkout wrapper for the installed maintenance command."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from aegis.cli.audit import main


if __name__ == "__main__":
    main()
