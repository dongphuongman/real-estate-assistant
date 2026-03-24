/* eslint-disable @typescript-eslint/no-require-imports */
const nextJest = require('next/jest');

const createJestConfig = nextJest({
  // Provide the path to your Next.js app to load next.config.js and .env files in your test environment
  dir: './',
});

const nodeMajor = Number.parseInt(process.versions.node.split('.')[0] ?? '0', 10);

// Add any custom config to be passed to Jest
const config = {
  coverageProvider: 'v8',
  coverageReporters: ['json', 'json-summary', 'text', 'lcov', 'clover'],
  testEnvironment: 'jsdom',
  setupFilesAfterEnv: ['<rootDir>/jest.setup.ts'],
  modulePathIgnorePatterns: ['<rootDir>/.next/'],
  watchPathIgnorePatterns: ['<rootDir>/.next/'],
  ...(nodeMajor >= 22 ? { maxWorkers: 1 } : {}),
  moduleNameMapper: {
    // Handle module aliases (this will be automatically configured for you soon)
    '^@/(.*)$': '<rootDir>/src/$1',
    // Mock next-intl to avoid ESM issues
    '^next-intl$': '<rootDir>/__mocks__/next-intl.tsx',
    '^next-intl/navigation$': '<rootDir>/__mocks__/next-intl-navigation.tsx',
    // Mock next/navigation to avoid ESM issues
    '^next/navigation$': '<rootDir>/__mocks__/next-navigation.tsx',
  },
  // Transform ESM modules from node_modules
  transformIgnorePatterns: [
    'node_modules/(?!(next-intl|use-intl|@radix-ui|lucide-react|recharts|framer-motion)/)',
  ],
  collectCoverage: true,
  collectCoverageFrom: [
    'src/**/*.{js,jsx,ts,tsx}',
    '!src/**/*.d.ts',
    '!src/lib/types.ts',
    '!src/**/layout.tsx',
    '!src/app/tools/page.tsx',
    '!src/app/layout.tsx',
    '!src/app/globals.css',
  ],
  coverageThreshold: {
    global: {
      branches: 70,
      functions: 78,
      lines: 85,
      statements: 85,
    },
  },
};

// createJestConfig is exported this way to ensure that next/jest can load the Next.js config which is async
module.exports = createJestConfig(config);
