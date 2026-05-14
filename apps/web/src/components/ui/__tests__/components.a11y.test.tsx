/**
 * Component-level a11y tests for key UI primitives (Task #61).
 *
 * Tests actual rendered components against WCAG 2.1 AA rules using jest-axe.
 */

import { render } from '@testing-library/react';
import { axe, toHaveNoViolations } from 'jest-axe';

import { Badge } from '../badge';
import { Progress } from '../progress';
import { Separator } from '../separator';
import { Skeleton } from '../skeleton';

expect.extend(toHaveNoViolations);

describe('Badge a11y', () => {
  it('has no axe violations', async () => {
    const { container } = render(<Badge>Test Badge</Badge>);
    expect(await axe(container)).toHaveNoViolations();
  });
});

describe('Progress a11y', () => {
  it('has accessible progressbar role with correct ARIA attributes', async () => {
    const { container } = render(<Progress value={65} aria-label="Upload progress" />);
    expect(await axe(container)).toHaveNoViolations();

    const progressbar = container.querySelector("[role='progressbar']");
    expect(progressbar).toBeTruthy();
    expect(progressbar?.getAttribute('aria-valuenow')).toBe('65');
    expect(progressbar?.getAttribute('aria-valuemin')).toBe('0');
    expect(progressbar?.getAttribute('aria-valuemax')).toBe('100');
  });

  it('zero value progress has no violations', async () => {
    const { container } = render(<Progress value={0} aria-label="Loading" />);
    expect(await axe(container)).toHaveNoViolations();
  });
});

describe('Skeleton a11y', () => {
  it('has no axe violations', async () => {
    const { container } = render(<Skeleton className="h-4 w-48" />);
    expect(await axe(container)).toHaveNoViolations();
  });
});

describe('Separator a11y', () => {
  it('decorative separator has no axe violations', async () => {
    const { container } = render(<Separator />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
