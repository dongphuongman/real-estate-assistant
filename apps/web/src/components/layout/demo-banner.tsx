'use client';

import Link from 'next/link';
import { useLocale, useTranslations } from 'next-intl';
import { Info, LogIn } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';

export function DemoBanner() {
  const t = useTranslations('demo');
  const locale = useLocale();
  const { isDemoMode } = useAuth();

  if (!isDemoMode) return null;

  return (
    <div className="bg-primary/10 border-b border-primary/20 text-sm">
      <div className="container mx-auto flex items-center justify-between px-4 py-2">
        <div className="flex items-center gap-2 text-primary">
          <Info className="w-4 h-4" aria-hidden="true" />
          <span>{t('banner')}</span>
        </div>
        <Link
          href={`/${locale}/auth/login`}
          className="inline-flex items-center gap-1.5 rounded-md bg-primary px-3 py-1 text-xs font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
        >
          <LogIn className="w-3.5 h-3.5" aria-hidden="true" />
          {t('login')}
        </Link>
      </div>
    </div>
  );
}
