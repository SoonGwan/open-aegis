"""A bounded graph of stored references for one asset and one validation plan."""
import json
from .checks import CATALOG
from .coverage import iter_task_rows
from .graph_queries import SQLiteGraph, PostgresGraph


class GraphNotFound(ValueError):
    pass


def build_graph(store, asset_id, task_id=None, *, check=None, severity=None, status=None,
                limit=10, offset=0, snapshot=None):
    if not 1 <= limit <= 25 or offset < 0 or (snapshot is not None and snapshot < 0):
        raise ValueError("Invalid graph page")
    nodes, edges = [], []
    node_ids = set()
    def node(kind, record_id, label, data):
        id = f'{kind}:{record_id}'
        if id not in node_ids:
            nodes.append({'id': id, 'kind': kind, 'record_id': record_id, 'label': label, 'data': data})
            node_ids.add(id)
        return id
    def edge(source, target, relation):
        edges.append({'id': f'{source}>{target}:{relation}', 'source': source, 'target': target, 'relation': relation})
    with store.read_transaction() as db:
        queries=PostgresGraph(db) if getattr(store,'backend',None)=='postgres' else SQLiteGraph(db)
        def get(kind,id):return store.get(kind,id,connection=db)
        asset = get('assets', asset_id)
        if not asset:
            raise GraphNotFound('자산이 없습니다.')
        public_asset = {key: asset.get(key) for key in ('id', 'name', 'url', 'owner', 'revision', 'archived_at')}
        root = node('asset', asset_id, asset['name'], public_asset)
        if task_id:
            task = get('tasks', task_id)
        else:
            task = queries.latest_task(asset_id)
        context = None
        result = {'asset': public_asset, 'task': context, 'nodes': nodes, 'edges': edges,
                  'findings': {'total': 0, 'limit': limit, 'offset': offset, 'snapshot': snapshot or 0, 'has_more': False},
                  'limits': {'evidence_per_finding': 2, 'endpoints': 10},
                  'omitted': {'evidence': 0, 'endpoints': 0, 'invalid_evidence': 0}}
        if task is None:
            if task_id:
                raise GraphNotFound('작업이 없습니다.')
            return result
        scope = next((a for a in task.get('scope_snapshot', []) if a['id'] == asset_id), None)
        if scope is None:
            raise GraphNotFound('이 자산이 포함된 작업이 아닙니다.')
        context = {key: task.get(key) for key in ('id', 'name', 'status', 'created_at', 'approved_at')}
        context['scope_revision'] = scope.get('revision', 1)
        context['scope_url'] = scope.get('url')
        result['task'] = context
        task_node = node('task', task['id'], task['name'], context)
        edge(root, task_node, 'scope')
        names = {c['id']: c['name'] for c in CATALOG}
        check_nodes = {}
        # One asset graph must not read every other asset's coverage matrix.
        selected={**task,'scope_snapshot':[scope]}
        for row in iter_task_rows(store, selected, get_record=get):
            if row['asset_id'] != asset_id or row['check'] not in names or (check and row['check'] != check):
                continue
            data = {key: row.get(key) for key in ('check', 'status', 'reason', 'asset_revision', 'error_type')}
            data['stale'] = scope.get('revision', 1) != asset.get('revision', 1)
            check_nodes[row['check']] = node('check', row['id'], names[row['check']], data)
            edge(task_node, check_nodes[row['check']], 'planned_check')
        if not check_nodes:
            return result
        if snapshot is None:snapshot=queries.watermark()
        total,findings=queries.findings(asset_id,task['id'],check_nodes,snapshot,severity,status,limit,offset)
        result['findings'] = {'total': total, 'limit': limit, 'offset': offset, 'snapshot': snapshot, 'has_more': offset + len(findings) < total}
        for finding in findings:
            finding_node = node('finding', finding['id'], finding['title'], finding)
            edge(check_nodes[finding['check']], finding_node, 'finding')
            # Membership, asset, task, check and fingerprint must all agree. Never
            # draw a proof edge merely because a foreign evidence ID was stored.
            count,evidence_rows,references,invalid=queries.proofs(finding['id'],asset_id,task['id'],finding['check'])
            finding['evidence_count'] = count
            finding['history_reference_count'] = references
            finding['invalid_reference_count'] = invalid
            result['omitted']['evidence'] += max(0, count - len(evidence_rows))
            result['omitted']['invalid_evidence'] += invalid
            for evidence_row in evidence_rows:
                proof = json.loads(evidence_row['data'])
                proof_data = {key: proof.get(key) for key in ('created_at', 'observation', 'check', 'task_id')}
                evidence_node = node('evidence', proof['id'], names.get(proof.get('check'), '검증') + ' 증거', proof_data)
                edge(finding_node, evidence_node, 'evidence')
        if 'endpoint_inventory' in check_nodes:
            count,endpoints=queries.endpoints(asset_id,task['id'])
            result['omitted']['endpoints'] = max(0, count - len(endpoints))
            for endpoint in endpoints:
                endpoint_id = node('endpoint', endpoint['id'], endpoint['url'], {'url': endpoint['url'], 'created_at': endpoint['created_at'], 'verified': False})
                edge(check_nodes['endpoint_inventory'], endpoint_id, 'observed_link')
    return result
