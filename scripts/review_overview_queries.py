"""Measure overview query components on owned synthetic retained task history.

No HTTP targets or real workspace. Native PostgreSQL uses a disposable Unix-only
cluster. Measurements do not certify production latency or a memory limit.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import statistics
import sqlite3
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from aegis.store import Store
from aegis.http_queries import SQLiteHTTP,PostgresHTTP
from scripts.review_execution_load import owned_postgres
from scripts.review_resource_load import bounded_int


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tasks',type=bounded_int(1,5000),default=2250)
    parser.add_argument('--padding-bytes',type=bounded_int(0,16384),default=8192)
    parser.add_argument('--postgres',action='store_true')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    environment={key:value for key,value in os.environ.items() if not key.startswith(('AEGIS_','PG')) and key not in ('PYTHONPATH','PYTHONHOME')}
    result={'valid':False,'backend':'postgres' if args.postgres else 'sqlite',
        'synthetic_tasks':args.tasks,'unused_padding_bytes_per_task':args.padding_bytes,
        'python':sys.version.split()[0],'sqlite_version':sqlite3.sqlite_version}
    fingerprint=hashlib.sha256()
    for path in sorted((ROOT/'aegis').rglob('*.py')):
        fingerprint.update(path.relative_to(ROOT).as_posix().encode());fingerprint.update(path.read_bytes())
    result['source_sha256']=fingerprint.hexdigest()
    with tempfile.TemporaryDirectory(prefix='aegis-overview-query-',dir='/tmp') as folder:
        root=Path(folder)
        with owned_postgres(root,args.postgres,environment) as (_,dsn):
            if args.postgres:
                from aegis.postgres_store import PostgresStore
                store=PostgresStore(dsn+" options='-c statement_timeout=15000'",'owned_execution_load');queries=PostgresHTTP(store)
            else:store=Store(root/'fixture.db');queries=SQLiteHTTP(store)
            asset={'id':'owned-a','name':'Synthetic retained history','url':'https://owned.invalid/',
                'authorized':True,'revision':1,'created_at':1,'authorization_rules':[]}
            checks=['security_headers','cookie_policy','endpoint_inventory']
            records=[('assets',asset)]
            for index in range(args.tasks):
                task={'id':f't-{index}','name':f'Synthetic task {index}','created_at':index+1,
                    'approved_at':index+1,'status':'completed','scope_snapshot':[asset],
                    'checks':checks,'asset_ids':[asset['id']],'done':1,'errors':0,
                    'diagnostic_padding':'x'*args.padding_bytes}
                records.append(('tasks',task))
                for check in checks:
                    records.append(('coverage',{'id':f"{task['id']}:{asset['id']}:{check}",
                        'task_id':task['id'],'asset_id':asset['id'],'asset_revision':1,
                        'check':check,'status':'completed','created_at':index+1}))
            store.put_many(records)
            operations={
                'tasks_page':lambda:store.page('tasks',limit=100),
                'findings_page':lambda:store.page('findings',limit=100,compact_findings=True),
                'assets_page_with_coverage':lambda:store.page('assets',archived=False,limit=100),
                'coverage_page':lambda:store.page('coverage',limit=100),
                'overview_coverage_and_severity':queries.overview_summary,
                'task_counts':lambda:[store.count('tasks'),store.count('tasks',statuses=['running','queued','stopping']),store.count('tasks',statuses=['pending'])],
            }
            timings={}
            for label,operation in operations.items():
                samples=[]
                for _ in range(5):
                    start=time.monotonic();value=operation();samples.append(time.monotonic()-start)
                if label=='overview_coverage_and_severity':
                    summary=value[0]
                    assert summary['completed']==3 and summary['expected']==6
                    result['coverage_summary']=summary
                timings[label]={'samples_seconds':samples,'median_seconds':statistics.median(samples)}
            result.update(valid=True,component_timings=timings,
                limitation='Synthetic retained task history, one asset and no findings; excludes HTTP, concurrent execution and real target validation.')
    result['temporary_resources_removed']=True
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,indent=2))
    print(json.dumps(result))


if __name__=='__main__':main()
