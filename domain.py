"""One historical tender replay. Upgrade the clause/action map before adding cases."""
import copy
import hashlib
import json
from pathlib import Path

DATA = Path(__file__).parent / 'data'
HASH_FIELDS = json.loads((DATA / 'manifest.json').read_text())['hash_contracts']['task_sha256']['fields']


def task_hash(task):
    if not int(task['task_exists']):
        return ''
    body = {key: task[key] for key in HASH_FIELDS}
    body['task_version'] = int(body['task_version'])
    for key in ('due_at', 'prior_approval_notice_id'):
        body[key] = body[key] or None
    encoded = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
    return hashlib.sha256(encoded).hexdigest()


def fixture(name):
    return json.loads((DATA / (name + '.json')).read_text())


def plan_from_native(response):
    """Every task, version, amendment and document dependency comes from native SQL."""
    if 'records' in response:
        rows = response['records']
        assert rows and all(isinstance(row, dict) for row in rows), 'Native records returned no complete evidence'
    else:
        headers, data = response['headers'], response['data']
        assert data and all(len(row) == len(headers) for row in data), 'Native query returned no complete evidence'
        rows = [dict(zip(headers, row)) for row in data]
    tasks, changes = {}, {}
    task_fields = ['task_id', 'snapshot_id', 'snapshot_version', 'task_exists', 'task_version',
                   'title', 'status', 'due_at', 'notes', 'prior_approval_notice_id', 'task_sha256']
    for row in rows:
        task = {key: row[key] for key in task_fields}
        for key in ('snapshot_version', 'task_exists', 'task_version'):
            task[key] = int(task[key])
        if task['task_id'] in tasks:
            assert tasks[task['task_id']] == task, 'Inconsistent task rows in native join'
        tasks[task['task_id']] = task
        change = {key: row[key] for key in ('change_id', 'section', 'old_value', 'new_value',
                                           'source_sha256', 'old_value_pointer', 'new_value_pointer')}
        if change['change_id'] in changes:
            assert changes[change['change_id']] == change, 'Inconsistent amendment rows'
        changes[change['change_id']] = change
    assert set(tasks) == {'T1', 'T2', 'T3', 'T4', 'T5'}, 'This replay supports five affected tasks'
    assert set(changes) == {'C1', 'C2', 'C3'}, 'Unexpected correction clauses'
    snapshots = {(t['snapshot_id'], t['snapshot_version']) for t in tasks.values()}
    assert len(snapshots) == 1, 'Query crossed source snapshots; refresh before planning'
    missing = sorted({r['document_id'] for r in rows if r['document_relation'] == 'requires_document'
                      and r['availability'] == 'awaiting_file'})
    assert missing == ['D1'], 'This replay expects the applicable SQ/guidance collection dependency'
    deadline = changes['C1']['new_value']
    assert deadline == '2024-12-09T16:00:00Z', 'This replay supports the recorded deadline amendment'
    definitions = {
        'T1': ('Update submission deadline', {'due_at': deadline}, 'C1', 'Keep the shared submission date aligned.'),
        'T2': ('Reopen financial review', {'status': 'review_required'}, 'C2',
               'Review the additional minimum requirements against applicable SQ guidance. Retain turnover evidence.'),
        'T3': ('Reopen technical review', {'status': 'review_required'}, 'C3',
               'Review the additional capability questions in applicable SQ guidance. Retain three case studies.'),
        'T4': ('Pause final sign-off', {'status': 'paused'}, 'C2 + C3',
               'Resume final sign-off after applicable files are recorded and financial and technical reviews pass.'),
        'T5': ('Create one document request', {'task_exists': 1, 'row_kind': 'existing_task', 'status': 'open'},
               'C2 + C3', 'Obtain the applicable SQ and accompanying guidance; record document versions on receipt.'),
    }
    actions = []
    for task_id, (label, desired, evidence, note) in definitions.items():
        task = tasks[task_id]
        aligned = all(task.get(key) == value for key, value in desired.items() if key != 'row_kind')
        patch = {} if aligned else dict(desired)
        if patch and task_id != 'T1':
            patch['notes'] = ((task['notes'] or '') + ' ' + note).strip()
        actions.append({'task_id': task_id, 'label': label, 'evidence': evidence, 'detail': note,
                        'aligned': aligned, 'patch': patch, 'before': task})
    snapshot_id, snapshot_version = next(iter(snapshots))
    return {'snapshot_id': snapshot_id, 'snapshot_version': snapshot_version, 'actions': actions,
            'changes': [changes[k] for k in sorted(changes)], 'missing_documents': missing,
            'expanded_rows': len(rows), 'evidence_task_pairs': len({(r['task_id'], r['change_id']) for r in rows}),
            'affected_tasks': len(tasks), 'planned_writes': sum(not a['aligned'] for a in actions),
            'already_aligned': sum(a['aligned'] for a in actions)}


def apply_plan(current, plan):
    """Validate the complete five-task batch, then make one source-file replacement."""
    tasks = {t['task_id']: t for t in current['rows']}
    conflicts = []
    source_snapshots = {(t['snapshot_id'], t['snapshot_version']) for t in current['rows']}
    if source_snapshots != {(plan['snapshot_id'], plan['snapshot_version'])}:
        conflicts.append({'kind': 'snapshot', 'expected_version': plan['snapshot_version'],
                          'current_versions': sorted({t['snapshot_version'] for t in current['rows']})})
    for action in plan['actions']:
        before = action['before']
        task = tasks.get(action['task_id'])
        if task is None or (task['task_version'], task['task_exists'], task['task_sha256']) != (
                before['task_version'], before['task_exists'], before['task_sha256']):
            conflicts.append({'kind': 'task', 'task_id': action['task_id'],
                              'expected_version': before['task_version'],
                              'current_version': task['task_version'] if task else None})
        if task is not None:
            assert task_hash(task) == (task['task_sha256'] or ''), 'Source body/hash disagreement'
    if conflicts:
        return current, {'result': 'stopped', 'writes': 0, 'conflicts': conflicts,
                         'message': 'A teammate changed the source. Refresh evidence before applying this batch.'}
    next_data = copy.deepcopy(current)
    writes = []
    for task in next_data['rows']:
        action = next((a for a in plan['actions'] if a['task_id'] == task['task_id']), None)
        if action and action['patch']:
            task.update(action['patch'])
            task['task_version'] += 1
            task['task_sha256'] = task_hash(task)
            writes.append({'task_id': task['task_id'], 'task_version': task['task_version'],
                           'label': action['label']})
    if writes:
        version = plan['snapshot_version'] + 1
        for task in next_data['rows']:
            task.update(snapshot_id=f'S{version - 1}-biddelta-applied', snapshot_version=version)
    return next_data, {'result': 'applied', 'writes': len(writes), 'write_receipts': writes,
                       'affected_tasks': plan['affected_tasks'], 'already_aligned': plan['already_aligned'],
                       'retained_task': 'T6', 'retained_documents': ['D2', 'D3', 'D4', 'D5', 'D6'],
                       'message': 'Recorded turnover evidence, three case studies and completed architecture retained.'}
