'use client';

import { useTranslations } from 'next-intl';
import { Info } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';

export function DemoBanner() {
  const t = useTranslations('demo');
  const { isDemoMode } = useAuth();

  if (!isDemoMode) return null;

  return (
    <div
      className="bg-primary/10 border-b border-primary/20 text-sm"
      role="status"
      aria-live="polite"
    >
      <div className="container mx-auto flex items-center justify-center px-4 py-2">
        <div className="flex items-center gap-2 text-primary">
          <Info className="w-4 h-4" aria-hidden="true" />
          <span>{t('banner')}</span>
        </div>
      </div>
    </div>
  );
}
