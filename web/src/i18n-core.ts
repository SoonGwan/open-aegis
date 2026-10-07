import english from './locales/en.ts';

export type Locale = 'en' | 'ko';
export const LOCALE_STORAGE_KEY = 'aegis-ui-locale';
export const supportedLocales = ['en', 'ko'] as const;
const listeners = new Set<() => void>();
const isLocale = (value: unknown): value is Locale => value === 'en' || value === 'ko';
export function readLocale(storage?: Pick<Storage, 'getItem'>): Locale {
  try {
    const value = storage?.getItem(LOCALE_STORAGE_KEY);
    return isLocale(value) ? value : 'en';
  } catch { return 'en'; }
}
let current: Locale = typeof window === 'undefined' ? 'en' : (() => {
  try { return readLocale(window.localStorage); } catch { return 'en'; }
})();
export function getLocale(): Locale { return current; }
export function getFormatLocale(): string { return current === 'ko' ? 'ko-KR' : 'en-US'; }
export function subscribeLocale(listener: () => void): () => void {
  listeners.add(listener);
  return () => { listeners.delete(listener); };
}
export function setLocale(value: Locale, storage?: Pick<Storage, 'setItem'>): void {
  if (!isLocale(value)) return;
  current = value;
  try {
    const target = storage ?? (typeof window === 'undefined' ? undefined : window.localStorage);
    target?.setItem(LOCALE_STORAGE_KEY, value);
  } catch { /* An unavailable preference store does not block the UI. */ }
  for (const listener of listeners) listener();
}
if (typeof window !== 'undefined') window.addEventListener('storage', event => {
  if (event.key !== LOCALE_STORAGE_KEY) return;
  current = isLocale(event.newValue) ? event.newValue : 'en';
  for (const listener of listeners) listener();
});
const reverse = new Map<string, string>();
for (const [source, value] of Object.entries(english)) if (!reverse.has(value)) reverse.set(value, source);
/** Translate only explicitly marked system UI messages; never transform record data. */
export function t(source: string, values: readonly unknown[] = []): string {
  const message = current === 'en' ? english[source] ?? source : reverse.get(source) ?? source;
  return message.replace(/\{(\d+)\}/g, (placeholder, index: string) => Number(index) < values.length ? String(values[Number(index)]) : placeholder);
}
const labelCache = new WeakMap<object, object>();
/** Lazy static label tables stay current without remounting forms or active requests. */
export function localizeLabels<T extends object>(labels: T): T {
  const existing = labelCache.get(labels);
  if (existing) return existing as T;
  const proxy = new Proxy(labels, { get(target, property, receiver) {
    const value = Reflect.get(target, property, receiver);
    if (typeof value === 'string') return t(value);
    if (value && typeof value === 'object' && !('$$typeof' in value) && (Array.isArray(value) || Object.getPrototypeOf(value) === Object.prototype)) return localizeLabels(value);
    return value;
  }});
  labelCache.set(labels, proxy);
  return proxy;
}
