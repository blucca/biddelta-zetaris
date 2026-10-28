"""Minimal offline contract check. Fixture-shaped rows do not claim a native query."""
import copy
import csv
import json
from domain import DATA, apply_plan, fixture, plan_from_native, task_hash
from server import session_due


def response_for(source):
    tasks = {t['task_id']: t for t in source['rows']}
    changes = {c['change_id']: c for c in fixture('notice_changes')['rows']}
    docs = {d['document_id']: d for d in csv.DictReader((DATA / 'document_register.csv').open())}
    links = [('T1', 'C1', None), ('T2', 'C2', 'D1'), ('T2', 'C2', 'D2'),
             ('T3', 'C3', 'D1'), ('T3', 'C3', 'D3'), ('T3', 'C3', 'D4'), ('T3', 'C3', 'D5'),
             ('T4', 'C2', 'D1'), ('T4', 'C3', 'D1'), ('T5', 'C2', 'D1'), ('T5', 'C3', 'D1')]
    headers = ['task_id', 'change_id', 'section', 'old_value', 'new_value', 'source_sha256',
               'old_value_pointer', 'new_value_pointer', 'snapshot_id', 'snapshot_version',
               'task_exists', 'task_version', 'title', 'status', 'due_at', 'notes',
               'prior_approval_notice_id', 'task_sha256', 'document_relation', 'document_id', 'availability']
    rows = []
    for task_id, change_id, document_id in links:
        row = {**changes[change_id], **tasks[task_id]}
        row.update(document_id=document_id, availability=docs[document_id]['availability'] if document_id else None,
                   document_relation=('requires_document' if document_id == 'D1' else 'retains_asset') if document_id else None)
        rows.append([row[key] for key in headers])
    return {'headers': headers, 'data': rows}


initial, edited = fixture('tasks_initial'), fixture('tasks_user_edit')
assert session_due({'idToken': 'e30.eyJleHAiOjF9.test'})
for task in initial['rows'] + edited['rows']:
    assert task_hash(task) == (task['task_sha256'] or '')
old_plan = plan_from_native(response_for(initial))
tabular = response_for(initial)
assert plan_from_native({'records': [dict(zip(tabular['headers'], row)) for row in tabular['data']]}) == old_plan
assert (old_plan['expanded_rows'], old_plan['evidence_task_pairs'], old_plan['planned_writes']) == (11, 7, 5)
before = copy.deepcopy(edited)
stopped_data, stopped = apply_plan(edited, old_plan)
assert stopped['result'] == 'stopped' and stopped['writes'] == 0 and stopped_data == before
fresh_plan = plan_from_native(response_for(edited))
applied_data, applied = apply_plan(edited, fresh_plan)
assert applied['writes'] == 4 and applied['already_aligned'] == 1
for task_id in ('T2', 'T6'):
    old = next(t for t in edited['rows'] if t['task_id'] == task_id)
    new = next(t for t in applied_data['rows'] if t['task_id'] == task_id)
    assert {k: v for k, v in old.items() if k not in ('snapshot_id', 'snapshot_version')} == {
        k: v for k, v in new.items() if k not in ('snapshot_id', 'snapshot_version')}
assert sum(t['task_id'] == 'T5' and t['task_exists'] for t in applied_data['rows']) == 1
for task in applied_data['rows']:
    assert task_hash(task) == (task['task_sha256'] or '')
assert plan_from_native(response_for(applied_data))['planned_writes'] == 0
print(json.dumps({'offline_contract': 'PASS', 'stale_writes': 0, 'fresh_writes': 4,
                  'aligned': 1, 'T2_body_retained': True, 'T6_body_retained': True, 'duplicate_request': False}))
