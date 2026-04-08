import { MetadataRoute } from 'next';

const BASE_URL = process.env.NEXT_PUBLIC_SITE_URL || 'https://ai-real-estate.example.com';
const LOCALES = ['en', 'pl', 'ru'];

const PUBLIC_PATHS = [
  '', // homepage
  '/search',
  '/chat',
  '/market-trends',
  '/city-overview',
  '/agents',
  '/tools',
  '/knowledge',
];

export default function sitemap(): MetadataRoute.Sitemap {
  const entries: MetadataRoute.Sitemap = [];

  for (const locale of LOCALES) {
    for (const path of PUBLIC_PATHS) {
      entries.push({
        url: `${BASE_URL}/${locale}${path}`,
        lastModified: new Date(),
        changeFrequency: path === '' ? 'daily' : 'weekly',
        priority: path === '' ? 1.0 : path === '/search' ? 0.9 : 0.7,
      });
    }
  }

  return entries;
}
