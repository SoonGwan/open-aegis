"""Supervise fixed MCP discovery code; this is not an arbitrary plugin sandbox."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

from .runtime import TaskControl

MAX_OUTPUT = 512 * 1024


class DiscoveryError(ValueError):
    pass


def discover(connection, stop=None, *, timeout=15):
    """Bound a child lifetime, reap on cancellation, and do not inherit app secrets."""
    control = TaskControl(stop=stop, deadline=time.monotonic() + timeout)
    environment = {k: v for k, v in os.environ.items()
                   if k in ('PATH', 'SYSTEMROOT', 'SSL_CERT_FILE', 'SSL_CERT_DIR', 'LANG', 'LC_CTYPE')}
    if connection.token_env and connection.token_env in os.environ:
        environment[connection.token_env] = os.environ[connection.token_env]
    request = json.dumps(connection.model_dump()).encode()
    bootstrap = ('import sys;sys.path.insert(0,sys.argv[1]);'
                 'from aegis.mcp_process import child_main;child_main()')
    process = None
    try:
        control.check()
        with tempfile.TemporaryDirectory(prefix='aegis-mcp-discovery-') as folder:
            # Output goes to a bounded child file, never an unbounded PIPE buffer.
            with tempfile.TemporaryFile(dir=folder) as output, tempfile.TemporaryFile(dir=folder) as input_file:
                input_file.write(request)
                input_file.seek(0)
                process = subprocess.Popen([sys.executable, '-I', '-c', bootstrap,
                                            str(Path(__file__).resolve().parent.parent)],
                                           cwd=folder, env=environment, stdin=input_file,
                                           stdout=output, stderr=subprocess.DEVNULL, close_fds=True)
                try:
                    while process.poll() is None:
                        control.wait(.02)
                    control.check()
                    if process.returncode != 0:
                        raise DiscoveryError('discovery_failed')
                    output.seek(0)
                    raw = output.read(MAX_OUTPUT + 1)
                    if len(raw) > MAX_OUTPUT:
                        raise DiscoveryError('output_budget')
                finally:
                    if process.poll() is None:
                        process.kill()
                    process.wait(timeout=3)
        from .remote_mcp import _decode
        value = _decode(raw)
        if not isinstance(value, dict) or set(value) != {'protocolVersion', 'serverInfo', 'tools'}:
            raise DiscoveryError('discovery_contract')
        return value
    except (OSError, ValueError, TimeoutError, InterruptedError):
        raise DiscoveryError('discovery_failed') from None
    finally:
        if process is not None and process.poll() is None:
            process.kill()
            process.wait(timeout=3)


def child_main():
    # Apply limits in the child rather than preexec_fn in a threaded web process.
    # Linux AS is a virtual-address limit. macOS has no equivalent reliable RSS
    # guarantee here; neither is a filesystem/egress isolation boundary.
    import resource
    resource.setrlimit(resource.RLIMIT_CPU, (5, 5))
    resource.setrlimit(resource.RLIMIT_FSIZE, (MAX_OUTPUT, MAX_OUTPUT))
    resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
    if sys.platform.startswith('linux'):
        resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))
    from .remote_mcp import Client, Connection, _decode, _encode
    client = None
    try:
        raw = sys.stdin.buffer.read(32769)
        if len(raw) > 32768:
            raise ValueError('configuration_budget')
        connection = Connection(**_decode(raw))
        client = Client(connection)
        control = TaskControl(deadline=time.monotonic() + 12)
        initialized = client.initialize(control)
        tools = client.list_tools(control)
        fields = {'name', 'title', 'description', 'inputSchema', 'outputSchema', 'annotations', '_meta'}
        result = {'protocolVersion': initialized['protocolVersion'],
                  'serverInfo': {k: initialized['serverInfo'][k] for k in ('name', 'version')},
                  'tools': sorted([{k: v for k, v in tool.items() if k in fields} for tool in tools],
                                  key=lambda tool: tool['name'])}
        encoded = _encode(result, MAX_OUTPUT)
        token = os.environ.get(connection.token_env, '') if connection.token_env else ''
        stack = [result]
        while token and stack:
            item = stack.pop()
            if isinstance(item, str) and token in item:
                raise ValueError('credential_in_metadata')
            if isinstance(item, dict):
                stack.extend(item.keys())
                stack.extend(item.values())
            elif isinstance(item, list):
                stack.extend(item)
        sys.stdout.buffer.write(encoded)
        sys.stdout.buffer.flush()
    except Exception:
        raise SystemExit(1) from None
    finally:
        if client is not None:
            try:
                client.close(TaskControl(deadline=time.monotonic() + 1))
            except Exception:
                pass
