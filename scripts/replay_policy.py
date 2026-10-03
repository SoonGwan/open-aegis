"""Source-checkout wrapper for the installed API policy replay command."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from aegis.cli.replay_policy import main


if __name__ == '__main__':
    main()
