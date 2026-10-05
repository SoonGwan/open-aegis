"""Task-local link metadata; reading an observation never grants execution rights."""
import hashlib
import json
import math
from contextlib import nullcontext

from .audit import hexadecimal
from .network import in_scope
from .store import now

FORMAT = 'aegis-worker-observation-v1'


def observation_id(task_id, asset_id, check, url):
    payload=json.dumps([task_id,asset_id,check,url],ensure_ascii=False,separators=(',',':')).encode()
    return hashlib.sha256(payload).hexdigest()


def record_link(store, task, asset, check, url, *, connection=None):
    tool=next(tool for tool in task['tool_contracts']['checks'] if tool['id']==check)
    record={'id':observation_id(task['id'],asset['id'],check,url), 'format':FORMAT,
            'asset_id':asset['id'], 'task_id':task['id'], 'worker_id':task['id']+':'+asset['id'],
            'check':check, 'tool_version':tool['version'], 'url':url, 'scope_url':asset['url'], 'scope_revision':asset.get('revision',1),
            'package_sha256':task['tool_contracts']['package_sha256'], 'created_at':now(), 'verified':False}
    store.put_many([('observations', record)], connection=connection)
    return record


def provenance(record, task):
    """Consistency with stored approval metadata, not authentication of its contents."""
    unmatched={'status':'unconfirmed','reason':'저장된 승인 범위와 관찰 출처의 일치를 확인할 수 없습니다.'}
    if not isinstance(task,dict) or not isinstance(record,dict):return unmatched
    if type(task.get('id')) is not str or type(record.get('asset_id')) is not str:return unmatched
    if type(task.get('checks')) is not list:return unmatched
    timestamp=record.get('created_at')
    if type(timestamp) not in (int,float) or not math.isfinite(timestamp) or timestamp<0:return unmatched
    approved=task.get('approved_at')
    if type(approved) not in (int,float) or not math.isfinite(approved) or approved<=0:return unmatched
    scopes=task.get('scope_snapshot')
    if type(scopes) is not list:return unmatched
    assets=[a for a in scopes if type(a) is dict and a.get('id')==record.get('asset_id')]
    if len(assets)!=1:return unmatched
    asset=assets[0];contract=task.get('tool_contracts')
    if type(asset.get('url')) is not str or not asset['url'] or len(asset['url'])>2000:return unmatched
    if type(contract) is not dict or contract.get('format')!='aegis-tools-v1' or not hexadecimal(contract.get('package_sha256'),64):return unmatched
    tools=contract.get('checks')
    if type(tools) is not list:return unmatched
    declarations=[tool for tool in tools if type(tool) is dict and tool.get('id')==record.get('check')]
    if len(declarations)!=1:return unmatched
    tool=declarations[0]
    if (type(tool.get('version')) is not int or tool['version']<1 or tool.get('method')!='GET'
        or type(tool.get('permissions')) is not list or 'observe-links' not in tool['permissions']
        or type(record.get('tool_version')) is not int or record['tool_version']!=tool['version']):return unmatched
    check=record.get('check');url=record.get('url');revision=record.get('scope_revision')
    if (record.get('format')!=FORMAT or record.get('task_id')!=task.get('id')
        or check!='endpoint_inventory' or check not in task.get('checks',[])
        or record.get('worker_id')!=task['id']+':'+asset['id']
        or type(revision) is not int or revision<1 or revision!=asset.get('revision',1)
        or record.get('scope_url')!=asset.get('url') or record.get('package_sha256')!=contract['package_sha256']
        or type(url) is not str or not url or len(url)>2000 or record.get('verified') is not False):
        return unmatched
    try:
        if not in_scope(url,asset['url']):return unmatched
    except (ValueError,TypeError):return unmatched
    if record.get('id')!=observation_id(task['id'],asset['id'],check,url):return unmatched
    return {'status':'matched','reason':'작업·Worker·도구·승인 범위와 코드 지문 메타데이터가 일치합니다.'}


def task_page(store, task_id, *, connection=None, **options):
    with (nullcontext(connection) if connection is not None else store.read_transaction()) as db:
        task=store.get('tasks',task_id,connection=db)
        if task is None:raise LookupError('작업이 없습니다.')
        result=store.page('observations',filters={'task_id':task_id},connection=db,**options)
        for item in result['items']:item['provenance']=provenance(item,task)
        return result
