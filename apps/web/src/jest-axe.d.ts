declare module 'jest-axe' {
  import type { Result } from 'axe-core';

  interface AxeResults {
    violations: Result[];
    passes: Result[];
    incomplete: Result[];
    inapplicable: Result[];
  }

  function axe(element: Element | string): Promise<AxeResults>;

  const toHaveNoViolations: {
    toHaveNoViolations(): { pass: boolean; message: () => string };
  };

  export { axe, toHaveNoViolations };
}
