'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useTranslations, useLocale } from 'next-intl';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { UserMenu } from '@/components/auth/UserMenu';
import { LanguageSwitcher } from '@/components/ui/language-switcher';
import { useAuth } from '@/contexts/AuthContext';
import {
  BarChart3,
  BookOpen,
  Building2,
  FileText,
  Heart,
  Lock,
  MessageSquare,
  Moon,
  Search,
  Settings,
  Sun,
  Globe,
  Users,
  type LucideIcon,
} from 'lucide-react';

const THEME_STORAGE_KEY = 'theme';

// Routes accessible in demo mode without auth
const DEMO_OPEN_ROUTES = new Set(['/search', '/city-overview', '/knowledge']);
// Routes completely hidden in demo mode
const DEMO_HIDDEN_ROUTES = new Set(['/settings']);

interface RouteConfig {
  href: string;
  label: string;
  icon: LucideIcon;
}

export function MainNav() {
  const pathname = usePathname();
  const locale = useLocale();
  const t = useTranslations('nav');
  const tDemo = useTranslations('demo');
  const tCommon = useTranslations('common');
  const { isDemoMode } = useAuth();

  const routes: RouteConfig[] = [
    {
      href: '/search',
      label: t('search'),
      icon: Search,
    },
    {
      href: '/favorites',
      label: t('favorites'),
      icon: Heart,
    },
    {
      href: '/documents',
      label: t('documents'),
      icon: FileText,
    },
    {
      href: '/city-overview',
      label: t('cities'),
      icon: Globe,
    },
    {
      href: '/chat',
      label: t('assistant'),
      icon: MessageSquare,
    },
    {
      href: '/analytics',
      label: t('analytics'),
      icon: BarChart3,
    },
    {
      href: '/agents',
      label: t('agents'),
      icon: Users,
    },
    {
      href: '/knowledge',
      label: t('knowledge'),
      icon: BookOpen,
    },
    {
      href: '/settings',
      label: t('settings'),
      icon: Settings,
    },
  ];

  const isActiveRoute = (href: string) => {
    const pathWithoutLocale = pathname.replace(/^\/(pl|en|ru)/, '') || '/';
    return pathWithoutLocale === href || (href !== '/' && pathWithoutLocale.startsWith(href));
  };

  const isLocked = (href: string) => isDemoMode && !DEMO_OPEN_ROUTES.has(href);
  const isHidden = (href: string) => isDemoMode && DEMO_HIDDEN_ROUTES.has(href);

  const toggleTheme = () => {
    const isDark = document.documentElement.classList.contains('dark');
    const next = isDark ? 'light' : 'dark';
    window.localStorage.setItem(THEME_STORAGE_KEY, next);
    document.documentElement.classList.toggle('dark', !isDark);
  };

  return (
    <nav aria-label={t('mainNavigation')} className="flex items-center w-full">
      {/* Logo - fixed on the left */}
      <Link
        href={`/${locale}`}
        className="hidden md:flex items-center gap-2 font-bold text-xl hover:opacity-80 transition-opacity shrink-0 mr-6"
      >
        <Building2 className="w-6 h-6 text-primary" aria-hidden="true" />
        <span>AI Estate</span>
      </Link>

      {/* Centered navigation links */}
      <div className="flex items-center justify-center flex-1 space-x-4 lg:space-x-6">
        {routes
          .filter((route) => !isHidden(route.href))
          .map((route) => {
            const locked = isLocked(route.href);
            return (
              <Link
                key={route.href}
                href={locked ? `/${locale}/auth/login` : `/${locale}${route.href}`}
                aria-current={!locked && isActiveRoute(route.href) ? 'page' : undefined}
                title={locked ? tDemo('lockedFeature') : undefined}
                className={cn(
                  'text-sm font-medium transition-colors hover:text-primary flex items-center gap-x-1.5 whitespace-nowrap',
                  isActiveRoute(route.href) ? 'text-foreground' : 'text-muted-foreground',
                  locked && 'opacity-60'
                )}
              >
                <route.icon className="w-4 h-4" aria-hidden="true" />
                {route.label}
                {locked && <Lock className="w-3 h-3 text-muted-foreground" aria-hidden="true" />}
              </Link>
            );
          })}
      </div>

      {/* Right-side controls */}
      <div className="flex items-center gap-2 shrink-0 ml-4">
        <LanguageSwitcher />
        <Button
          type="button"
          variant="ghost"
          size="icon"
          onClick={toggleTheme}
          aria-label={tCommon('toggleTheme')}
        >
          <Sun className="h-4 w-4 hidden dark:block" aria-hidden="true" />
          <Moon className="h-4 w-4 block dark:hidden" aria-hidden="true" />
        </Button>
        <UserMenu />
      </div>
    </nav>
  );
}
