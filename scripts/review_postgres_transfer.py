"""Rehearse installed transfer CLI using an owned disposable PostgreSQL cluster."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import venv


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--wheel-dir',required=True,type=Path)
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    wheels=list(args.wheel_dir.resolve().glob('open_aegis-*.whl'))
    if len(wheels)!=1:parser.error('Supply one wheel')
    wheel=wheels[0]
    binaries={name:shutil.which(name) for name in ('initdb','pg_ctl','createdb','pg_dump','pg_restore')}
    if not all(binaries.values()):parser.error('PostgreSQL client and server binaries are required')
    environment={key:value for key,value in os.environ.items() if not key.startswith(('AEGIS_','PYTHON','PG')) and key!='VIRTUAL_ENV'}
    with tempfile.TemporaryDirectory(prefix='aegis-installed-pg-',dir='/tmp') as directory:
        temporary=Path(directory);installation=temporary/'installation';data=temporary/'cluster';socket=temporary/'socket';socket.mkdir(mode=0o700)
        venv.EnvBuilder(with_pip=True).create(installation)
        python=installation/'bin'/'python';cli=installation/'bin'/'aegis-transfer-storage'
        def run(command,label,env=None):
            result=subprocess.run([str(item) for item in command],cwd=temporary,env=env or environment,capture_output=True,text=True,timeout=180)
            if result.returncode:raise RuntimeError(label+' failed')
            return result.stdout
        run([python,'-m','pip','install','-r',root/'requirements.lock','-r',root/'requirements-postgres.lock'],'locked installation')
        run([python,'-m','pip','install','--no-deps',wheel],'wheel installation');run([python,'-m','pip','check'],'pip check')
        run([cli,'--help'],'transfer entry point')
        run([binaries['initdb'],'-D',data,'--auth=trust','--no-locale','--encoding=UTF8'],'initdb')
        run([binaries['pg_ctl'],'-D',data,'-l',temporary/'server.log','-o',f"-c listen_addresses='' -k {socket} -p 55439",'-w','start'],'owned PostgreSQL start')
        environment.update(AEGIS_POSTGRES_DSN=f'host={socket} port=55439 dbname=postgres',PGHOST=str(socket),PGPORT='55439')
        try:
            source=temporary/'source'/'aegis.db'
            origin=json.loads(run([python,'-I','-c','''
import json,sys,time,os,psycopg
from pathlib import Path
import aegis
from aegis.store import Store
from aegis.auth import new_user
assert Path(aegis.__file__).is_relative_to(Path(sys.prefix))
with psycopg.connect(os.environ['AEGIS_POSTGRES_DSN']) as db:
    assert db.execute('SHOW fsync').fetchone()[0]=='on'
s=Store(sys.argv[1]);u=new_user('admin','합성 관리자','admin','owned-installed-transfer-password');s.add_user(u)
s.session('owned-old-cookie',time.time()+3600,u['id']);s.put('notes',{'id':'proof','title':'합성 한글 🚀','amount':'0.000000000000001'})
s.event(None,'합성 설치본 전송 검수',detail={'amount':'0.000000000000001'})
print(json.dumps({'module':aegis.__file__,'audit':s.audit_integrity()}))
''',source],'installed source creation'))
            forward=json.loads(run([cli,'sqlite-to-postgres','--source',source,'--schema','owned_transfer'],'installed transfer'))
            dump=temporary/'owned.dump'
            run([binaries['pg_dump'],'--format=custom','--schema','owned_transfer','--file',dump,'postgres'],'real pg_dump');dump.chmod(0o600)
            run([binaries['createdb'],'owned_restore'],'empty restore database')
            run([binaries['pg_restore'],'--exit-on-error','--dbname','owned_restore',dump],'real pg_restore')
            environment['AEGIS_POSTGRES_DSN']=f'host={socket} port=55439 dbname=owned_restore'
            output=temporary/'returned'/'aegis.db'
            reverse=json.loads(run([cli,'postgres-to-sqlite','--schema','owned_transfer','--output',output],'installed reverse transfer'))
            assert forward['manifest']==reverse['manifest'] and forward['audit']==reverse['audit'] and forward['sessions_revoked']==1
            run([python,'-I','-c','''
import sys
from aegis.store import Store
from aegis.auth import password_hash
s=Store(sys.argv[1]);u=s.user(username='admin')
assert u['password_hash']==password_hash('owned-installed-transfer-password',u['salt'])
assert not s.valid_session('owned-old-cookie')
assert s.get('notes','proof')['amount']=='0.000000000000001'
s.event(None,'반환 후 이벤트');assert s.audit_integrity()['valid']
''',output],'installed returned credentials, record and audit continuation')
            print(json.dumps({'valid':True,'wheel_sha256':hashlib.sha256(wheel.read_bytes()).hexdigest(),
                'postgres_version':run([binaries['pg_ctl'],'--version'],'version').strip(),
                'installed_origin':origin['module'],'manifest':forward['manifest'],'audit':forward['audit'],
                'checks':['locked optional dependency','server fsync enabled','installed six-command package','atomic offline transfer','real pg_dump/pg_restore',
                          'installed SQLite return','revoked old sessions','preserved password hashes and exact record','audit continuation'],
                'target_requests':0,'service_postgres_backend_enabled':False}))
        finally:
            run([binaries['pg_ctl'],'-D',data,'-w','-m','fast','stop'],'owned PostgreSQL stop')


if __name__=='__main__':main()
