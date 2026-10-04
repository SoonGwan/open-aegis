"""Build and rehearse an owned Docker image/volume; never approve target execution."""
import argparse
from http.cookiejar import CookieJar
import json
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import time
from urllib.error import HTTPError
from urllib.request import Request, build_opener, HTTPCookieProcessor, ProxyHandler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--postgres-extra', action='store_true', help='Build with the locked native PostgreSQL driver; HTTP rehearsal still uses SQLite')
    args = parser.parse_args()
    docker = shutil.which('docker')
    if not docker:
        parser.error('Docker executable is required; no container verification was performed')
    root = Path(__file__).resolve().parents[1]
    identity = 'open-aegis-review-'+secrets.token_hex(8)
    image, volume, network, container = identity+':local', identity+'-data', identity+'-network', identity+'-server'
    password, token = secrets.token_urlsafe(24), secrets.token_urlsafe(24)
    resources = []

    def run(*arguments, timeout=60, expected=0):
        result = subprocess.run([docker,*map(str,arguments)], cwd=root, capture_output=True, text=True, timeout=timeout)
        if result.returncode != expected:
            raise RuntimeError(f'Docker operation failed (exit {result.returncode}); no success evidence recorded')
        return result.stdout.strip()

    def state():
        return json.loads(run('inspect','--format','{{json .State}}',container))

    def endpoint():
        address = run('port',container,'8787/tcp').splitlines()
        if len(address) != 1 or not re.fullmatch(r'127\.0\.0\.1:[0-9]+',address[0]):
            raise RuntimeError('Review container must publish exactly one loopback port')
        return 'http://'+address[0]

    def wait_healthy():
        deadline = time.monotonic()+60
        while True:
            current=state()
            if not current['Running']:
                raise RuntimeError('Review server exited during startup')
            if current.get('Health',{}).get('Status') == 'healthy':
                return
            if time.monotonic() >= deadline:
                raise RuntimeError('Review server health timed out')
            time.sleep(.2)

    def stop():
        run('stop','--time','15',container,timeout=25)
        current=state()
        if current['Running'] or current['ExitCode'] not in (0,143):
            raise RuntimeError('Container did not stop cleanly')

    try:
        run('info','--format','{{.ServerVersion}}')
        resources.append(('image',image))
        run('build','--build-arg',f'AEGIS_INSTALL_POSTGRES={int(args.postgres_extra)}','--tag',image,'.',timeout=900)
        run('volume','create','--label',f'open-aegis.review={identity}',volume)
        resources.append(('volume',volume))
        run('network','create','--internal','--label',f'open-aegis.review={identity}',network)
        resources.append(('network',network))
        resources.append(('container',container))
        run('run','--detach','--name',container,'--label',f'open-aegis.review={identity}',
            '--network',network,'--publish','127.0.0.1::8787','--read-only',
            '--tmpfs','/tmp:rw,nosuid,noexec,size=64m','--cap-drop','ALL',
            '--security-opt','no-new-privileges:true','--health-interval','1s',
            '--mount',f'type=volume,src={volume},dst=/app/data',
            '--env',f'AEGIS_SETUP_TOKEN={token}','--env','AEGIS_ALLOWED_HOSTS=localhost,127.0.0.1',image)
        wait_healthy()
        assert int(run('exec',container,'id','-u')) == 10001
        configuration=json.loads(run('inspect','--format','{{json .HostConfig}}',container))
        assert configuration['ReadonlyRootfs'] and 'ALL' in configuration['CapDrop']
        assert 'no-new-privileges:true' in configuration['SecurityOpt']
        assert run('network','inspect','--format','{{.Internal}}',network)=='true'
        run('exec',container,'python','-c',
            "import errno; from pathlib import Path; p=Path('/app/review-write');\ntry: p.write_text('fixture')\nexcept OSError as e: assert e.errno==errno.EROFS\nelse: raise AssertionError('Root filesystem writable')\np=Path('/app/data/review-write');p.write_text('fixture');assert p.read_text()=='fixture';p.unlink()")
        run('exec',container,'python','-m','pip','check')
        if args.postgres_extra:
            run('exec',container,'python','-c',"import psycopg; assert psycopg.__version__=='3.3.6'")
        base=endpoint()
        anonymous=build_opener(ProxyHandler({}))
        authenticated=build_opener(ProxyHandler({}),HTTPCookieProcessor(CookieJar()))

        def request(path, body=None, expected=200, opener=authenticated):
            request=Request(base+path, data=None if body is None else json.dumps(body).encode(),
                            headers={} if body is None else {'Content-Type':'application/json'})
            try: response=opener.open(request,timeout=5)
            except HTTPError as exc: response=exc
            with response:
                if response.code != expected:raise RuntimeError(f'HTTP {path} returned {response.code}, expected {expected}')
                raw=response.read()
                return json.loads(raw) if 'application/json' in response.headers.get('Content-Type','') else raw.decode()

        request('/api/assets',expected=401,opener=anonymous)
        request('/api/auth/setup',{'password':password,'setup_token':token})
        html=request('/')
        bundles=re.findall(r'(?:src|href)="(/assets/[^"\s]+)"',html)
        assert bundles and any(path.endswith('.js') for path in bundles)
        for path in bundles:assert request(path)
        asset=request('/api/assets',{'name':'Owned synthetic container fixture','url':'https://container-fixture.invalid/','authorized':True})
        task=request('/api/tasks',{'name':'Never-approved fixture','asset_ids':[asset['id']]})
        assert task['status']=='pending' and task['approved_at'] is None
        archive='/app/data/review-backup.db'
        run('exec',container,'aegis-backup','--backend','sqlite','--source','/app/data/aegis.db','--output',archive)
        capture=json.loads(run('exec',container,'aegis-checkpoint','--backend','sqlite','--source','/app/data/aegis.db','--destination','/app/data/checkpoints'))
        assert capture['created']
        assert not json.loads(run('exec',container,'aegis-checkpoint','--backend','sqlite','--source','/app/data/aegis.db','--destination','/app/data/checkpoints'))['created']
        late=request('/api/notes',{'title':'After backup','content':'Synthetic only'})
        stop()
        run('start',container);wait_healthy();base=endpoint()
        assert asset['id'] in [row['id'] for row in request('/api/assets')]
        assert request('/api/tasks/'+task['id'])['task']['status']=='pending'
        assert request('/api/runtime')['requests']['requests']==0
        stop()
        maintenance=[ 'run','--network','none','--read-only','--tmpfs','/tmp:rw,nosuid,noexec,size=64m',
                     '--cap-drop','ALL','--security-opt','no-new-privileges:true',
                     '--mount',f'type=volume,src={volume},dst=/app/data',image]
        def maintain(*arguments):
            name=identity+'-maintenance-'+secrets.token_hex(4)
            resources.append(('container',name))
            output=run(maintenance[0],'--name',name,*maintenance[1:],*arguments)
            run('rm',name)
            resources.remove(('container',name))
            return output
        restored=json.loads(maintain('aegis-restore','--backend','sqlite','--source',archive,'--destination','/app/data/aegis.db'))
        assert restored['sessions_revoked']
        maintain('aegis-verify-audit','--backend','sqlite','--source','/app/data/aegis.db')
        run('start',container);wait_healthy();base=endpoint()
        request('/api/assets',expected=401)
        request('/api/auth/login',{'password':password})
        assert asset['id'] in [row['id'] for row in request('/api/assets')]
        assert request('/api/tasks/'+task['id'])['task']['status']=='pending'
        assert late['id'] not in [row['id'] for row in request('/api/notes')]
        assert request('/api/runtime')['requests']['requests']==0
        stop()
        result={'valid':True,'postgres_driver':args.postgres_extra,'http_backend':'sqlite','target_requests':0,
                'checks':['image build','nonroot/read-only/isolated network','actual health','UI bundles','setup/auth',
                          'volume data/cookie retained across restart','checkpoint capture/repeat','offline restore',
                          'restored session rejected and password retained','pending task without execution','clean stop']}
    finally:
        failures=[]
        for kind,name in reversed(resources):
            command={'container':['rm','--force',name],'network':['network','rm',name],
                     'volume':['volume','rm',name],'image':['image','rm',name]}[kind]
            cleaned=subprocess.run([docker,*command],cwd=root,capture_output=True,text=True,timeout=60)
            if cleaned.returncode and kind!='image':failures.append(kind)
        if failures:raise RuntimeError('Owned Docker resource cleanup failed: '+','.join(failures))
    print(json.dumps(result))


if __name__ == '__main__':
    main()
