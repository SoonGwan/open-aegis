"""Disposable event-progress desktop fixture; no targets or provider calls."""
import argparse
from contextlib import asynccontextmanager
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from aegis.app import create_app
from aegis.auth import new_user
from aegis.__main__ import AegisServer
from aegis.event_planner import STATE_ID,FORMAT,policy_fingerprint


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port',type=int,default=8813)
    parser.add_argument('--state',choices=('current','replay','invalid'),default='current')
    args=parser.parse_args()
    if not 1<=args.port<=65535:parser.error('port must be 1..65535')
    for key in list(os.environ):
        if key.startswith('AEGIS_'):del os.environ[key]
    os.environ['AEGIS_WEB_DIR']=str(ROOT/'web/dist')
    with tempfile.TemporaryDirectory(prefix='aegis-event-progress-ui-') as folder:
        app=create_app(folder,allow_private=False);store=app.state.store
        store.add_user(new_user('admin','Owned progress reviewer','admin','owned-event-progress-password'))
        original=app.router.lifespan_context
        @asynccontextmanager
        async def lifespan(application):
            async with original(application):
                app.state.event_planner.close()
                for i in range(37):store.event(None,'Synthetic progress fixture '+str(i))
                latest=store.events(limit=1000)[-1]['seq']
                state={'id':STATE_ID,'format':FORMAT,'after':0,'fanout':None,
                       'policy_fingerprint':policy_fingerprint(app.state.engine.policy.public())}
                if args.state=='replay':state.update(after=latest,policy_fingerprint='old-policy')
                if args.state=='invalid':state['after']=latest+1000
                store.put('planner_state',state)
                print(json.dumps({'synthetic_fixture':True,'state':args.state,'target_execution':False}),flush=True)
                yield
        app.router.lifespan_context=lifespan
        try:AegisServer(app,host='127.0.0.1',port=args.port,access_log=False,timeout_graceful_shutdown=5).run()
        finally:print(json.dumps({'target_traffic':store.count('traffic'),'tasks':store.count('tasks'),'synthetic_fixture_removed_on_exit':True}),flush=True)


if __name__=='__main__':
    try:main()
    except KeyboardInterrupt:raise SystemExit(130)
