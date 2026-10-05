"""Coverage meaning across compact task projection and latest-result lookup."""
import pytest
from aegis import coverage
from aegis.postgres_coverage import latest_summary as native_summary
from aegis.postgres_bootstrap import initialize
from aegis.postgres_store import PostgresStore
from aegis.store import Store
from tests.test_postgres_transfer import postgres,schema


@pytest.fixture(params=('sqlite','postgres'))
def backend(request,tmp_path):
    if request.param=='sqlite':return Store(tmp_path/'fixture.db'),coverage.latest_summary
    cluster=request.getfixturevalue('postgres');name=schema();initialize(cluster['dsn'],name)
    return PostgresStore(cluster['dsn'],name),native_summary


def summary(backend,ids=None):
    store,query=backend
    with store.read_transaction() as db:return query(db,ids)


def task(id,assets,checks,approved=1,**extra):
    return {'id':id,'status':'completed','created_at':1,'approved_at':approved,
            'scope_snapshot':assets,'checks':checks,**extra}


def proof(plan,asset,check,status='completed',**extra):
    return {'id':f"{plan['id']}:{asset['id']}:{check}",'task_id':plan['id'],
            'asset_id':asset['id'],'check':check,'status':status,**extra}


def test_latest_approval_tie_revision_and_wrong_result_source(backend):
    store,_=backend
    a={'id':'a','revision':2};b={'id':'b','revision':1};archived={'id':'archived','archived_at':99}
    old=task('old',[{**a,'revision':1},b],['security_headers','cookie_policy'],10)
    current=task('current',[a,b],['security_headers'],20,created_at=50)
    tie=task('tie',[a],['security_headers'],20,created_at=2,diagnostic_padding='한글🙂'*3000)
    pending=task('pending',[a,b],['security_headers'],None,status='pending',created_at=999)
    observed=task('observed',[a],['security_headers'],999,observation_execution={'urls':[]})
    records=[('assets',x) for x in (a,b,archived)]
    records += [('tasks',x) for x in (old,current,tie,pending,observed)]
    records += [('coverage',proof(old,x,c)) for x in (a,b) for c in old['checks']]
    records += [('coverage',proof(current,b,'security_headers',asset_id='a')),
                ('coverage',proof(tie,a,'security_headers')),
                ('coverage',proof(observed,a,'security_headers','failed'))]
    store.put_many(records)
    result=summary(backend)
    assert result['expected']==12 and result['completed']==2
    assert result['counts']['stale']==1 and result['counts']['not_recorded']==1
    assert result['counts']['not_started']==8 and result['covered_assets']==2
    assert result['fully_covered_assets']==0
    selected=summary(backend,['a'])
    assert selected['expected']==6 and selected['completed']==1
    assert selected['assets']['a']['counts']['stale']==1
    assert summary(backend,[])['expected']==0 and summary(backend,['archived'])['expected']==0


def test_goal_objectives_and_selected_cells_intersect_without_overwriting_others(backend):
    store,_=backend;a={'id':'a'};b={'id':'b'};checks=['security_headers','cookie_policy']
    old=task('old',[a,b],checks,1)
    selected=task('selected',[a,b],checks,2,
        goal_plan={'execution':'approved','decomposition':{'objectives':[
            {'asset_ids':['a'],'checks':['security_headers']},
            {'asset_ids':['b'],'checks':['cookie_policy']}]}},
        goal_selection={'cells':[{'asset_id':'a','check':'security_headers'}]})
    records=[('assets',a),('assets',b),('tasks',old),('tasks',selected)]
    records += [('coverage',proof(old,x,c,'future' if x==a and c=='cookie_policy' else 'completed')) for x in (a,b) for c in checks]
    records += [('coverage',proof(selected,x,c,'failed')) for x in (a,b) for c in checks]
    store.put_many(records)
    result=summary(backend)
    assert result['expected']==12 and result['completed']==2
    assert result['counts']['failed']==1 and result['counts']['not_recorded']==1
    assert result['counts']['not_started']==8
    assert summary(backend,['a'])['completed']==0
    assert summary(backend,['b'])['completed']==2


def test_legacy_timestamp_fallback_and_unreferenced_archived_history(backend):
    store,_=backend;a={'id':'a'};archived={'id':'archived','archived_at':99}
    queued=task('queued',[a],['security_headers','cookie_policy'],10,status='queued')
    legacy=task('legacy',[a],['cookie_policy'],None,created_at=20)
    irrelevant=task('irrelevant',[archived],['security_headers'],None,created_at='legacy-invalid-time')
    store.put_many([('assets',a),('assets',archived),('tasks',queued),('tasks',legacy),('tasks',irrelevant),
        ('coverage',proof(queued,a,'security_headers','future')),
        ('coverage',proof(legacy,a,'cookie_policy','interrupted'))])
    result=summary(backend)
    assert result['expected']==6 and result['completed']==0
    assert result['counts']['not_recorded']==1 and result['counts']['interrupted']==1
    assert result['counts']['not_started']==4


def test_sqlite_without_materialization_hint_preserves_results(tmp_path,monkeypatch):
    store=Store(tmp_path/'compat.db');a={'id':'a'};plan=task('one',[a],['security_headers'])
    store.put_many([('assets',a),('tasks',plan),('coverage',proof(plan,a,'security_headers'))])
    backend=(store,coverage.latest_summary);expected=summary(backend,['a'])
    monkeypatch.setattr(coverage.sqlite3,'sqlite_version_info',(3,34,0))
    assert summary(backend,['a'])==expected


@pytest.mark.parametrize('scalar_scope,scalar_checks',[(False,False),(False,True),(True,False),(True,True)])
def test_sqlite_retains_json_each_scalar_path_semantics(tmp_path,scalar_scope,scalar_checks):
    import json
    store=Store(tmp_path/'scalar.db');a={'id':'a'}
    plan=task('legacy',json.dumps(a) if scalar_scope else [a],
              'security_headers' if scalar_checks else ['security_headers'])
    store.put_many([('assets',a),('tasks',plan),('coverage',proof(plan,a,'security_headers'))])
    result=summary((store,coverage.latest_summary))
    assert result['completed']==1 and result['counts']['not_started']==5
