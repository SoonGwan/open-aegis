"""Read literal app settings and only explicitly referenced integration values."""
import json
import re


REFERENCES = {
    'AEGIS_MODEL_DESTINATIONS': ('base_env', 'key_env'),
    'AEGIS_NOTIFICATION_DESTINATIONS': ('endpoint_env', 'token_env'),
    'AEGIS_SCOPESENTRY_SOURCES': ('token_env',),
    'AEGIS_MCP_CONNECTIONS': ('token_env',),
    'AEGIS_MCP_EXECUTORS': ('scope_key_env',),
}
SYSTEM_NAMES = {'HOME', 'PATH', 'SHELL', 'USER', 'LOGNAME', 'TMPDIR', 'VIRTUAL_ENV'}


def load_config_env(path, environment):
    if not path.exists():
        return
    values = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        key = key.strip()
        if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]{0,99}', key):
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
            value = value[1:-1]
        values[key] = value
    for key, value in values.items():
        if key.startswith('AEGIS_'):
            environment.setdefault(key, value)
    for definition, fields in REFERENCES.items():
        raw = environment.get(definition, '[]')
        if len(raw) > 262144:
            continue
        try:
            items = json.loads(raw)
        except (ValueError, RecursionError):
            continue  # The application validates and reports invalid definitions.
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            for field in fields:
                key = item.get(field)
                if (isinstance(key, str) and key in values and key not in SYSTEM_NAMES
                        and not key.startswith(('PYTHON', 'LD_', 'DYLD_'))):
                    environment.setdefault(key, values[key])
