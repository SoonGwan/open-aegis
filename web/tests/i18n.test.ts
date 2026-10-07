import { test, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import { t, setLocale, getLocale, getFormatLocale, readLocale, subscribeLocale, localizeLabels, LOCALE_STORAGE_KEY } from '../src/i18n-core.ts';
import english from '../src/locales/en.ts';
afterEach(() => setLocale('en'));
test('English is the default even when preferences are invalid or unavailable', () => {
  assert.equal(getLocale(), 'en');
  assert.equal(readLocale(), 'en');
  assert.equal(readLocale({ getItem: () => 'fr' }), 'en');
  assert.equal(readLocale({ getItem: () => { throw Error('blocked'); } }), 'en');
  assert.equal(readLocale({ getItem: key => key === LOCALE_STORAGE_KEY ? 'ko' : null }), 'ko');
  assert.equal(t('실행 승인'), 'Execution approvals');
});
test('Korean selection persists, notifies subscribers, and changes date formatting', () => {
  const saved: string[][] = []; let calls = 0;
  const unsubscribe = subscribeLocale(() => calls++);
  setLocale('ko', { setItem: (key, value) => { saved.push([key, value]); } });
  assert.equal(t('실행 승인'), '실행 승인');
  assert.equal(getFormatLocale(), 'ko-KR');
  assert.deepEqual(saved, [[LOCALE_STORAGE_KEY, 'ko']]);
  assert.equal(calls, 1); unsubscribe(); setLocale('en');
  assert.equal(calls, 1); assert.equal(getFormatLocale(), 'en-US');
});
test('blocked preference writes do not prevent changing language', () => {
  setLocale('ko', { setItem: () => { throw Error('quota'); } });
  assert.equal(getLocale(), 'ko'); assert.equal(t('발견 사항'), '발견 사항');
});
test('interpolation preserves user values and missing parameters literally', () => {
  assert.equal(t('{0}개 항목', ['사용자 {1}']), '사용자 {1} items');
  assert.equal(t('{0}개 항목'), '{0} items');
  assert.equal(t('unregistered record text 사용자'), 'unregistered record text 사용자');
});
test('static nested label tables update without rebuilding or mutating their data', () => {
  const icon = { $$typeof: Symbol('react'), label: '발견 사항' };
  const source = { label: '발견 사항', nested: [{ label: '실행 승인' }], icon, count: 4 };
  const labels = localizeLabels(source);
  assert.equal(labels.label, 'Findings'); assert.equal(labels.nested[0].label, 'Execution approvals');
  assert.equal(labels.icon, icon); assert.equal(labels.count, 4);
  setLocale('ko'); assert.equal(labels.label, '발견 사항');
  assert.equal(source.label, '발견 사항'); assert.equal(localizeLabels(source), labels);
});
test('the complete catalog contains English messages and preserves all substitution slots', () => {
  assert.ok(Object.keys(english).length >= 1744);
  for (const [source, translated] of Object.entries(english)) {
    assert.ok(translated.trim().length > 0, source);
    assert.doesNotMatch(translated, /[가-힣]/, source);
    const slots = (text: string) => [...new Set(text.match(/\{\d+\}/g) ?? [])].sort();
    assert.deepEqual(slots(translated), slots(source), source);
  }
});
