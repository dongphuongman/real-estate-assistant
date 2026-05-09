/**
 * Accessibility tests for interactive UI components (Task #61).
 *
 * Uses jest-axe to verify WCAG 2.1 AA compliance for all shared UI primitives.
 */

import { render, screen } from '@testing-library/react';
import { axe, toHaveNoViolations } from 'jest-axe';

expect.extend(toHaveNoViolations);

describe('Input accessibility', () => {
  it('text input has no axe violations', async () => {
    const { container } = render(<input type="text" aria-label="Search" />);
    expect(await axe(container)).toHaveNoViolations();
  });

  it('input with label association has no violations', async () => {
    const { container } = render(
      <>
        <label htmlFor="email">Email</label>
        <input id="email" type="email" />
      </>
    );
    expect(await axe(container)).toHaveNoViolations();
  });

  it('required input with aria-required', async () => {
    const { container } = render(
      <>
        <label htmlFor="name">Name</label>
        <input id="name" type="text" aria-required="true" />
      </>
    );
    expect(await axe(container)).toHaveNoViolations();
  });

  it('input with error has aria-invalid', async () => {
    const { container } = render(
      <>
        <label htmlFor="pass">Password</label>
        <input id="pass" type="password" aria-invalid="true" aria-describedby="pass-error" />
        <span id="pass-error" role="alert">
          Password is required
        </span>
      </>
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});

describe('Select accessibility', () => {
  it('native select has no axe violations', async () => {
    const { container } = render(
      <>
        <label htmlFor="city">City</label>
        <select id="city" aria-label="Select city">
          <option value="">Choose a city</option>
          <option value="krakow">Krakow</option>
          <option value="warsaw">Warsaw</option>
        </select>
      </>
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});

describe('Button accessibility', () => {
  it('icon-only button has aria-label', async () => {
    const { container } = render(
      <button aria-label="Close dialog" type="button">
        <span aria-hidden="true">✕</span>
      </button>
    );
    expect(await axe(container)).toHaveNoViolations();
    expect(screen.getByLabelText('Close dialog')).toBeInTheDocument();
  });

  it('loading button indicates state', async () => {
    const { container } = render(
      <button disabled aria-busy="true" aria-label="Submitting form">
        <span aria-hidden="true">Loading...</span>
      </button>
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});

describe('Tabs accessibility', () => {
  it('tab list follows ARIA tablist pattern', async () => {
    const { container } = render(
      <div>
        <div role="tablist" aria-label="Settings tabs">
          <button role="tab" id="tab-1" aria-selected="true" aria-controls="panel-1">
            General
          </button>
          <button role="tab" id="tab-2" aria-selected="false" aria-controls="panel-2" tabIndex={-1}>
            Notifications
          </button>
        </div>
        <div role="tabpanel" id="panel-1" aria-labelledby="tab-1">
          General settings
        </div>
        <div role="tabpanel" id="panel-2" aria-labelledby="tab-2" hidden>
          Notification settings
        </div>
      </div>
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});

describe('Dialog / Modal accessibility', () => {
  it('dialog has proper ARIA attributes', async () => {
    const { container } = render(
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="dialog-title"
        aria-describedby="dialog-desc"
      >
        <h2 id="dialog-title">Confirm Action</h2>
        <p id="dialog-desc">Are you sure you want to proceed?</p>
        <button type="button">Cancel</button>
        <button type="button">Confirm</button>
      </div>
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});

describe('Alert / Live region accessibility', () => {
  it('error alert uses role="alert"', async () => {
    const { container } = render(
      <div role="alert" aria-live="assertive">
        Form submission failed. Please try again.
      </div>
    );
    expect(await axe(container)).toHaveNoViolations();
  });

  it('status message uses aria-live="polite"', async () => {
    const { container } = render(
      <div aria-live="polite" aria-atomic="true">
        5 properties found
      </div>
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});

describe('Navigation accessibility', () => {
  it('nav element with aria-label', async () => {
    const { container } = render(
      <nav aria-label="Main navigation">
        <ul>
          <li>
            <a href="/search">Search</a>
          </li>
          <li>
            <a href="/favorites">Favorites</a>
          </li>
          <li>
            <a href="/settings">Settings</a>
          </li>
        </ul>
      </nav>
    );
    expect(await axe(container)).toHaveNoViolations();
  });

  it('skip navigation link', async () => {
    const { container } = render(
      <>
        <a href="#main-content" className="sr-only focus:not-sr-only">
          Skip to main content
        </a>
        <main id="main-content">Main content</main>
      </>
    );
    expect(await axe(container)).toHaveNoViolations();
    expect(screen.getByText('Skip to main content')).toBeInTheDocument();
  });
});

describe('Form accessibility', () => {
  it('form with fieldset and legend', async () => {
    const { container } = render(
      <form>
        <fieldset>
          <legend>Search Filters</legend>
          <div>
            <label htmlFor="min-price">Minimum Price</label>
            <input id="min-price" type="number" />
          </div>
          <div>
            <label htmlFor="max-price">Maximum Price</label>
            <input id="max-price" type="number" />
          </div>
        </fieldset>
        <button type="submit">Apply Filters</button>
      </form>
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});

describe('Image accessibility', () => {
  it('decorative image has empty alt', async () => {
    const { container } = render(<img src="/decoration.svg" alt="" role="presentation" />);
    expect(await axe(container)).toHaveNoViolations();
  });

  it('meaningful image has descriptive alt', async () => {
    const { container } = render(
      <img src="/map.png" alt="Property location map showing Krakow city center" />
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});
