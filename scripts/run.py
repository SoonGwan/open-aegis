"""Load literal .env values without shell evaluation, then run the console."""
import os
from pathlib import Path
import sys
from config_env import load_config_env

root = Path(__file__).resolve().parent.parent
os.chdir(root)
sys.path.insert(0, str(root))
load_config_env(root / '.env', os.environ)

from aegis.__main__ import AegisServer
from aegis.app import create_app
from aegis.maintenance import WorkspaceBusy

try:
    AegisServer(create_app(), host=os.environ.get('AEGIS_HOST', '127.0.0.1'),
                port=int(os.environ.get('AEGIS_PORT', '8787')), access_log=False,
                timeout_graceful_shutdown=5).run()
except WorkspaceBusy as exc:
    raise SystemExit(str(exc))
