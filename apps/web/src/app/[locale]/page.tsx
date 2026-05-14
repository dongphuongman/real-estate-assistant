import { useTranslations } from 'next-intl';
import { HomeCTAs } from '@/components/home/HomeCTAs';

export default function Home() {
  const t = useTranslations('home');

  return (
    <div className="flex flex-col items-center justify-center min-h-[calc(100vh-4rem)] bg-background">
      <div className="container px-4 md:px-6 flex flex-col items-center text-center space-y-4">
        <h1 className="text-4xl font-bold tracking-tighter sm:text-5xl md:text-6xl lg:text-7xl">
          {t('title')}
        </h1>
        <p className="mx-auto max-w-[700px] text-muted-foreground md:text-xl">{t('subtitle')}</p>
        <HomeCTAs />
      </div>
    </div>
  );
}
