// Mock for next-intl to avoid ESM issues in Jest
import React from 'react';

export const useTranslations = () => {
  return (key: string) => key;
};

export const useFormatter = () => ({
  dateTime: (value: Date | number) => new Date(value).toLocaleDateString(),
  number: (value: number) => value.toLocaleString(),
});

export const useLocale = () => 'en';
export const useMessages = () => ({});
export const useNow = () => new Date();
export const useTimeZone = () => 'UTC';

export const NextIntlClientProvider: React.FC<{
  children: React.ReactNode;
  messages?: Record<string, unknown>;
}> = ({ children }) => {
  return <>{children}</>;
};

const nextIntlMock = {
  useTranslations,
  useFormatter,
  useLocale,
  useMessages,
  useNow,
  useTimeZone,
  NextIntlClientProvider,
};

export default nextIntlMock;
