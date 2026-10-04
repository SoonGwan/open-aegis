/* Only injected by the disposable loopback QA launcher; never a product entry. */
const originalFetch = window.fetch.bind(window);
const heldNotes = [];
let released = 0;
let changes = 0;
const panel = document.createElement('section');
panel.className = 'panel';
panel.style.cssText = 'margin:16px;padding:16px;position:relative;z-index:1001';
panel.setAttribute('aria-label', '합성 세션 검수 제어');
panel.innerHTML = '<strong>임시 실제 앱 세션 검수</strong><p>노트는 실제 저장하고 응답만 지연합니다. 새 문서를 열면 지연 응답은 사라집니다. 모달에서도 F8: 오래된 응답 해제, F9: 서버 로그아웃.</p><p id="session-review-metrics" role="status"></p><button type="button" id="session-review-revoke">현재 세션 서버 로그아웃</button> <button type="button" id="session-review-release">가장 오래된 노트 응답 해제</button>';
document.body.prepend(panel);
function render() {
  document.getElementById('session-review-metrics').textContent =
    `지연 응답: ${heldNotes.length} · 해제: ${released} · 목록 갱신 이벤트: ${changes}`;
}
window.addEventListener('aegis-records-changed', () => { changes++; render(); });
window.fetch = async (input, init) => {
  const response = await originalFetch(input, init);
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
});
render();
