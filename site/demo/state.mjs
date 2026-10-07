// Browser-only sample workflow. It never sends requests or executes real checks.
export const checks = ['headers', 'cookie', 'cors'];
export function initialState() {
  return { phase: 'idle', page: 'overview', generation: 0, completed: [], findings: [], events: [], selected: 'headers', remediation: false, retest: null };
}
export function transition(previous, action) {
  if (action.type === 'reset') return { ...initialState(), generation: previous.generation + 1 };
  if (action.type === 'page' && ['overview', 'plan', 'findings'].includes(action.page)) return { ...previous, page: action.page };
  if (action.type === 'select' && previous.findings.some(f => f.id === action.id)) return { ...previous, page: 'findings', selected: action.id };
  if (action.type === 'draft' && previous.phase === 'idle') return { ...previous, phase: 'pending', page: 'plan', events: [...previous.events, 'draft'] };
  if (action.type === 'approve' && previous.phase === 'pending') return { ...previous, phase: 'running', generation: previous.generation + 1, events: [...previous.events, 'approved'] };
  if (action.type === 'tick' && previous.phase === 'running' && action.generation === previous.generation) {
    const id = checks[previous.completed.length];
    if (!id) return previous;
    const completed = [...previous.completed, id];
    return { ...previous, completed, findings: [...previous.findings, { id, status: 'open', original: 'sample-fail' }], phase: completed.length === checks.length ? 'completed' : 'running', events: [...previous.events, id, ...(completed.length === checks.length ? ['completed'] : [])] };
  }
  if (action.type === 'cancel' && previous.phase === 'running') return { ...previous, phase: 'interrupted', generation: previous.generation + 1, events: [...previous.events, 'cancelled'] };
  if (action.type === 'resume-draft' && previous.phase === 'interrupted') return { ...previous, phase: 'pending', page: 'plan', events: [...previous.events, 'resume-draft'] };
  if (action.type === 'remediate' && previous.phase === 'completed' && !previous.remediation) return { ...previous, remediation: true, page: 'findings', selected: 'headers', events: [...previous.events, 'remediation'] };
  if (action.type === 'retest-draft' && previous.remediation && previous.retest === null) return { ...previous, retest: 'pending', events: [...previous.events, 'retest-draft'] };
  if (action.type === 'retest-approve' && previous.retest === 'pending') return { ...previous, retest: 'running', generation: previous.generation + 1, events: [...previous.events, 'retest-approved'] };
  if (action.type === 'retest-tick' && previous.retest === 'running' && action.generation === previous.generation) return { ...previous, retest: 'completed', findings: previous.findings.map(f => f.id === 'headers' ? { ...f, status: 'resolved', retest: 'sample-pass' } : f), events: [...previous.events, 'retest-completed'] };
  return previous;
}
