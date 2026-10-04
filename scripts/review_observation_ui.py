"""Disposable built-app observation/dependency/next-plan UI fixtures; synthetic metadata, no target execution."""
import argparse
import asyncio
import os
from pathlib import Path
import sys
import tempfile
import time
import html
import shutil
from contextlib import asynccontextmanager
from starlette.routing import Route
from starlette.responses import HTMLResponse, JSONResponse, Response

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from aegis.app import create_app
from aegis.auth import new_user
from aegis.__main__ import AegisServer
from aegis.tool_contracts import contracts_for
from aegis.worker_observations import record_link
from aegis.coverage import slot


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port',type=int,default=8815)
    parser.add_argument('--editor',action='store_true',help='Seed30 extra synthetic selectable assets for dependency editor QA')
    parser.add_argument('--task-fail-flag',type=Path,help='Owned QA flag: while present, task creation POST returns503')
    parser.add_argument('--next-plan',action='store_true',help='Seed synthetic terminal two-Worker proposal evidence; never execute targets')
    parser.add_argument('--next-read-fail-flag',type=Path)
    parser.add_argument('--next-write-fail-flag',type=Path)
    parser.add_argument('--next-write-hold-flag',type=Path)
    parser.add_argument('--dependencies',action='store_true',help='Synthetic pending two-Worker dependency approval fixture')
    parser.add_argument('--fail-flag',type=Path,help='Owned QA flag: while present, only task observation GET returns503')
    parser.add_argument('--worker-process',action='store_true',help='Seed synthetic isolated Worker events for readonly process UI QA')
    parser.add_argument('--worker-fail-flag',type=Path,help='Owned QA flag: while present, Worker process and collection GET return503')
    args=parser.parse_args()
    if not 1<=args.port<=65535:parser.error('port must be1..65535')
    for key in list(os.environ):
        if key.startswith('AEGIS_'):del os.environ[key]
    os.environ['AEGIS_WEB_DIR']=str(ROOT/'web/dist')
    with tempfile.TemporaryDirectory(prefix='aegis-observation-ui-') as temporary:
        app=create_app(Path(temporary),allow_private=False)
        async def frame(request):
            width=request.query_params.get('width','390')
            source=request.query_params.get('source','?page=observations')
            if width not in ('320','390','768') or not source.startswith('?'):
                return JSONResponse({'detail':'Invalid QA frame'},status_code=400)
            return HTMLResponse('<!doctype html><html><body style="margin:0"><iframe title="Responsive observation QA" style="border:0;width:'+width+'px;height:844px" src="/'+html.escape(source+'&qa_frame=1',quote=True)+'"></iframe><button id="measure">너비 검사</button><output id="dimensions" aria-label="너비 측정 결과"></output><script src="/qa-layout.js"></script></body></html>')
        async def layout(request):
            return Response('''document.getElementById('measure').addEventListener('click',()=>{
                const d=document.querySelector('iframe').contentDocument;
                const m=e=>e?{client:e.clientWidth,scroll:e.scrollWidth}:null;
                const overflow=Array.from(d.querySelectorAll('*')).filter(e=>e.clientWidth>0&&e.scrollWidth>e.clientWidth+1).map(e=>({tag:e.tagName,class:e.className,...m(e),minWidth:d.defaultView.getComputedStyle(e).minWidth}));
                document.getElementById('dimensions').textContent=JSON.stringify({document:m(d.documentElement),dialog:m(d.querySelector('[role="dialog"]')),panel:m(d.querySelector('.next-plan')),overflow});
            });''',media_type='application/javascript')
        app.router.routes.insert(0,Route('/qa-layout.js',layout))
        app.router.routes.insert(0,Route('/qa-frame',frame))
        task_posts=0
        next_posts=0
        @app.middleware('http')
        async def failure(request,call_next):
            nonlocal task_posts,next_posts
            if request.method=='GET' and ('/workers/' in request.url.path or request.url.path=='/api/worker-events') and args.worker_fail_flag and args.worker_fail_flag.exists():
                return JSONResponse({'detail':'합성 Worker 과정 조회 실패'},status_code=503)
            if request.url.path.endswith('/next-plan'):
                if request.method=='GET' and args.next_read_fail_flag and args.next_read_fail_flag.exists():
                    return JSONResponse({'detail':'합성 제안 조회 실패'},status_code=503)
                if request.method=='POST':
                    next_posts+=1
                    deadline=time.monotonic()+15
                    while args.next_write_hold_flag and args.next_write_hold_flag.exists() and time.monotonic()<deadline:
                        await asyncio.sleep(.05)
                    if args.next_write_fail_flag and args.next_write_fail_flag.exists():
                        return JSONResponse({'detail':'합성 후속 계획 저장 실패'},status_code=503)
            if request.method=='POST' and request.url.path=='/api/tasks':
                task_posts+=1
                if args.task_fail_flag and args.task_fail_flag.exists():
                    return JSONResponse({'detail':'합성 계획 저장 실패'},status_code=503)
            if request.url.path.startswith('/api/tasks/') and request.url.path.endswith('/observations') and args.fail_flag and args.fail_flag.exists():
                return JSONResponse({'detail':'합성 관찰 조회 실패'},status_code=503)
            response=await call_next(request)
            if request.query_params.get('qa_frame')=='1':
                response.headers['X-Frame-Options']='SAMEORIGIN'
                if 'content-security-policy' in response.headers:
                    response.headers['Content-Security-Policy']=response.headers['Content-Security-Policy'].replace("frame-ancestors 'none'","frame-ancestors 'self'")
            return response
        store=app.state.store
        store.add_user(new_user('fixture-admin','합성 관찰 관리자','admin','observation-ui-fixture-only'))
        asset={'id':'qa-asset','name':'관찰 QA 자산','url':'https://observation-qa.invalid/app/',
               'type':'web','owner':'Synthetic QA','authorized':True,'revision':1,'archived_at':None,'tags':[]}
        task={'id':'qa-source-task','name':'관찰 출처 QA 작업','status':'completed','goal':'Synthetic UI fixture only',
              'created_at':time.time(),'started_at':1.,'finished_at':2.,'approved_at':1.,'done':1,'errors':0,
              'asset_ids':[asset['id']],'scope_snapshot':[asset],'checks':['endpoint_inventory'],
              'tool_contracts':contracts_for(['endpoint_inventory']),'workers':1,'planner':'rules'}
        if args.dependencies or args.next_plan:
            parent={**asset,'id':'qa-parent-asset','name':'선행 검수 자산','url':asset['url']+'parent/'}
            asset['name']='후행 검수 자산'
            task.update(status='pending',approved_at=None,started_at=None,finished_at=None,done=0,
                        asset_ids=[asset['id'],parent['id']],scope_snapshot=[asset,parent],
                        worker_dependencies={asset['id']:[parent['id']]})
            store.put('assets',parent)
        if args.next_plan:
            task.update(status='completed',approved_at=1.,started_at=1.,finished_at=2.,done=2,errors=1,
                        checks=['security_headers','endpoint_inventory'],
                        tool_contracts=contracts_for(['security_headers','endpoint_inventory']))
            store.put('coverage',slot(task,asset,'security_headers',status='failed'))
            store.put('coverage',slot(task,asset,'endpoint_inventory',status='skipped'))
            for check in task['checks']:
                store.put('coverage',slot(task,parent,check,status='completed'))
        store.put_many([('assets',asset),('tasks',task)])
        if args.worker_process:
            store.event('missing-worker-task','합성 원본 없는 Worker 기록','info',
                        {'asset_id':asset['id'],'worker_id':'missing-worker-task:'+asset['id']})
            for i in range(31):
                store.event(task['id'],f'합성 후행 Worker 단계 {i:02d}','info',
                            {'asset_id':asset['id'],'worker_id':task['id']+':'+asset['id']})
            store.event(task['id'],'합성 이전 Worker 기록','info',{'asset_id':asset['id']})
            if args.next_plan:
                store.event(task['id'],'합성 선행 Worker 기록','info',
                            {'asset_id':parent['id'],'worker_id':task['id']+':'+parent['id']})
        for i in range(60):
            record_link(store,task,asset,'endpoint_inventory',asset['url']+f'owned-link-{i:02d}')
        store.put('observations',{'id':'qa-legacy','task_id':task['id'],'asset_id':asset['id'],
                                 'url':asset['url']+'legacy-link','created_at':time.time()})
        store.put('observations',{'id':'qa-missing','task_id':'missing-task','asset_id':asset['id'],
                                 'url':asset['url']+'missing-source','created_at':time.time()})
        if args.editor:
            for i in range(30):
                store.put('assets',{**asset,'id':f'qa-editor-{i:02d}','name':f'편집 검수 {i:02d}',
                                    'url':asset['url']+f'editor-{i:02d}/'})
        original_lifespan=app.router.lifespan_context
        @asynccontextmanager
        async def reviewed_lifespan(application):
            async with original_lifespan(application):yield
            assert store.count('traffic')==0
            assert store.get('tasks',task['id'])['status']==task['status']
            shutil.rmtree(temporary)
            print('Fixture lifespan completed; target requests0; task creation POSTs'+str(task_posts)+'; next-plan POSTs'+str(next_posts)+'; temporary data removed',flush=True)
        app.router.lifespan_context=reviewed_lifespan
        print('Owned observation UI fixture at http://127.0.0.1:'+str(args.port),flush=True)
        AegisServer(app,host='127.0.0.1',port=args.port,log_level='warning',timeout_graceful_shutdown=5).run()


if __name__=='__main__':
    main()
