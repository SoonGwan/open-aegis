# Interface languages

The source console, primary README, website and interactive demo default to English.
Korean is available through the console language selector, [README.ko.md](../README.ko.md),
[/ko/](https://aegis.no-money-do-you-have-money.com/ko/) and the
[localized demo](https://aegis.no-money-do-you-have-money.com/demo/?lang=ko).
The signed v1.0.0 bundle predates this source update; it has not been replaced or retagged.

## Console

`web/src/i18n-core.ts` translates explicitly marked interface strings. The original
Korean messages are stable keys; `web/src/locales/en.ts` contains the 1,744 extracted interface messages plus known server catalog
labels and sign-in feedback. `{0}`, `{1}`, etc. interpolate values without recursively translating
them. `localizeLabels` supplies language-sensitive static label tables.

The selector saves only `aegis-ui-locale` in browser storage. Unavailable storage
still permits switching during the current session. The default is English, including
for invalid preferences. Other tabs receive preference changes through the storage
event. Forms and active requests are not remounted by a language change. Dates use
the selected language's formatting locale.

Stored asset names, notes, goals, evidence, original responses, provider drafts and
historical server records retain their original language. This is interface
localization, not machine translation of user data or evidence. Some backend-generated
messages and older records can remain Korean; translations must not rewrite them.

## Add a locale

1. Add a catalog under `web/src/locales/`, keeping the same message keys and placeholder sets.
2. Register its locale in `Locale`, `supportedLocales`, validation, formatting and catalog lookup in `i18n-core.ts`.
3. Add its visible option in `i18n.tsx`; keep a valid English fallback for missing translations.
4. Translate website/demo copy separately and add language links and metadata.
5. Verify translated messages, preference recovery and switching with an unfinished form.

Run `npm test --prefix web` and `npm run build --prefix web` using Node.js 22.
Catalog tests verify that substitutions are preserved and English messages contain
no untranslated Korean interface text. This does not assert that arbitrary stored
records are English.
