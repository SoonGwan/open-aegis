"""Rehearse the real Compose definition with owned volumes and no target approvals.

Requires Docker Compose >=2.24.4 (ports !override). Optional PostgreSQL uses a
disposable database container and fresh-schema logical restore, never a host DB.
"""
import argparse
from http.cookiejar import CookieJar
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import time
from urllib.error import HTTPError
from urllib.request import Request, build_opener, HTTPCookieProcessor, ProxyHandler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--postgres', action='store_true', help='Use an actual PostgreSQL container, native HTTP storage and fresh-schema restore')
    parser.add_argument('--postgres-image', default='postgres:16-alpine', help='PostgreSQL 16-compatible image; resolved digest/version recorded in result')
    args = parser.parse_args()
    docker = shutil.which('docker')
    if not docker:
        parser.error('Docker is required; no Compose verification performed')
    root = Path(__file__).resolve().parents[1]
    identity = 'open-aegis-compose-'+secrets.token_hex(8)
    image = identity+':local'
    backend = 'postgres' if args.postgres else 'sqlite'
    password, token, database_password = [secrets.token_urlsafe(24) for _ in range(3)]
    # Do not inherit user application/Compose configuration or credentials.
    env = {key:value for key,value in os.environ.items()
           if not key.startswith(('AEGIS_', 'COMPOSE_'))}
    result = None

    def progress(message):
        print(message, file=sys.stderr, flush=True)

    def run(arguments, timeout=60):
        completed = subprocess.run([docker,*map(str,arguments)], cwd=root, env=env,
                                   capture_output=True, text=True, timeout=timeout)
        if completed.returncode:
            # Captured config/errors may include synthetic secrets; never publish them.
            raise RuntimeError(f'Owned Docker/Compose operation failed (exit {completed.returncode})')
        return completed.stdout.strip()

    with tempfile.TemporaryDirectory(prefix='aegis-compose-review-') as temporary:
        folder = Path(temporary)
        environment_file, override = folder/'fixture.env', folder/'override.yml'
        values = {'AEGIS_SETUP_TOKEN':token, 'AEGIS_INSTALL_POSTGRES':str(int(args.postgres)),
                  'AEGIS_STORAGE_BACKEND':backend, 'AEGIS_POSTGRES_SCHEMA':'owned_source' if args.postgres else '',
                  'AEGIS_POSTGRES_DSN':f'postgresql://owned:{database_password}@database:5432/owned' if args.postgres else '',
                  'REVIEW_DB_PASSWORD':database_password}

        def write_environment():
            descriptor = os.open(environment_file,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
            with os.fdopen(descriptor,'w') as output:
                output.write(''.join(f'{key}={value}\n' for key,value in values.items()))

        write_environment()
        text = f'''services:
  aegis:
    image: {image}
    ports: !override
      - "127.0.0.1::8787"
    restart: "no"
    healthcheck:
      interval: 1s
'''
        if args.postgres:
            text += f'''    networks:
      - default
      - database-only
  database:
    image: {json.dumps(args.postgres_image)}
    environment:
      POSTGRES_USER: owned
      POSTGRES_DB: owned
      POSTGRES_PASSWORD: ${{REVIEW_DB_PASSWORD:?}}
    volumes:
      - database-data:/var/lib/postgresql/data
    networks:
      - database-only
    healthcheck:
      test: ["CMD", "pg_isready", "-U", "owned", "-d", "owned"]
      interval: 1s
      timeout: 3s
      retries: 60
volumes:
  database-data:
networks:
  database-only:
    internal: true
'''
        override.write_text(text)
        command = ['compose','--project-name',identity,'--project-directory',str(root),
                   '--env-file',str(environment_file),'-f',str(root/'compose.yml'),'-f',str(override)]

        def compose(*arguments, timeout=60):
            return run([*command,*arguments], timeout)

        def container(service='aegis'):
            identifier = compose('ps','--all','--quiet',service)
            if not re.fullmatch(r'[0-9a-f]{64}',identifier):
                raise RuntimeError('Expected exactly one owned service container')
            inspected = json.loads(run(['inspect',identifier]))[0]
            assert inspected['Config']['Labels']['com.docker.compose.project'] == identity
            return identifier

        def wait_healthy(service='aegis'):
            identifier = container(service)
            deadline = time.monotonic()+90
            while time.monotonic() < deadline:
                state = json.loads(run(['inspect','--format','{{json .State}}',identifier]))
                if not state['Running']:
                    raise RuntimeError('Owned service exited during startup')
                if state.get('Health',{}).get('Status') == 'healthy':
                    return identifier
                time.sleep(.2)
            raise RuntimeError('Owned service health timed out')

        def stop():
            identifier = container()
            compose('stop','--timeout','15','aegis',timeout=30)
            state = json.loads(run(['inspect','--format','{{json .State}}',identifier]))
            assert not state['Running'] and state['ExitCode'] in (0,143)

        def maintenance(*arguments):
            return compose('run','--rm','--no-deps','-T','aegis',*arguments)

        anonymous = build_opener(ProxyHandler({}))
        authenticated = build_opener(ProxyHandler({}),HTTPCookieProcessor(CookieJar()))
        base = ''

        def start():
            nonlocal base
            compose('up','--detach','--no-deps','aegis')
            wait_healthy()
            ports = run(['port',container(),'8787/tcp']).splitlines()
            assert len(ports)==1 and re.fullmatch(r'127\.0\.0\.1:[0-9]+',ports[0])
            base = 'http://'+ports[0]

        def request(path, body=None, expected=200, opener=authenticated):
            query = Request(base+path, data=None if body is None else json.dumps(body).encode(),
                            headers={} if body is None else {'Content-Type':'application/json'})
            try:
                response = opener.open(query,timeout=5)
            except HTTPError as exc:
                response = exc
            with response:
                if response.code!=expected:
                    raise RuntimeError(f'HTTP {path} returned {response.code}; expected {expected}')
                raw = response.read()
                return json.loads(raw) if 'application/json' in response.headers.get('Content-Type','') else raw.decode()

        cleanup_needed = False
        try:
            compose_version = run(['compose','version','--short'])
            model = json.loads(compose('config','--format','json'))
            service = model['services']['aegis']
            assert service['environment']['AEGIS_STORAGE_BACKEND']==backend
            assert len(service['ports'])==1 and service['ports'][0]['host_ip']=='127.0.0.1'
            assert service['read_only'] and service['cap_drop']==['ALL']
            assert 'no-new-privileges:true' in service['security_opt']
            if args.postgres:
                assert not model['services']['database'].get('ports')
                assert model['networks']['database-only']['internal']
            cleanup_needed = True
            progress(f'Building actual Compose application ({backend})')
            compose('build','aegis',timeout=900)
            database_info = None
            if args.postgres:
                compose('up','--detach','database',timeout=300)
                database = wait_healthy('database')
                assert not any(json.loads(run(['inspect','--format','{{json .NetworkSettings.Ports}}',database])).values())
                database_info = {'image_id':run(['inspect','--format','{{.Image}}',database]),
                                 'repo_digests':json.loads(run(['image','inspect','--format','{{json .RepoDigests}}',args.postgres_image])),
                                 'version':run(['exec',database,'postgres','--version'])}
                assert json.loads(maintenance('aegis-init-postgres'))['created']
            start()
            configuration = json.loads(run(['inspect',container()]))[0]
            assert configuration['HostConfig']['ReadonlyRootfs']
            assert 'ALL' in configuration['HostConfig']['CapDrop']
            assert 'no-new-privileges:true' in configuration['HostConfig']['SecurityOpt']
            assert any(mount['Type']=='volume' and mount['Destination']=='/app/data'
                       for mount in configuration['Mounts'])
            assert int(run(['exec',container(),'id','-u']))==10001
            request('/api/assets',expected=401,opener=anonymous)
            request('/api/auth/setup',{'password':password,'setup_token':token})
            assert request('/api/settings')['storage']==backend
            bundles = re.findall(r'(?:src|href)="(/assets/[^"\s]+)"',request('/'))
            assert bundles and any(path.endswith('.js') for path in bundles)
            for path in bundles:
                assert request(path)
            asset = request('/api/assets',{'name':'Owned Compose fixture','url':'https://compose-fixture.invalid/','authorized':True})
            task = request('/api/tasks',{'name':'Never-approved Compose fixture','asset_ids':[asset['id']]})
            assert task['status']=='pending' and task['approved_at'] is None
            archive = '/app/data/review-backup.'+('zip' if args.postgres else 'db')
            compose('exec','-T','aegis','aegis-backup','--output',archive)
            checkpoint = '/app/data/review-checkpoint.json'
            compose('exec','-T','aegis','aegis-verify-audit','--output',checkpoint)
            late = request('/api/notes',{'title':'After Compose backup','content':'Synthetic only'})
            assert request('/api/runtime')['requests']['requests']==0
            stop()
            progress('Recreating services with retained named volumes')
            compose('rm','--force','aegis')
            if args.postgres:
                compose('stop','--timeout','15','database',timeout=30)
                compose('rm','--force','database')
                compose('up','--detach','database')
                wait_healthy('database')
            start()
            assert asset['id'] in [row['id'] for row in request('/api/assets')]
            assert request('/api/tasks/'+task['id'])['task']['status']=='pending'
            assert late['id'] in [row['id'] for row in request('/api/notes')]
            stop()
            progress('Restoring backup with application stopped')
            restore = ['aegis-restore','--source',archive]
            if args.postgres:
                restore += ['--schema','owned_restored','--checkpoint',checkpoint]
            restored = json.loads(maintenance(*restore))
            assert restored['sessions_revoked']
            if args.postgres:
                assert restored['existing_schema_preserved']
                # The original schema still contains its later note; restore created a new one.
                code = "import os,psycopg; from psycopg import sql; " \
                       "db=psycopg.connect(os.environ['AEGIS_POSTGRES_DSN']); " \
                       "q=sql.SQL('SELECT count(*) FROM {}.records WHERE kind=%s AND id=%s').format(sql.Identifier('owned_source')); " \
                       "assert db.execute(q,('notes',"+repr(late['id'])+")).fetchone()[0]==1; db.close()"
                maintenance('python','-c',code)
                values['AEGIS_POSTGRES_SCHEMA']='owned_restored'
                write_environment()
            audit = json.loads(maintenance('aegis-verify-audit','--checkpoint',checkpoint))
            assert audit['valid']
            start()
            request('/api/assets',expected=401)
            request('/api/auth/login',{'password':password})
            assert asset['id'] in [row['id'] for row in request('/api/assets')]
            assert request('/api/tasks/'+task['id'])['task']['status']=='pending'
            assert late['id'] not in [row['id'] for row in request('/api/notes')]
            assert request('/api/runtime')['requests']['requests']==0
            if args.postgres:
                compose('exec','-T','aegis','python','-c',
                        "from pathlib import Path; assert not list(Path('/app/data').rglob('*.db'))")
            stop()
            result = {'valid':True,'backend':backend,'compose_version':compose_version,
                      'database':database_info,'target_requests':0,
                      'checks':['actual compose config/build/start/health','loopback publication',
                                'nonroot/read-only','setup/auth/native storage/UI','pending unapproved task',
                                'volume and cookie retained after container recreation','online backup',
                                'stopped-app restore against checkpoint','restored cookie rejected/password retained',
                                'post-backup note absent','clean stop'],
                      'network':'ordinary application bridge; no application egress firewall',
                      'database_network':'internal/no published ports' if args.postgres else None,
                      'source_schema_preserved':True if args.postgres else None}
        finally:
            if cleanup_needed:
                progress('Removing only owned Compose project resources')
                compose('down','--volumes','--remove-orphans','--timeout','15',timeout=60)
                for kind in ('container','volume','network'):
                    names = run([kind,'ls','--filter',f'label=com.docker.compose.project={identity}',
                                 '--format','{{.ID}}' if kind=='container' else '{{.Name}}'])
                    assert not names, f'Owned {kind} cleanup incomplete'
                # This explicit tag belongs to this fixture; base images/cache may remain.
                if run(['image','ls','--quiet',image]):
                    run(['image','rm',image])
    result['owned_resources_removed']=True
    print(json.dumps(result))


if __name__=='__main__':
    main()
