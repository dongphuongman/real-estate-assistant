import React from 'react';

export const useTranslations = () => (key: string) => key;
export const useLocale = () => 'en';
export const useMessages = () => ({});
export const NextIntlClientProvider = ({ children }: { children: React.ReactNode }) => (
  <>{children}</>
);
