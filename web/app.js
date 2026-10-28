'use strict';
const $ = selector => document.querySelector(selector);
const state = {source: null, documents: [], sql: '', plan: null, native: null, receipt: null,
  phase: 'query', selectedChange: 'C1', trace: 'sql', busy: false};
const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const label = value => ({review_required:'Review required', approved:'Approved', ready:'Ready',
  paused:'Paused', done:'Done', open:'Open'})[value] || (value ? String(value).replace(/_/g,' ') : 'Reserved creation');

async function api(path, body) {
  const response = await fetch(path, body === undefined ? {} : {method:'POST',
    headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)});
  const result = await response.json();
  if (!response.ok && !result.receipt) throw new Error(result.error || `Request failed (${response.status})`);
  return result;
}

function banner(text, success = false) {
  const node = $('#event-banner');
  node.hidden = !text; node.classList.toggle('success', success); node.textContent = text;
}

function setBusy(busy, message='') {
  state.busy = busy;
  for (const button of document.querySelectorAll('.action-buttons button,#reset-button')) button.disabled = busy;
  if (busy) { $('#primary-button').textContent = message; $('#next-action-detail').textContent = 'The native platform is executing the source query or recording the version-checked batch.'; }
}

function evidence() {
  if (!state.plan) return;
  const change = state.plan.changes.find(c => c.change_id === state.selectedChange);
  const titles = {C1:'A later SQ submission deadline',C2:'Additional financial requirements',C3:'Additional technical questions'};
  const impacts = {C1:'T1 follows the changed deadline. Its task identity and existing notes stay intact.',
    C2:'T2 must review the added minimum requirements. Retained turnover evidence stays recorded.',
    C3:'T3 must review the added questions. All three existing case studies stay recorded.'};
  let comparison;
  if (change.change_id === 'C1') {
    comparison = '<p class="quote-label">Previously recorded</p><blockquote class="evidence-date">2 December 2024, 12:00 GMT</blockquote>' +
      '<p class="quote-label">Official correction</p><blockquote class="added evidence-date">9 December 2024, 16:00 GMT</blockquote>';
  } else {
    const added = change.new_value.startsWith(change.old_value) ? change.new_value.slice(change.old_value.length).trim() : change.new_value;
    comparison = `<p class="quote-label">Existing requirement retained</p><blockquote>${escape(change.old_value)}</blockquote>` +
      `<p class="quote-label">Added in the correction</p><blockquote class="added">${escape(added)}</blockquote>`;
  }
  $('#evidence-content').innerHTML = `<p class="section-ref">${escape(change.change_id)} / Section ${escape(change.section)}</p><h3>${titles[change.change_id]}</h3>${comparison}<p class="clause-impact">${impacts[change.change_id]}</p>` +
    `<details class="provenance"><summary>Inspect exact source pointers & hash</summary><p>Old: ${escape(change.old_value_pointer)}<br>New: ${escape(change.new_value_pointer)}<br>Source SHA-256: ${escape(change.source_sha256)}</p></details>`;
  document.querySelectorAll('[data-change]').forEach(b => b.classList.toggle('selected', b.dataset.change === state.selectedChange));
}

function renderTasks() {
  if (!state.source) return;
  const tasks = state.source.rows.filter(t => t.task_id !== 'T6');
  const version = state.source.rows[0].snapshot_version;
  $('#snapshot-badge').textContent = `Source snapshot ${version}`;
  $('#tasks').innerHTML = tasks.map(task => {
    const action = state.plan?.actions.find(a => a.task_id === task.task_id);
    const changed = action && action.before.task_version !== task.task_version && state.phase !== 'applied' && state.phase !== 'verified';
    const aligned = action?.aligned;
    const proposal = action ? `<p class="${aligned ? 'already' : 'proposal'}">${aligned ? 'Already aligned; retain this work' : (state.phase === 'applied' || state.phase === 'verified' ? 'Recorded: ' : 'Proposed: ') + escape(action.label)}</p>` : '';
    const detail = task.task_id === 'T2' && task.task_version >= 2 ? `<p class="task-detail">${escape(task.notes)}</p>` : '';
    return `<article class="task-row ${aligned ? 'aligned' : ''} ${changed ? 'changed' : ''}"><span class="task-number">${escape(task.task_id)}</span><div class="task-copy"><strong>${escape(task.title)}</strong>${proposal}${detail}</div><div class="task-state"><strong>${escape(label(task.status))}</strong><small>${changed ? 'Plan v' + action.before.task_version + ' / now v' + task.task_version : 'Task v' + task.task_version}</small></div></article>`;
  }).join('');
  if (state.plan) {
    const p = state.plan;
    $('#task-summary').textContent = `${p.affected_tasks} affected tasks / ${p.planned_writes} planned writes / ${p.already_aligned} already aligned`;
  }
}

function renderAction() {
  const edit = $('#edit-button'), primary = $('#primary-button');
  edit.hidden = !(state.plan && state.source?.rows[0].snapshot_version === 1 && state.phase === 'planned');
  const choices = {
    query: ['A changed tender needs a fresh plan.','Read the three sources before changing approved work.','Query sources in Zetaris'],
    planned: ['Five changes, ready for your review.','Add the sample teammate edit to exercise the complete-batch version gate.',`Check & apply ${state.plan?.planned_writes || 5} changes`],
    edited: ['A teammate reopened the financial review.','The prepared plan still carries the earlier task version. Check it before writing.','Check prepared plan'],
    conflict: ['The stale batch stopped with zero writes.','Read the current task state from all three sources before preparing a new plan.','Refresh evidence in Zetaris'],
    fresh: ['The teammate’s work is already aligned.','Keep the entire financial-review note. Apply the remaining four task changes.',`Apply ${state.plan?.planned_writes ?? 4} changes`],
    applied: ['Four changes recorded. One task already aligned.','Verify the new source snapshot with another native Zetaris query.','Verify in Zetaris'],
    verified: ['The source confirms the recorded result.','Final sign-off remains paused while the applicable guidance awaits collection.','Refresh source evidence'],
  };
  const [title, detail, text] = choices[state.phase];
  $('#next-action-title').textContent = title; $('#next-action-detail').textContent = detail; primary.textContent = text;
}

function renderWorkflow() {
  const order = ['query','edit','check','refresh'];
  const current = ({query:0,planned:1,edited:2,conflict:3,fresh:3,applied:3,verified:3})[state.phase];
  document.querySelectorAll('[data-step]').forEach(li => {
    const step = order.indexOf(li.dataset.step);
    li.classList.toggle('active', step === current); li.classList.toggle('done', step < current || state.phase === 'verified');
  });
}

function renderReceipt() {
  if (state.native) {
    const n = state.native, p = state.plan;
    $('#connection-label').textContent = 'Native Zetaris query completed'; $('#connection-dot').classList.add('queried');
    $('#query-receipt').innerHTML = `<span class="receipt-icon" aria-hidden="true">⌘</span><p>Zetaris returned ${p.expanded_rows} rows / ${p.evidence_task_pairs} evidence–task pairs / ${p.affected_tasks} tasks<small>Snapshot ${p.snapshot_version} / ${(n.duration_ms / 1000).toFixed(1)}s / ${escape(n.utc.slice(11,19))} UTC / request ${escape(n.request_id.slice(0,8))}</small></p>`;
  }
  const receipt = state.receipt;
  $('#apply-receipt').hidden = !(receipt && receipt.result === 'applied');
  if (receipt?.result === 'applied') $('#apply-receipt').innerHTML = `<span class="write-count">${receipt.writes}</span><div><h3>Writes recorded. Five tasks reconciled.</h3><p>${receipt.already_aligned} already aligned / teammate note retained / T6 untouched</p></div><div class="receipt-tasks">${receipt.write_receipts.map(r => escape(r.task_id) + ' recorded at v' + r.task_version).join('<br>')}</div>`;
}

function renderTrace() {
  if (state.trace === 'sql') $('#trace-content').textContent = state.sql;
  if (state.trace === 'response') $('#trace-content').textContent = state.native ? JSON.stringify(state.native, null, 2) : 'Run a source query to inspect its real native response.';
  if (state.trace === 'sources') $('#trace-content').textContent = JSON.stringify({
    public_notice: {platform_source:'biddelta_public',connector:'REST',provenance:'Official historical Find a Tender notice & correction',
      original:'https://www.find-tender.service.gov.uk/Notice/035490-2024',correction:'https://www.find-tender.service.gov.uk/Notice/036312-2024',cutoff:'2024-11-08T15:56:37Z'},
    supplier_workspace:{platform_source:'biddelta_tasks',connector:'REST',provenance:'Illustrative supplier tasks and authored dependency map',
      snapshot:state.source?.rows[0].snapshot_id,task_body_hash:'Canonical task body; snapshot metadata is carried separately'},
    document_register:{platform_source:'biddelta_document_pg',connector:'PostgreSQL JDBC',provenance:'Illustrative document records',
      note:'D1 awaits collection. D2–D6 are retained illustrative assets. The register stays fixed in this replay.',documents:state.documents},
    write_back:'The Python replay service validates the complete source snapshot and five task versions/hashes, then atomically replaces the synthetic task source.'
  }, null, 2);
  document.querySelectorAll('[data-trace]').forEach(b => b.classList.toggle('selected', b.dataset.trace === state.trace));
}

function render() { evidence(); renderTasks(); renderAction(); renderWorkflow(); renderReceipt(); renderTrace(); }

async function runQuery() {
  const previous = state.phase;
  setBusy(true, 'Querying native Zetaris…');
  const result = await api('/api/query', {});
  Object.assign(state, result);
  if (previous === 'conflict' || previous === 'fresh') {
    state.phase = 'fresh'; banner(`Fresh native snapshot ${state.plan.snapshot_version}: T2 is already in review. Its complete teammate note is retained; four writes remain.`, true);
  } else if (previous === 'applied' || previous === 'verified' || state.plan.planned_writes === 0) {
    state.phase = 'verified'; banner(`Native source verification completed: snapshot ${state.plan.snapshot_version}, ${state.plan.planned_writes} further writes required. Sign-off stays paused and retained work is intact.`, true);
  } else { state.phase = 'planned'; banner('The native three-source query prepared five task actions with their source versions.'); }
}

$('#primary-button').addEventListener('click', async () => {
  if (state.busy) return;
  try {
    if (['query','conflict','applied','verified'].includes(state.phase)) await runQuery();
    else {
      setBusy(true,'Checking complete-batch versions…');
      const result = await api('/api/apply', {plan_id:state.plan.plan_id});
      Object.assign(state, result);
      if (result.receipt.result === 'stopped') { state.phase='conflict'; banner('Batch stopped: T2 changed from version 1 to 2. Zero writes. The teammate’s complete note and all other tasks remain intact.'); }
      else { state.phase='applied'; banner('Four writes completed. The financial review was already aligned; its full teammate note stays intact.', true); }
    }
  } catch (error) { banner(error.message); }
  finally { setBusy(false); render(); }
});

$('#edit-button').addEventListener('click', async () => {
  if (state.busy) return;
  try {
    setBusy(true,'Recording sample teammate edit…');
    const result = await api('/api/demo/teammate-edit', {});
    state.source = result.source; state.phase='edited';
    banner('Sample teammate edit: T2 reopened at version 2. “Finance review reopened; awaiting the applicable SQ guidance.” The prepared plan still carries version 1.');
  } catch (error) { banner(error.message); }
  finally { setBusy(false); render(); }
});

$('#reset-button').addEventListener('click', async () => {
  if (state.busy) return;
  try {
    const result = await api('/api/demo/reset', {});
    Object.assign(state,{source:result.source,plan:null,native:null,receipt:null,phase:'query'});
    banner('Historical sample reset to snapshot 1. Query Zetaris to prepare the first plan.');
    $('#connection-label').textContent='Source query ready'; $('#connection-dot').classList.remove('queried');
    $('#evidence-content').innerHTML='<div class="evidence-placeholder"><h3>Start with the source evidence.</h3><p>The faithful notice, task and PostgreSQL document sources are ready for a native query.</p></div>';
    $('#task-summary').textContent='Query to prepare the five-task impact plan';
    $('#query-receipt').innerHTML='<span class="receipt-icon" aria-hidden="true">⌘</span><p>Every evidence refresh executes on the real Zetaris platform.<small>The task write-back uses a complete-batch version check.</small></p>';
    render();
  } catch(error) { banner(error.message); }
});

document.querySelectorAll('[data-change]').forEach(b => b.addEventListener('click', () => {state.selectedChange=b.dataset.change; evidence();}));
$('#trace-button').addEventListener('click', () => {renderTrace();$('#trace-dialog').showModal();});
$('#trace-close').addEventListener('click', () => $('#trace-dialog').close());
document.querySelectorAll('[data-trace]').forEach(b => b.addEventListener('click', () => {state.trace=b.dataset.trace;renderTrace();}));
api('/api/state').then(result => {Object.assign(state,result);render();}).catch(error => banner(error.message));
