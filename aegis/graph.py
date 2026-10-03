"""A bounded graph of stored references for one asset and one validation plan."""
import json
from .checks import CATALOG
from .coverage import task_rows


class GraphNotFound(ValueError):
    pass


def build_graph(store, asset_id, task_id=None, *, check=None, severity=None, status=None,
                limit=10, offset=0, snapshot=None):
    if not 1 <= limit <= 25 or offset < 0:
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
    with store.connect() as db:
        db.execute('BEGIN')
        def get(kind, id):
            row = db.execute('SELECT data FROM records WHERE kind=? AND id=?', (kind, id)).fetchone()
            return json.loads(row['data']) if row else None
        asset = get('assets', asset_id)
        if not asset:
            raise GraphNotFound('자산이 없습니다.')
        public_asset = {key: asset.get(key) for key in ('id', 'name', 'url', 'owner', 'revision', 'archived_at')}
        root = node('asset', asset_id, asset['name'], public_asset)
        if task_id:
            task = get('tasks', task_id)
        else:
            row = db.execute("SELECT data FROM records WHERE kind='tasks' AND EXISTS (SELECT 1 FROM json_each(records.data,'$.asset_ids') WHERE value=?) ORDER BY rowid DESC LIMIT 1", (asset_id,)).fetchone()
            task = json.loads(row['data']) if row else None
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
        for row in task_rows(store, task, get_record=get):
            if row['asset_id'] != asset_id or row['check'] not in names or (check and row['check'] != check):
                continue
            data = {key: row.get(key) for key in ('check', 'status', 'reason', 'asset_revision', 'error_type')}
            data['stale'] = scope.get('revision', 1) != asset.get('revision', 1)
            check_nodes[row['check']] = node('check', row['id'], names[row['check']], data)
            edge(task_node, check_nodes[row['check']], 'planned_check')
        if not check_nodes:
            return result
        if snapshot is None:
            snapshot = db.execute("SELECT coalesce(max(rowid),0) FROM records WHERE kind='findings'").fetchone()[0]
        clauses = ["kind='findings'", 'rowid<=?', "json_extract(data,'$.asset_id')=?",
                   "EXISTS (SELECT 1 FROM json_each(records.data,'$.task_ids') WHERE value=?)",
                   "json_extract(data,'$.check') IN (" + ','.join('?' for _ in check_nodes) + ')']
        args = [snapshot, asset_id, task['id'], *check_nodes]
        for key, value in (('severity', severity), ('status', status)):
            if value:
                clauses.append(f"json_extract(data,'$.{key}')=?")
                args.append(value)
        where = ' AND '.join(clauses)
        total = db.execute('SELECT count(*) FROM records WHERE ' + where, args).fetchone()[0]
        fields = ('title', 'check', 'severity', 'status', 'confidence')
        projection = ','.join(f"json_extract(data,'$.{key}') AS \"{key}\"" for key in fields)
        findings = [dict(row) for row in db.execute('SELECT id,' + projection + ' FROM records WHERE ' + where + ' ORDER BY rowid DESC LIMIT ? OFFSET ?', (*args, limit, offset))]
        result['findings'] = {'total': total, 'limit': limit, 'offset': offset, 'snapshot': snapshot, 'has_more': offset + len(findings) < total}
        for finding in findings:
            finding_node = node('finding', finding['id'], finding['title'], finding)
            edge(check_nodes[finding['check']], finding_node, 'finding')
            # Membership, asset, task, check and fingerprint must all agree. Never
            # draw a proof edge merely because a foreign evidence ID was stored.
            matches = """FROM records f CROSS JOIN json_each(f.data,'$.evidence_ids') ref
              JOIN records e ON e.kind='evidence' AND e.id=ref.value
              WHERE f.kind='findings' AND f.id=? AND json_extract(e.data,'$.asset_id')=?
                AND json_extract(e.data,'$.task_id')=? AND json_extract(e.data,'$.check')=?
                AND json_extract(e.data,'$.fingerprint')=json_extract(f.data,'$.fingerprint')"""
            proof_args = (finding['id'], asset_id, task['id'], finding['check'])
            count = db.execute('SELECT count(DISTINCT e.id) ' + matches, proof_args).fetchone()[0]
            evidence_rows = db.execute('SELECT e.id,e.data ' + matches + ' GROUP BY e.id ORDER BY e.rowid DESC LIMIT 2', proof_args).fetchall()
            references = db.execute("SELECT count(DISTINCT value) FROM records f,json_each(f.data,'$.evidence_ids') WHERE f.kind='findings' AND f.id=?", (finding['id'],)).fetchone()[0]
            # Other-task references are valid history, not an inconsistency.
            invalid = db.execute("SELECT count(DISTINCT ref.value) FROM records f CROSS JOIN json_each(f.data,'$.evidence_ids') ref LEFT JOIN records e ON e.kind='evidence' AND e.id=ref.value WHERE f.kind='findings' AND f.id=? AND (e.id IS NULL OR json_extract(e.data,'$.asset_id') IS NOT ? OR json_extract(e.data,'$.check') IS NOT ? OR json_extract(e.data,'$.task_id') IS NULL OR json_extract(e.data,'$.fingerprint') IS NULL OR json_extract(f.data,'$.fingerprint') IS NULL OR json_extract(e.data,'$.fingerprint') IS NOT json_extract(f.data,'$.fingerprint'))", (finding['id'], asset_id, finding['check'])).fetchone()[0]
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
            endpoint_where = "kind='observations' AND json_extract(data,'$.asset_id')=? AND json_extract(data,'$.task_id')=?"
            endpoint_args = (asset_id, task['id'])
            count = db.execute('SELECT count(*) FROM records WHERE ' + endpoint_where, endpoint_args).fetchone()[0]
            endpoints = db.execute("SELECT id,json_extract(data,'$.url') AS url,json_extract(data,'$.created_at') AS created_at FROM records WHERE " + endpoint_where + ' ORDER BY rowid DESC LIMIT 10', endpoint_args).fetchall()
            result['omitted']['endpoints'] = max(0, count - len(endpoints))
            for endpoint in endpoints:
                endpoint_id = node('endpoint', endpoint['id'], endpoint['url'], {'url': endpoint['url'], 'created_at': endpoint['created_at'], 'verified': False})
                edge(check_nodes['endpoint_inventory'], endpoint_id, 'observed_link')
    return result
