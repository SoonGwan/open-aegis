"""Check the actual Compose environment model without a Docker daemon or real secrets."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--compose-binary',type=Path,help='Optional standalone official Compose executable')
    args=parser.parse_args()
    command=[str(args.compose_binary.resolve(strict=True))] if args.compose_binary else ['docker','compose']
    source=Path(__file__).resolve().parents[1]
    environment={k:v for k,v in os.environ.items() if not k.startswith(('AEGIS_','COMPOSE_','OWNED_COMPOSE_'))}
    values={
        'AEGIS_SETUP_TOKEN':'owned-compose-config-fixture',
        'AEGIS_PORT':'8799','AEGIS_DATA_DIR':'/wrong-owned-data','AEGIS_WEB_DIR':'/wrong-owned-web',
        'AEGIS_MODEL_DESTINATIONS':json.dumps([{'id':'owned','name':'Owned model',
            'base_env':'OWNED_COMPOSE_MODEL_BASE','key_env':'OWNED_COMPOSE_MODEL_KEY'}]),
        'OWNED_COMPOSE_MODEL_BASE':'https://owned-provider.invalid/v1',
        'OWNED_COMPOSE_MODEL_KEY':'owned-literal-$value',
        'AEGIS_NOTIFICATION_DESTINATIONS':json.dumps([{'id':'owned','name':'Owned webhook',
            'endpoint_env':'OWNED_COMPOSE_WEBHOOK'}]),
        'OWNED_COMPOSE_WEBHOOK':'https://owned-webhook.invalid/events',
        'AEGIS_MCP_CONNECTIONS':'[]','OWNED_COMPOSE_API_CREDENTIAL':'owned-extra-$credential',
    }
    checked=[]
    with tempfile.TemporaryDirectory(prefix='aegis-compose-config-') as folder:
        root=Path(folder)
        shutil.copy2(source/'compose.yml',root/'compose.yml')
        def write(path,data):
            assert all("'" not in v and '\n' not in v for v in data.values())
            path.write_text(''.join(f"{k}='{v}'\n" for k,v in data.items()))
            path.chmod(0o600)
        def model(file=None,extra=None):
            flags=['--env-file',str(file)] if file else []
            result=subprocess.run([*command,'--project-directory',str(root),*flags,
                '-f',str(root/'compose.yml'),'config','--format','json'],
                cwd=root,env={**environment,**(extra or {})},capture_output=True,text=True,timeout=30)
            if result.returncode:raise RuntimeError(f'Owned Compose config failed with exit {result.returncode}; captured output is not published')
            return json.loads(result.stdout)['services']['aegis']
        def check(service):
            actual=service['environment']
            for name in ('AEGIS_MODEL_DESTINATIONS','OWNED_COMPOSE_MODEL_BASE','OWNED_COMPOSE_MODEL_KEY',
                         'AEGIS_NOTIFICATION_DESTINATIONS','OWNED_COMPOSE_WEBHOOK',
                         'AEGIS_MCP_CONNECTIONS','OWNED_COMPOSE_API_CREDENTIAL'):
                # Rendered Compose config escapes literal dollars for safe round trips.
                # The real container rehearsal separately checks the exact environment.
                assert isinstance(actual.get(name),str) and actual[name].replace('$$','$')==values[name],f'Named environment variable missing or altered: {name}'
            assert actual['AEGIS_HOST']=='0.0.0.0' and actual['AEGIS_PORT']=='8787'
            assert actual['AEGIS_DATA_DIR']=='/app/data' and actual['AEGIS_WEB_DIR']=='/app/web/dist'
            assert len(service['ports'])==1 and service['ports'][0]['host_ip']=='127.0.0.1'
            assert service['read_only'] and service['cap_drop']==['ALL']
        custom=root/'custom.env'
        write(custom,{**values,'AEGIS_CONFIG_ENV_FILE':str(custom)})
        check(model(custom));checked.append('explicit named environment file')
        write(root/'.env',values)
        check(model());checked.append('default .env named configuration')
        (root/'.env').unlink()
        legacy=model(extra={'AEGIS_SETUP_TOKEN':values['AEGIS_SETUP_TOKEN']})
        assert legacy['environment']['AEGIS_SETUP_TOKEN']==values['AEGIS_SETUP_TOKEN']
        assert 'OWNED_COMPOSE_MODEL_KEY' not in legacy['environment']
        checked.append('legacy exported setup token without optional file')
    print(json.dumps({'valid':True,'checks':checked,'container_started':False,
        'target_provider_requests':0,'credential_values_published':False,'temporary_environment_removed':True}))


if __name__=='__main__':main()
