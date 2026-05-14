import { defineRouting } from 'next-intl/routing';

export const routing = defineRouting({
  locales: ['pl', 'en', 'ru', 'de', 'es', 'it', 'pt', 'tr', 'uk'],
  defaultLocale: 'pl',
  localePrefix: 'always',
});
