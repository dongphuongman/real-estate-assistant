'use client';

import { Link } from '@/i18n/navigation';
import { useTranslations } from 'next-intl';
import { Info, Sparkles } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';

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
      <div className="container mx-auto flex items-center justify-between px-4 py-2">
        <div className="flex items-center gap-2 text-primary">
          <Info className="w-4 h-4 shrink-0" aria-hidden="true" />
          <span>{t('banner')}</span>
        </div>
        <Button
          variant="ghost"
          size="sm"
          className="text-primary hover:text-primary hover:bg-primary/10 gap-1.5 h-7 text-xs"
          asChild
        >
          <Link href="/auth/register">
            <Sparkles className="w-3.5 h-3.5" aria-hidden="true" />
            {t('signUpCta')}
          </Link>
        </Button>
      </div>
    </div>
  );
}
