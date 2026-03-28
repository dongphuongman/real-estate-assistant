import { axe, toHaveNoViolations } from 'jest-axe';

expect.extend(toHaveNoViolations);

/**
 * Run axe-core accessibility audit on a container element.
 * Returns the results so tests can add custom assertions.
 */
export async function checkA11y(container: HTMLElement) {
  const results = await axe(container);
  expect(results).toHaveNoViolations();
  return results;
}

export { axe };
