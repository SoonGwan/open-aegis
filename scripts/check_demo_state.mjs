import test from 'node:test';
import assert from 'node:assert/strict';
import { initialState, transition } from '../site/demo/state.mjs';

const act = (state, type, extra = {}) => transition(state, { type, ...extra });
const finish = state => {
  for (let i = 0; i < 3; i++) state = act(state, 'tick', { generation: state.generation });
  return state;
};

test('planning alone cannot execute, and repeated approval cannot start another run', () => {
  const idle = initialState();
  assert.equal(act(idle, 'approve'), idle);
  const pending = act(idle, 'draft');
  assert.equal(pending.phase, 'pending');
  assert.deepEqual(pending.completed, []);
  assert.equal(act(pending, 'tick', { generation: pending.generation }), pending);
  const running = act(pending, 'approve');
  assert.equal(act(running, 'approve'), running);
  const completed = finish(running);
  assert.equal(completed.phase, 'completed');
  assert.equal(completed.findings.length, 3);
  assert.equal(act(completed, 'tick', { generation: completed.generation }), completed);
});

test('reset during a run rejects an old callback even after a new approval', () => {
  const oldRun = act(act(initialState(), 'draft'), 'approve');
  let current = act(oldRun, 'reset');
  assert.deepEqual(current.events, []);
  current = act(act(current, 'draft'), 'approve');
  assert.equal(act(current, 'tick', { generation: oldRun.generation }), current);
  assert.deepEqual(current.findings, []);
  assert.equal(finish(current).findings.length, 3);
});

test('cancel keeps evidence, rejects stale work and requires a fresh approval to resume', () => {
  let state = act(act(initialState(), 'draft'), 'approve');
  state = act(state, 'tick', { generation: state.generation });
  const generation = state.generation;
  state = act(state, 'cancel');
  assert.equal(state.phase, 'interrupted');
  assert.equal(state.findings.length, 1);
  assert.equal(act(state, 'tick', { generation }), state);
  state = act(state, 'resume-draft');
  assert.equal(state.phase, 'pending');
  assert.equal(act(state, 'tick', { generation: state.generation }), state);
  state = finish(act(state, 'approve'));
  assert.deepEqual(state.findings.map(f => f.id), ['headers', 'cookie', 'cors']);
});

test('remediation and planning cannot resolve a finding without separate retest approval', () => {
  let state = finish(act(act(initialState(), 'draft'), 'approve'));
  const original = structuredClone(state.findings);
  assert.equal(act(state, 'retest-approve'), state);
  state = act(state, 'remediate');
  assert.deepEqual(state.findings, original);
  state = act(state, 'retest-draft');
  assert.equal(act(state, 'retest-tick', { generation: state.generation }), state);
  state = act(state, 'retest-approve');
  assert.equal(act(state, 'retest-approve'), state);
  state = act(state, 'retest-tick', { generation: state.generation });
  assert.equal(state.findings[0].status, 'resolved');
  assert.equal(state.findings[0].original, original[0].original);
  assert.equal(state.findings[0].retest, 'sample-pass');
  assert.deepEqual(state.findings.slice(1), original.slice(1));
  assert.equal(state.findings.filter(f => f.status === 'open').length, 2);
});

test('reset cancels pending retest results, and navigation preserves current work', () => {
  let state = finish(act(act(initialState(), 'draft'), 'approve'));
  state = act(act(act(state, 'remediate'), 'retest-draft'), 'retest-approve');
  const generation = state.generation;
  const navigated = act(state, 'page', { page: 'overview' });
  assert.equal(navigated.retest, 'running');
  assert.deepEqual(navigated.findings, state.findings);
  state = act(navigated, 'reset');
  assert.equal(act(state, 'retest-tick', { generation }), state);
  assert.equal(state.retest, null);
  assert.deepEqual(state.findings, []);
});
