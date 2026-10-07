import { useEffect, useSyncExternalStore } from 'react';
import { getLocale, setLocale, subscribeLocale, type Locale } from './i18n-core.ts';

export function useLocale(): Locale {
  const locale = useSyncExternalStore<Locale>(subscribeLocale, getLocale, () => 'en');
  useEffect(() => { document.documentElement.lang = locale; }, [locale]);
  return locale;
}
export function LanguageSwitcher() {
  const locale = useLocale();
  return <label className="language-switcher"><span>{locale === 'en' ? 'Language' : '언어'}</span><select aria-label={locale === 'en' ? 'Interface language' : '화면 언어'} value={locale} onChange={event => setLocale(event.target.value as Locale)}><option value="en">English</option><option value="ko">한국어</option></select></label>;
}
