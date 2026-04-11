export const locales = ['pl', 'en', 'ru', 'de', 'es', 'it', 'pt', 'tr', 'uk'] as const;
export const defaultLocale = 'pl' as const;

export type Locale = (typeof locales)[number];

export const localeNames: Record<Locale, string> = {
  pl: 'Polski',
  en: 'English',
  ru: 'Русский',
  de: 'Deutsch',
  es: 'Español',
  it: 'Italiano',
  pt: 'Português',
  tr: 'Türkçe',
  uk: 'Українська',
};

export const localeFlags: Record<Locale, string> = {
  pl: '🇵🇱',
  en: '🇬🇧',
  ru: '🇷🇺',
  de: '🇩🇪',
  es: '🇪🇸',
  it: '🇮🇹',
  pt: '🇵🇹',
  tr: '🇹🇷',
  uk: '🇺🇦',
};

/** RTL locales that require right-to-left layout */
export const rtlLocales: readonly Locale[] = [] as const;

/** Check if a locale uses RTL layout */
export function isRTL(locale: string): boolean {
  return (rtlLocales as readonly string[]).includes(locale);
}

/**
 * Validates if a string is a valid locale
 */
export function isValidLocale(locale: string): locale is Locale {
  return locales.includes(locale as Locale);
}
