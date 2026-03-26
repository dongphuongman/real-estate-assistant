import { describe, it, expect } from '@jest/globals';
import {
  locales,
  defaultLocale,
  localeNames,
  localeFlags,
  isValidLocale,
  type Locale,
} from '../config';

describe('i18n config', () => {
  describe('locales', () => {
    it('should contain supported locales', () => {
      expect(locales).toContain('pl');
      expect(locales).toContain('en');
      expect(locales).toContain('ru');
    });

    it('should have exactly 3 locales', () => {
      expect(locales).toHaveLength(3);
    });

    it('should be readonly array', () => {
      expect(Array.isArray(locales)).toBe(true);
    });
  });

  describe('defaultLocale', () => {
    it('should be Polish', () => {
      expect(defaultLocale).toBe('pl');
    });

    it('should be one of the valid locales', () => {
      expect(locales).toContain(defaultLocale);
    });
  });

  describe('localeNames', () => {
    it('should have names for all locales', () => {
      expect(localeNames.pl).toBe('Polski');
      expect(localeNames.en).toBe('English');
      expect(localeNames.ru).toBe('Русский');
    });

    it('should have names for all defined locales', () => {
      locales.forEach((locale) => {
        expect(localeNames[locale]).toBeDefined();
      });
    });
  });

  describe('localeFlags', () => {
    it('should have flags for all locales', () => {
      expect(localeFlags.pl).toBe('🇵🇱');
      expect(localeFlags.en).toBe('🇬🇧');
      expect(localeFlags.ru).toBe('🇷🇺');
    });

    it('should have flags for all defined locales', () => {
      locales.forEach((locale) => {
        expect(localeFlags[locale]).toBeDefined();
      });
    });
  });

  describe('isValidLocale', () => {
    it('should return true for valid locales', () => {
      expect(isValidLocale('pl')).toBe(true);
      expect(isValidLocale('en')).toBe(true);
      expect(isValidLocale('ru')).toBe(true);
    });

    it('should return false for invalid locales', () => {
      expect(isValidLocale('de')).toBe(false);
      expect(isValidLocale('fr')).toBe(false);
      expect(isValidLocale('')).toBe(false);
      expect(isValidLocale('PL')).toBe(false); // case-sensitive
    });
  });

  describe('Locale type', () => {
    it('should be a union of locale strings', () => {
      const validLocale: Locale = 'pl';
      expect(typeof validLocale).toBe('string');
    });
  });
});
