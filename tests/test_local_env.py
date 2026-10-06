"""Exercise the real launch script with an owned stand-in server, without traffic."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


def test_launch_loads_named_integration_values_without_shell_or_system_overrides(tmp_path):
    root = Path(__file__).resolve().parents[1]
    scripts = tmp_path / 'scripts'
    scripts.mkdir()
    for name in ('run.py', 'config_env.py'):
        if (root / 'scripts' / name).exists():
            shutil.copy2(root / 'scripts' / name, scripts / name)
    package = tmp_path / 'aegis'
    package.mkdir()
    (package / '__init__.py').write_text('')
    (package / 'app.py').write_text('def create_app(): return None\n')
    (package / 'maintenance.py').write_text('class WorkspaceBusy(RuntimeError): pass\n')
    names = ['OWNED_MODEL_BASE', 'OWNED_MODEL_KEY', 'OWNED_WEBHOOK', 'OWNED_TOKEN',
             'OWNED_SCOPE_KEY', 'OWNED_OVERRIDE', 'OWNED_UNREFERENCED', 'AEGIS_PORT', 'HOME']
    (package / '__main__.py').write_text(
        'import json,os\nclass AegisServer:\n'
        ' def __init__(self,*a,**kw): pass\n'
        f' def run(self): print(json.dumps({{k:os.environ.get(k) for k in {names!r}}}))\n')
    config = {
        'AEGIS_MODEL_DESTINATIONS': [{'base_env': 'OWNED_MODEL_BASE', 'key_env': 'OWNED_MODEL_KEY'},
                                   {'base_env': 'HOME', 'key_env': 'OWNED_MODEL_KEY'}],
        'AEGIS_NOTIFICATION_DESTINATIONS': [{'endpoint_env': 'OWNED_WEBHOOK', 'token_env': 'OWNED_OVERRIDE'}],
        'AEGIS_SCOPESENTRY_SOURCES': [{'token_env': 'OWNED_TOKEN'}],
        'AEGIS_MCP_CONNECTIONS': [{'token_env': 'OWNED_TOKEN'}],
        'AEGIS_MCP_EXECUTORS': [{'scope_key_env': 'OWNED_SCOPE_KEY'}],
    }
    rows = [f'{key}={json.dumps(value)}' for key, value in config.items()]
    rows += ['AEGIS_PORT=8799', 'OWNED_MODEL_BASE=https://owned.invalid/v1',
             "OWNED_MODEL_KEY='owned-$literal-$(touch forbidden)'",
             'OWNED_WEBHOOK=https://owned.invalid/hook', 'OWNED_TOKEN=owned-token',
             'OWNED_SCOPE_KEY=owned-scope', 'OWNED_OVERRIDE=file-value',
             'OWNED_UNREFERENCED=do-not-load', 'HOME=do-not-replace']
    (tmp_path / '.env').write_text('\n'.join(rows) + '\n')
    env = {k: v for k, v in os.environ.items() if not k.startswith(('AEGIS_', 'OWNED_'))}
    env.update(AEGIS_PORT='8787', OWNED_OVERRIDE='exported-value')
    result = subprocess.run([sys.executable, str(scripts / 'run.py')], cwd=tmp_path,
                            env=env, text=True, capture_output=True, check=True)
    values = json.loads(result.stdout)
    assert values['OWNED_MODEL_BASE'] == 'https://owned.invalid/v1'
    assert values['OWNED_MODEL_KEY'] == 'owned-$literal-$(touch forbidden)'
    assert values['OWNED_WEBHOOK'] == 'https://owned.invalid/hook'
    assert values['OWNED_TOKEN'] == 'owned-token'
    assert values['OWNED_SCOPE_KEY'] == 'owned-scope'
    assert values['OWNED_OVERRIDE'] == 'exported-value'
    assert values['AEGIS_PORT'] == '8787'
    assert values['OWNED_UNREFERENCED'] is None
    assert values['HOME'] == env.get('HOME')
    assert not (tmp_path / 'forbidden').exists()
