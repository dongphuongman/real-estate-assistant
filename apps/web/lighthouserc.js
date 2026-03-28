/** @type {import('@lhci/cli').LhciConfig} */
module.exports = {
  ci: {
    collect: {
      startServerCommand: 'npm run start',
      startServerReadyPattern: 'Ready in',
      url: ['http://localhost:3000/en/search', 'http://localhost:3000/en/chat'],
      numberOfRuns: 3,
      settings: {
        configPath: './lighthouse.config.js',
      },
    },
    assert: {
      assertions: {
        // Category scores
        'categories:performance': ['error', { minScore: 0.9 }],
        'categories:accessibility': ['error', { minScore: 0.9 }],
        'categories:best-practices': ['warn', { minScore: 0.9 }],
        'categories:seo': ['warn', { minScore: 0.8 }],
        // Core Web Vitals
        'first-contentful-paint': ['error', { maxNumericValue: 2000 }],
        'largest-contentful-paint': ['error', { maxNumericValue: 2500 }],
        'cumulative-layout-shift': ['error', { maxNumericValue: 0.1 }],
        'total-blocking-time': ['error', { maxNumericValue: 300 }],
        'speed-index': ['error', { maxNumericValue: 3000 }],
      },
    },
    upload: {
      target: 'temporary-public-storage',
    },
  },
};
