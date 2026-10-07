import { checks, initialState, transition } from './state.mjs';

const copy = {
  ko: {
    overview:'워크스페이스', plan:'계획 · 실행', findings:'발견 · 증거',
    title:'검토에서 증거까지, 직접 체험하세요.', intro:'샘플 쇼핑몰의 보안 설정을 확인하는 짧은 워크플로입니다. 계획을 검토하고, 실행을 승인하고, 증거로 수정 결과를 확인하세요.',
    disclosure:'체험 모드 · 샘플 데이터입니다. 브라우저 안에서만 동작하며 실제 스캔이나 외부 요청을 보내지 않습니다.',
    reset:'처음부터', local:'브라우저 안에서 실행', localDescription:'샘플 데이터만 사용합니다. 실제 자산을 검사하지 않습니다.', back:'← 프로젝트 소개',
    phase:{idle:'시작 전',pending:'승인 대기',running:'샘플 실행 중',completed:'검사 완료',interrupted:'중지됨'},
    metricAssets:'샘플 자산',metricChecks:'완료한 검사',metricFindings:'열린 발견 사항',metricRequests:'외부 검사 요청',sample:'이 데모의 샘플',stepsUnit:'3개 중',requestsNote:'실제 네트워크 검사 없음',
    assetTitle:'검증할 자산',assetName:'샘플 쇼핑몰',assetBadge:'샘플',assetNote:'범위는 shop-demo.example 한 곳의 GET 요청으로 한정됩니다. 입력하는 실제 대상은 없습니다.',
    draft:'검사 계획 만들기',toPlan:'계획 확인',toFindings:'발견 사항 보기',flowTitle:'지금 어디까지 왔나요?',
    flow:['자산과 범위','계획 검토','별도 실행 승인','발견 사항과 증거','수정 후 재검증'],
    flowNotes:['예시 자산 1개와 검사 한도를 확인합니다.','어떤 검사를 할지 실행 전에 확인합니다.','승인한 다음 샘플 단계가 진행됩니다.','요청·응답 예시와 판단 근거를 확인합니다.','원래 증거를 보존하고 새 결과를 연결합니다.'],
    planTitle:'무엇이 실행되는지, 먼저 확인하세요.',planIntro:'허용한 범위, 요청 방식과 검사 한도를 검토하세요. 계획 생성과 실행 승인은 별도입니다.',
    planPanel:'검사 계획',scope:'대상 범위',method:'요청 방식',budget:'요청 한도',budgetValue:'최대 12개 · 샘플 검사 3단계',policy:'범위 밖 요청',policyValue:'허용하지 않음',
    pendingNote:'아직 실행하지 않았습니다. 승인 버튼을 누르면 미리 준비한 샘플 응답으로 진행합니다.', approve:'검토한 계획 승인 · 실행',cancel:'샘플 실행 중지',resume:'남은 검사의 새 계획 만들기',
    idleNote:'워크스페이스에서 계획을 만든 뒤 이곳에서 검토하세요.',runningNote:'아래 진행 상태는 브라우저가 재생하는 샘플 단계입니다. 실제 서버를 검사하는 상태가 아닙니다.',doneNote:'샘플 검사 3개가 완료됐습니다. 발견 사항에서 원래 증거와 수정 후 결과를 확인하세요.',stoppedNote:'남은 샘플 단계를 중지했습니다. 수집한 샘플 증거는 남아 있으며, 재개하려면 새 계획을 승인해야 합니다.',
    execution:'샘플 진행 상태',waiting:'대기',checking:'샘플 처리 중',observed:'샘플 근거 수집',events:'진행 기록',noEvents:'아직 이벤트가 없습니다. 계획을 만들어 시작하세요.',
    event:{draft:'검사 계획 생성 · 실행 승인 대기',approved:'계획 실행 승인 · 샘플 처리 시작',headers:'헤더 검사 예시 · nosniff 누락 기록',cookie:'쿠키 검사 예시 · HttpOnly 누락 기록',cors:'CORS 정책 예시 · 지정한 기대값과 불일치',completed:'샘플 검사 완료 · 발견 사항 3개 보존',cancelled:'샘플 실행 중지 · 기존 증거 보존','resume-draft':'남은 검사에 대한 새 계획 생성 · 승인 대기',remediation:'헤더 조치 기록 · 원래 증거 보존','retest-draft':'헤더 재검증 계획 생성 · 별도 승인 대기','retest-approved':'재검증 승인 · 샘플 처리 시작','retest-completed':'재검증 예시 통과 · 원래/새 증거 연결'},
    findingsTitle:'발견 사항에서 판단의 근거까지.',findingsIntro:'예시 요청·응답을 확인하고, 헤더 문제의 조치를 기록한 뒤 별도로 승인한 재검증을 체험하세요.',noFindings:'아직 발견 사항이 없습니다. 계획을 승인하고 샘플 검사를 진행해 보세요.',original:'원래 증거 · 샘플',request:'요청 예시',response:'원래 응답 예시',why:'왜 확인해야 하나요?',fix:'권장 조치',open:'열림',resolved:'재검증 통과',medium:'중간',low:'정책 검토',
    remediation:'헤더 조치 기록하기',remediationNote:'예시 조치: X-Content-Type-Options: nosniff 추가. 원래 증거는 변경하지 않습니다.',
    retestDraft:'헤더 재검증 계획 만들기',retestTitle:'새 재검증 계획',retestNote:'같은 범위에서 헤더 1개를 다시 확인합니다. 조치 기록만으로 해결 처리하지 않습니다.',retestApprove:'재검증 승인 · 실행',retesting:'샘플 재검증 진행 중…',retestDone:'수정 후 결과 · 샘플 통과',retestProof:'새 응답에 X-Content-Type-Options: nosniff가 있습니다. 원래 누락 응답은 위에 그대로 남아 있습니다. 다른 발견 사항 2개는 아직 열려 있습니다.',
    headers:{title:'콘텐츠 유형 보호 헤더 누락',why:'샘플 응답에는 X-Content-Type-Options가 없습니다. 브라우저가 선언된 콘텐츠 유형을 따르도록 설정을 검토합니다.',fix:'응답에 X-Content-Type-Options: nosniff를 추가합니다.'},
    cookie:{title:'세션 쿠키의 HttpOnly 누락',why:'이 예시의 세션 쿠키에는 HttpOnly가 없습니다. 스크립트의 쿠키 접근을 제한해야 한다는 운영 정책과 비교합니다.',fix:'세션 쿠키에 HttpOnly를 추가하고 Secure·SameSite 정책을 함께 검토합니다.'},
    cors:{title:'CORS 허용 출처가 기대값과 불일치',why:'이 샘플 API의 운영 정책은 console.example만 허용합니다. 응답의 와일드카드는 그 기대값과 다릅니다. 와일드카드 자체가 모든 공개 API의 취약점인 것은 아닙니다.',fix:'실제 API의 공개 범위와 인증 요구를 확인하고 명시적으로 허용한 출처로 설정합니다.'},
    startHint:'1 / 샘플 자산으로 시작', eventHint:'행동 → 상태 → 근거',
  },
  en: {
    overview:'Workspace',plan:'Plan & run',findings:'Findings', title:'Try the path from review to evidence.',intro:'Walk through a sample shop configuration check. Review the plan, approve execution, then connect the evidence to a remediation and independent retest.',
    disclosure:'Demo mode · Sample data. Runs entirely in your browser. No real scans or external target requests.',reset:'Start over',local:'Runs in your browser',localDescription:'Sample data only. No real assets are scanned.',back:'← About the project',
    phase:{idle:'Not started',pending:'Awaiting approval',running:'Sample running',completed:'Checks complete',interrupted:'Stopped'},
    metricAssets:'Sample assets',metricChecks:'Checks complete',metricFindings:'Open findings',metricRequests:'External target requests',sample:'This sample scenario',stepsUnit:'of 3',requestsNote:'No real network checks',
    assetTitle:'The asset to review',assetName:'Sample shop',assetBadge:'SAMPLE',assetNote:'Scope is limited to GET requests on shop-demo.example. No real target input is accepted.',
    draft:'Create a check plan',toPlan:'Review the plan',toFindings:'View findings',flowTitle:'Where are we now?',flow:['Asset & scope','Review the plan','Approve execution','Findings & evidence','Remediate & retest'],flowNotes:['Review one sample asset and its limits.','See the checks before execution.','Sample processing starts after approval.','Inspect sample requests, responses and reasons.','Keep the original proof and link the new result.'],
    planTitle:'Review what will run first.',planIntro:'Check the allowed scope, request method and budget. Creating a plan and approving execution are separate actions.',planPanel:'Check plan',scope:'Allowed scope',method:'Method',budget:'Request budget',budgetValue:'Maximum 12 · 3 sample steps',policy:'Outside scope',policyValue:'Not allowed',
    pendingNote:'Nothing has run yet. Approval starts the prepared sample responses.',approve:'Approve reviewed plan & run',cancel:'Stop sample execution',resume:'Create a plan for remaining checks',idleNote:'Create a plan from the workspace, then review it here.',runningNote:'These stages replay sample data inside your browser. They do not show a real server being scanned.',doneNote:'All 3 sample checks are complete. Inspect the findings, original evidence and retest result.',stoppedNote:'Remaining sample steps stopped. Existing sample evidence is retained. Create and approve a new plan to continue.',execution:'Sample progress',waiting:'Waiting',checking:'Sample processing',observed:'Sample evidence recorded',events:'Activity log',noEvents:'No activity yet. Create a plan to begin.',
    event:{draft:'Check plan created · awaiting approval',approved:'Execution approved · sample processing starts',headers:'Header example · missing nosniff recorded',cookie:'Cookie example · missing HttpOnly recorded',cors:'CORS example · configured expectation differs',completed:'Sample checks complete · 3 findings retained',cancelled:'Sample execution stopped · original evidence retained','resume-draft':'Remaining checks planned · awaiting fresh approval',remediation:'Header remediation recorded · original evidence retained','retest-draft':'Header retest planned · awaiting separate approval','retest-approved':'Retest approved · sample processing starts','retest-completed':'Sample retest passed · original/new evidence linked'},
    findingsTitle:'Follow a finding back to the evidence.',findingsIntro:'Inspect sample requests and responses. Record the header remediation, then approve a separate retest.',noFindings:'No findings yet. Approve the plan and run the sample checks.',original:'Original evidence · sample',request:'Sample request',response:'Original sample response',why:'Why review it?',fix:'Suggested remediation',open:'Open',resolved:'Retest passed',medium:'Medium',low:'Policy review',
    remediation:'Record header remediation',remediationNote:'Sample change: add X-Content-Type-Options: nosniff. Original evidence stays unchanged.',retestDraft:'Create header retest plan',retestTitle:'New retest plan',retestNote:'Check one header in the same scope. Recording a remediation alone does not resolve the finding.',retestApprove:'Approve retest & run',retesting:'Sample retest running…',retestDone:'New result · sample passed',retestProof:'The new response includes X-Content-Type-Options: nosniff. The original missing-header response stays above. The other 2 findings remain open.',
    headers:{title:'Content-type protection header missing',why:'The sample response omits X-Content-Type-Options. Review whether browsers should enforce the declared content type.',fix:'Add X-Content-Type-Options: nosniff to the response.'},cookie:{title:'Session cookie missing HttpOnly',why:'This sample session cookie omits HttpOnly. Compare it with the policy requiring restricted script access to the session cookie.',fix:'Add HttpOnly to the session cookie and review Secure/SameSite settings.'},cors:{title:'CORS origin differs from the expectation',why:'This sample API policy allows only console.example. The response wildcard differs. A wildcard alone is not a vulnerability for every public API.',fix:'Review the API audience and authentication requirements, then configure its explicit allowed origins.'},startHint:'1 / START WITH A SAMPLE ASSET',eventHint:'ACTION → STATE → EVIDENCE',
  },
};
const responses = {
  headers: 'HTTP/1.1 200 OK\nContent-Type: text/html; charset=utf-8\n\n<!-- Sample response: X-Content-Type-Options is absent. -->',
  cookie: 'HTTP/1.1 200 OK\nSet-Cookie: session=[sample-redacted]; Secure; SameSite=Lax\n\n# Sample response: HttpOnly is absent.',
  cors: 'HTTP/1.1 200 OK\nAccess-Control-Allow-Origin: *\nContent-Type: application/json\n\n{"example": true}',
};
const escape = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let language = new URLSearchParams(location.search).get('lang') === 'en' ? 'en' : 'ko';
let state = initialState();
let timer = null;
const app = document.querySelector('#app');
const text = () => copy[language];
const button = (action,label,primary=false) => `<button type="button" class="button${primary?' primary':''}" data-action="${action}">${escape(label)}</button>`;
const badge = (label,color='') => `<span class="badge ${color}">${escape(label)}</span>`;
const eventPanel = t => `<section class="panel"><div class="panel-title"><h2>${t.events}</h2></div><p class="eyebrow">${t.eventHint}</p>${state.events.length ? `<ol class="event-log">${state.events.map((id,i)=>`<li><small>${String(i+1).padStart(2,'0')}</small><span>${escape(t.event[id])}</span></li>`).join('')}</ol>` : `<p class="empty">${t.noEvents}</p>`}</section>`;
function progress(t) {
  return `<section class="panel"><div class="panel-title"><h2>${t.execution}</h2>${badge(t.phase[state.phase],state.phase==='completed'?'green':'purple')}</div><progress class="progress" max="3" value="${state.completed.length}" aria-label="${escape(t.metricChecks)}"></progress><div class="progress-label"><span>${state.completed.length} / 3</span><span>${t.metricRequests}: 0</span></div><ul class="checks">${checks.map((id,i)=>`<li><span>${escape(t[id].title)}</span>${badge(state.completed.includes(id)?t.observed:(state.phase==='running'&&i===state.completed.length?t.checking:t.waiting),state.completed.includes(id)?'green':'')}</li>`).join('')}</ul></section>`;
}
function overview(t) {
  const flowIndex = state.retest==='completed'?5:state.remediation?4:state.phase==='completed'?3:state.phase==='running'?2:state.phase==='pending'?1:0;
  return `<div class="page-head"><div><p class="eyebrow">${t.startHint}</p><h1>${t.title}</h1><p>${t.intro}</p></div>${badge(t.phase[state.phase],'purple')}</div>
    <div class="metrics">${[[t.metricAssets,'1',t.sample],[t.metricChecks,String(state.completed.length),t.stepsUnit],[t.metricFindings,String(state.findings.filter(f=>f.status==='open').length),t.sample],[t.metricRequests,'0',t.requestsNote]].map(([label,value,note])=>`<div class="metric"><span>${label}</span><strong>${value}</strong><small>${note}</small></div>`).join('')}</div>
    <div class="grid"><div><section class="panel"><div class="panel-title"><h2>${t.assetTitle}</h2></div><div class="asset"><span class="asset-icon" aria-hidden="true">S</span><div><strong>${t.assetName}</strong><code>https://shop-demo.example/</code></div>${badge(t.assetBadge,'green')}</div><p class="explanation">${t.assetNote}</p><div class="actions">${state.phase==='idle'?button('draft',t.draft,true):button('plan',t.toPlan,true)}${state.findings.length?button('findings',t.toFindings):''}</div></section>${eventPanel(t)}</div><section class="panel purple"><div class="panel-title"><h2>${t.flowTitle}</h2></div><ol class="flow">${t.flow.map((title,i)=>`<li class="${i<flowIndex?'done':i===flowIndex?'active':''}"><span class="number">${i<flowIndex?'✓':String(i+1).padStart(2,'0')}</span><div><strong>${title}</strong><small>${t.flowNotes[i]}</small></div></li>`).join('')}</ol></section></div>`;
}
function plan(t) {
  if (state.phase==='idle') return `<div class="page-head"><div><h1>${t.planTitle}</h1><p>${t.planIntro}</p></div></div><section class="panel"><p>${t.idleNote}</p>${button('draft',t.draft,true)}</section>`;
  const note = {pending:t.pendingNote,running:t.runningNote,completed:t.doneNote,interrupted:t.stoppedNote}[state.phase];
  const action = {pending:button('approve',t.approve,true),running:button('cancel',t.cancel),completed:button('findings',t.toFindings,true),interrupted:button('resume-draft',t.resume,true)}[state.phase];
  return `<div class="page-head"><div><h1>${t.planTitle}</h1><p>${t.planIntro}</p></div>${badge(t.phase[state.phase],'purple')}</div><div class="grid"><div><section class="panel"><div class="panel-title"><h2>${t.planPanel}</h2></div><dl class="scope"><dt>${t.scope}</dt><dd><code>https://shop-demo.example/</code></dd><dt>${t.method}</dt><dd>GET</dd><dt>${t.budget}</dt><dd>${t.budgetValue}</dd><dt>${t.policy}</dt><dd>${t.policyValue}</dd></dl><p class="explanation">${note}</p><div class="actions">${action}</div></section>${progress(t)}</div>${eventPanel(t)}</div>`;
}
function findings(t) {
  if (!state.findings.length) return `<div class="page-head"><div><h1>${t.findingsTitle}</h1><p>${t.findingsIntro}</p></div></div><section class="panel"><p>${t.noFindings}</p>${button(state.phase==='idle'?'draft':'plan',state.phase==='idle'?t.draft:t.toPlan,true)}</section>`;
  const finding = state.findings.find(f=>f.id===state.selected) || state.findings[0];
  const info = t[finding.id];
  let remediation = '';
  if (finding.id==='headers' && state.phase==='completed') {
    if (!state.remediation) remediation = `<div class="retest-card"><p>${t.remediationNote}</p>${button('remediate',t.remediation,true)}</div>`;
    else if (state.retest===null) remediation = `<div class="retest-card"><p>${t.remediationNote}</p>${button('retest-draft',t.retestDraft,true)}</div>`;
    else if (state.retest==='pending') remediation = `<div class="retest-card"><h3>${t.retestTitle}</h3><p>${t.retestNote}</p>${button('retest-approve',t.retestApprove,true)}</div>`;
    else if (state.retest==='running') remediation = `<div class="retest-card"><strong>${t.retesting}</strong><p>${t.runningNote}</p></div>`;
    else remediation = `<div class="retest-result"><strong>${t.retestDone}</strong><p>${t.retestProof}</p><pre>${escape('HTTP/1.1 200 OK\nContent-Type: text/html; charset=utf-8\nX-Content-Type-Options: nosniff')}</pre></div>`;
  }
  return `<div class="page-head"><div><h1>${t.findingsTitle}</h1><p>${t.findingsIntro}</p></div>${badge(`${t.metricFindings}: ${state.findings.filter(f=>f.status==='open').length}`,'orange')}</div><div class="grid"><div><section class="panel"><div class="finding-list">${state.findings.map(f=>`<button type="button" class="finding-item" data-action="select" data-id="${f.id}" aria-pressed="${f.id===finding.id}"><strong>${escape(t[f.id].title)}</strong><span class="finding-meta">${badge(f.id==='cors'?t.low:t.medium,'orange')}${badge(f.status==='resolved'?t.resolved:t.open,f.status==='resolved'?'green':'')}</span></button>`).join('')}</div></section>${eventPanel(t)}</div><section class="panel evidence"><div class="panel-title"><h2>${escape(info.title)}</h2></div><p>${badge(t.original,'purple')}</p><h3>${t.request}</h3><pre>${escape(`GET ${finding.id==='cors'?'/api/catalog':'/'} HTTP/1.1\nHost: shop-demo.example\n${finding.id==='cors'?'Origin: https://console.example\n':''}`)}</pre><h3>${t.response}</h3><pre>${escape(responses[finding.id])}</pre><h3>${t.why}</h3><p class="explanation">${escape(info.why)}</p><h3>${t.fix}</h3><p class="explanation">${escape(info.fix)}</p>${remediation}</section></div>`;
}
function render() {
  const t = text();
  const activeAction = document.activeElement?.dataset.action;
  const activeId = document.activeElement?.dataset.id;
  document.documentElement.lang = language;
  document.title = language==='ko'?'Open Aegis — 체험 데모':'Open Aegis — Interactive demo';
  document.querySelector('#language').textContent = language==='ko'?'English':'한국어';
  document.querySelector('#demo-disclosure').textContent = t.disclosure;
  document.querySelector('#reset-button').textContent = t.reset;
  document.querySelector('#local-label').textContent = t.local;
  document.querySelector('#local-description').textContent = t.localDescription;
  document.querySelector('#back-link').textContent = t.back;
  document.querySelector('#navigation').innerHTML = ['overview','plan','findings'].map(page=>`<button type="button" data-action="${page}" ${state.page===page?'aria-current="page"':''}>${t[page]}<span aria-hidden="true">${page==='findings'?state.findings.length:'↗'}</span></button>`).join('');
  app.innerHTML = ({overview,plan,findings}[state.page])(t);
  if (activeAction) {
    const next = Array.from(document.querySelectorAll('[data-action]')).find(el=>el.dataset.action===activeAction&&el.dataset.id===activeId);
    if (next) next.focus({preventScroll:true});
  }
}
function schedule(type) {
  if (timer!==null) clearTimeout(timer);
  const generation = state.generation;
  timer = setTimeout(() => {
    timer = null;
    apply({type,generation});
    if (type==='tick' && state.phase==='running' && state.generation===generation) schedule('tick');
  }, 1100);
}
function apply(action) {
  const next = transition(state,action);
  if (next===state) return;
  state = next;
  if (['reset','cancel'].includes(action.type) && timer!==null) { clearTimeout(timer); timer=null; }
  render();
  const t = text();
  const eventId = ({approve:'approved', cancel:'cancelled', remediate:'remediation', 'retest-approve':'retest-approved', 'retest-tick':'retest-completed'})[action.type] || action.type;
  document.querySelector('#announcement').textContent = action.type==='reset'?t.reset:(t.event[eventId] || (action.type==='tick'?(state.phase==='completed'?t.event.completed:t.event[state.completed.at(-1)]):''));
  if (action.type==='approve') schedule('tick');
  if (action.type==='retest-approve') schedule('retest-tick');
}
document.addEventListener('click', event => {
  const target = event.target.closest('button[data-action]');
  if (!target) return;
  const action = target.dataset.action;
  if (['overview','plan','findings'].includes(action)) apply({type:'page',page:action});
  else apply({type:action,id:target.dataset.id});
});
document.querySelector('#language').addEventListener('click', () => {
  language = language==='ko'?'en':'ko';
  render();
});
render();
