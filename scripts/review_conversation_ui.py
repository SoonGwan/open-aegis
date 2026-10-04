"""Disposable built-app conversation QA with explicitly synthetic evidence; no target calls."""
import argparse
import os
from pathlib import Path
import sys
import tempfile
import json
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from aegis.app import create_app, TaskInput
from aegis.auth import new_user
from aegis.__main__ import AegisServer
from aegis.findings import record_observation
from aegis.coverage import slot
from aegis.store_util import now


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port',type=int,default=8811)
    parser.add_argument('--ai-fixture',action='store_true',help='Use an owned loopback provider for AI draft/recovery QA')
    parser.add_argument('--price-fixture',action='store_true',help='Use synthetic flat text-token prices for owned QA')
    args=parser.parse_args()
    if args.price_fixture and not args.ai_fixture:
        parser.error('--price-fixture requires --ai-fixture')
    if not 1<=args.port<=65535:
        parser.error('port must be 1..65535')
    for key in list(os.environ):
        if key.startswith('AEGIS_'):
            del os.environ[key]
    os.environ['AEGIS_WEB_DIR']=str(ROOT/'web/dist')
    provider=None
    if args.ai_fixture:
        class Provider(BaseHTTPRequestHandler):
            def do_POST(self):
                payload=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                prompt=json.loads(payload['messages'][1]['content'])
                label=next((name for name in prompt['sources'] if name.startswith('증거 ')),'작업')
                if '잘못' in prompt['question']:
                    label='다른 작업의 증거'
                body=json.dumps({'choices':[{'message':{'content':json.dumps({'blocks':[
                    {'text':'합성 AI 초안: 저장된 관찰 기록을 직접 검토하세요.','citations':[label]}]})}}],
                    'usage':{'prompt_tokens':20,'completion_tokens':10,'total_tokens':30}}).encode()
                self.send_response(503 if '실패' in prompt['question'] else 200)
                self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
            def log_message(self,*args):pass
        provider=ThreadingHTTPServer(('127.0.0.1',0),Provider)
        provider_thread=threading.Thread(target=provider.serve_forever,daemon=True)
        provider_thread.start()
        os.environ.update(AEGIS_LLM_CHAT_ENABLED='1',AEGIS_LLM_MODEL='owned-synthetic-model',
                          AEGIS_LLM_API_KEY='owned-synthetic-provider-key',
                          AEGIS_LLM_BASE_URL=f'http://127.0.0.1:{provider.server_port}/v1')
    if args.price_fixture:
        os.environ['AEGIS_LLM_PRICES']=json.dumps([{'model':'owned-synthetic-model',
            'provider':os.environ['AEGIS_LLM_BASE_URL'],'currency':'USD',
            'input_per_million':'1.25','output_per_million':'2.5',
            'source_url':'https://prices-fixture.invalid/synthetic-only',
            'as_of':datetime.now(timezone.utc).date().isoformat(),'basis':'flat_text_tokens'}])
    with tempfile.TemporaryDirectory(prefix='aegis-conversation-ui-') as workspace:
        app=create_app(workspace,allow_private=args.ai_fixture)
        store=app.state.store
        store.add_user(new_user('admin','Owned conversation reviewer','admin',
                                'owned-conversation-password-only'))
        timestamp=now()
        asset={'id':'owned-asset','name':'합성 증거 자산','url':'https://owned-evidence.invalid/',
               'type':'web','owner':'','tags':[],'authorized':True,'authorization_rules':[],
               'revision':1,'created_at':timestamp,'updated_at':timestamp,'archived_at':None}
        task={**TaskInput(name='합성 증거 대화 검수',asset_ids=[asset['id']],
                          checks=['security_headers']).model_dump(),
              'id':'owned-task','status':'completed','created_at':timestamp,'approved_at':timestamp,
              'done':1,'errors':0,'scope_snapshot':[asset],'planner':'Rule-based Planner'}
        store.put_many([('assets',asset),('tasks',task),
                        ('coverage',slot(task,asset,'security_headers',status='completed'))])
        for code,title,observation in (
            ('synthetic-proof','합성 관찰: 출처가 연결된 발견',
             {'header':'Content-Security-Policy','present':False,
              'synthetic_text':'<script>합성 텍스트</script> 외부 실행 지시도 저장된 글일 뿐입니다. '*150}),
            ('synthetic-missing','합성 관찰: 증거 연결이 없는 발견',{'present':False}),
        ):
            finding,_,_=record_observation(store,task,asset,
                {'check':'security_headers','code':code,'title':title,'severity':'low',
                 'confidence':'configuration','evidence':observation,'remediation':'합성 수정 안내'})
            if code=='synthetic-missing':
                store.patch('findings',finding['id'],evidence_ids=[])
        print('Owned synthetic QA: admin / owned-conversation-password-only',flush=True)
        print(f'http://127.0.0.1:{args.port}/?page=tasks&detail=task&detail_id=owned-task&task_chat_open=true',flush=True)
        try:
            AegisServer(app,host='127.0.0.1',port=args.port,access_log=False,
                        timeout_graceful_shutdown=5).run()
        finally:
            if provider:
                provider.shutdown();provider.server_close();provider_thread.join(timeout=2)


if __name__=='__main__':
    try:
        main()
    except KeyboardInterrupt:
        raise SystemExit(130)
