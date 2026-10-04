/* Only injected by the disposable loopback QA launcher; never a product entry. */
const originalFetch = window.fetch.bind(window);
const heldNotes = [];
let released = 0;
let changes = 0;
let failNextNote = false;
const holdAuth = new URLSearchParams(location.search).get('hold_auth') === '1';
const heldAuth = [];
let authRequests = 0;
const panel = document.createElement('section');
panel.className = 'panel';
panel.style.cssText = 'margin:16px;padding:16px;position:relative;z-index:1001';
panel.setAttribute('aria-label', '합성 세션 검수 제어');
panel.innerHTML = '<strong>임시 실제 앱 세션 검수</strong><p>노트는 실제 저장하고 응답만 지연합니다. 새 문서를 열면 지연 응답은 사라집니다. 모달에서도 F8: 오래된 응답 해제, F9: 서버 로그아웃, F7: 다음 노트 요청을 전송 전 합성 503으로 거절.</p><p id="session-review-metrics" role="status"></p><button type="button" id="session-review-revoke">현재 세션 서버 로그아웃</button> <button type="button" id="session-review-release">가장 오래된 노트 응답 해제</button>';
document.body.prepend(panel);
if (holdAuth) {
  const burst = document.createElement('button');
  burst.textContent = '인증 폼 연속 제출 검수';
  burst.onclick = () => {
    const form = document.querySelector('.auth-card form');
    form?.requestSubmit();
    form?.requestSubmit();
  };
  const release = document.createElement('button');
  release.textContent = '가장 오래된 인증 응답 해제';
  release.onclick = () => { heldAuth.shift()?.(); render(); };
  panel.append(burst, release);
}
function render() {
  document.getElementById('session-review-metrics').textContent =
    `지연 응답: ${heldNotes.length} · 해제: ${released} · 목록 갱신 이벤트: ${changes}` +
    (holdAuth ? ` · 인증 HTTP 요청: ${authRequests} · 지연 인증 응답: ${heldAuth.length}` : '');
}
window.addEventListener('aegis-records-changed', () => { changes++; render(); });
window.fetch = async (input, init) => {
  if (String(input) === '/api/notes' && init?.method === 'POST' && failNextNote) {
    failNextNote = false;
    return new Response(JSON.stringify({detail:'합성 503: 내용을 유지하고 다시 저장하세요.'}),
      {status:503,headers:{'Content-Type':'application/json'}});
  }
  const auth = holdAuth && ['/api/auth/login','/api/auth/setup'].includes(String(input)) && init?.method === 'POST';
  if (auth) { authRequests++; render(); }
  const response = await originalFetch(input, init);
  if (auth) return new Promise(resolve => { heldAuth.push(() => resolve(response)); render(); });
  if (String(input) === '/api/notes' && init?.method === 'POST' && response.ok) {
    return new Promise(resolve => { heldNotes.push(() => resolve(response)); render(); });
  }
  return response;
};
async function revoke() {
  const response = await originalFetch('/api/auth/logout', {method:'POST', credentials:'same-origin'});
  if (!response.ok) throw new Error('Owned fixture logout failed');
  // The app's real periodic read detects 401; do not dispatch a fake expiry event.
}
function releaseOldest() {
  const release = heldNotes.shift();
  if (release) { released++; release(); render(); }
}
document.getElementById('session-review-revoke').onclick = revoke;
document.getElementById('session-review-release').onclick = releaseOldest;
document.addEventListener('keydown', event => {
  if (event.key === 'F8') { event.preventDefault(); releaseOldest(); }
  if (event.key === 'F9') { event.preventDefault(); void revoke(); }
  if (event.key === 'F7') { event.preventDefault(); failNextNote = true; }
});
render();
