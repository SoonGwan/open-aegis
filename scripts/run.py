"""Load literal .env values without shell evaluation, then run the console."""
import os
from pathlib import Path
import sys

root = Path(__file__).resolve().parent.parent
os.chdir(root)
sys.path.insert(0, str(root))
env_file = root / '.env'
if env_file.exists():
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        if key.startswith('AEGIS_'):
            os.environ.setdefault(key, value.strip().strip('"\''))

import uvicorn
from aegis.app import create_app

uvicorn.run(create_app(), host=os.environ.get('AEGIS_HOST', '127.0.0.1'), port=int(os.environ.get('AEGIS_PORT', '8787')),
            access_log=False, timeout_graceful_shutdown=5)
