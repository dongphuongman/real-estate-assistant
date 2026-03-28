import { render } from '@testing-library/react';
import { axe } from 'jest-axe';
import { toHaveNoViolations } from 'jest-axe';
import { Button } from '../button';

expect.extend(toHaveNoViolations);

describe('Button accessibility', () => {
  it('default button has no axe violations', async () => {
    const { container } = render(<Button>Click me</Button>);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('destructive variant has no axe violations', async () => {
    const { container } = render(<Button variant="destructive">Delete</Button>);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('disabled button has no axe violations', async () => {
    const { container } = render(<Button disabled>Disabled</Button>);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('button as link (asChild) has no axe violations', async () => {
    const { container } = render(
      <Button asChild>
        <a href="https://example.com">Link Button</a>
      </Button>
    );
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
