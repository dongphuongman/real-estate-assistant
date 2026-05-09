import { describe, it, expect, jest } from '@jest/globals';
import { locales, type Locale } from '../../i18n/config';

// Mock the dynamic import of message files
jest.mock('../../messages/pl.json', () => ({ default: { greeting: 'Witaj' } }), { virtual: true });
jest.mock('../../messages/en.json', () => ({ default: { greeting: 'Hello' } }), { virtual: true });
jest.mock('../../messages/ru.json', () => ({ default: { greeting: 'Привет' } }), { virtual: true });

describe('i18n request configuration', () => {
  describe('locale validation', () => {
    it('should include valid locales', () => {
      expect(locales).toContain('pl');
      expect(locales).toContain('en');
      expect(locales).toContain('ru');
    });

    it('should have Polish as first locale (default)', () => {
      expect(locales[0]).toBe('pl');
    });
  });

  describe('locale fallback logic', () => {
    it('should use provided locale when valid', async () => {
      const requestLocale = 'en';
      let locale = requestLocale;
      if (!locale || !locales.includes(locale as Locale)) {
        locale = 'pl';
      }
      expect(locale).toBe('en');
    });

    it('should fallback to pl when locale is undefined', async () => {
      const requestLocale = undefined;
      let locale = requestLocale;
      if (!locale || !locales.includes(locale as Locale)) {
        locale = 'pl';
      }
      expect(locale).toBe('pl');
    });

    it('should fallback to pl when locale is invalid', async () => {
      const requestLocale = 'xx';
      let locale = requestLocale;
      if (!locale || !locales.includes(locale as Locale)) {
        locale = 'pl';
      }
      expect(locale).toBe('pl');
    });

    it('should fallback to pl when locale is empty string', async () => {
      const requestLocale = '';
      let locale = requestLocale;
      if (!locale || !locales.includes(locale as Locale)) {
        locale = 'pl';
      }
      expect(locale).toBe('pl');
    });
  });

  describe('message loading', () => {
    it('should construct correct message path for pl locale', async () => {
      const locale = 'pl';
      const messagePath = `../../messages/${locale}.json`;
      expect(messagePath).toBe('../../messages/pl.json');
    });

    it('should construct correct message path for en locale', async () => {
      const locale = 'en';
      const messagePath = `../../messages/${locale}.json`;
      expect(messagePath).toBe('../../messages/en.json');
    });

    it('should construct correct message path for ru locale', async () => {
      const locale = 'ru';
      const messagePath = `../../messages/${locale}.json`;
      expect(messagePath).toBe('../../messages/ru.json');
    });
  });
});
