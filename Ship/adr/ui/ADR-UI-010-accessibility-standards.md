# ADR-UI-010: Accessibility Standards

**Status:** Accepted
**Date:** 2025-01-20
**Technical Area:** Frontend

---

## Context

The platform must be accessible to all users, including those with disabilities, to comply with regulations and ensure inclusive design.

### Business Context
Accessibility requirements:
- Legal compliance (ADA, Section 508)
- Inclusive design for all users
- Enterprise customers may require accessibility
- Broader user base reach
- Better SEO through semantic HTML

### Technical Context
- Next.js web application (ADR-UI-001)
- React Native mobile app (ADR-UI-006)
- shadcn/ui built on Radix (accessible primitives)
- Complex forms and data tables
- Real-time bidding features

### Assumptions
- WCAG 2.1 AA as target standard
- Automated testing catches most issues
- Manual testing for complex interactions
- Progressive enhancement approach

---

## Decision Drivers

- Legal compliance
- User inclusivity
- Testing automation
- Developer experience
- Performance impact

---

## Decision

We will implement WCAG 2.1 Level AA compliance across web and mobile applications, using accessible component primitives (Radix UI) and automated testing tools.

---

## Implementation Notes

### Accessibility Standards

```
WCAG 2.1 AA Compliance Checklist:

1. Perceivable
   - Text alternatives for non-text content
   - Captions for multimedia
   - Content adaptable to different presentations
   - Distinguishable (color contrast, text resize)

2. Operable
   - Keyboard accessible
   - Enough time to read and use content
   - No content that causes seizures
   - Navigable (skip links, focus order, headings)

3. Understandable
   - Readable text
   - Predictable navigation
   - Input assistance (error identification, labels)

4. Robust
   - Compatible with assistive technologies
   - Valid HTML
   - Proper ARIA usage
```

### Component Accessibility Patterns

```tsx
// components/ui/button.tsx - Accessible Button
import * as React from 'react';
import { Slot } from '@radix-ui/react-slot';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  asChild?: boolean;
  loading?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ asChild, loading, disabled, children, ...props }, ref) => {
    const Comp = asChild ? Slot : 'button';

    return (
      <Comp
        ref={ref}
        disabled={disabled || loading}
        aria-disabled={disabled || loading}
        aria-busy={loading}
        {...props}
      >
        {loading ? (
          <>
            <span className="sr-only">Loading</span>
            <Spinner aria-hidden="true" />
          </>
        ) : (
          children
        )}
      </Comp>
    );
  }
);
Button.displayName = 'Button';

// Screen reader only utility
// globals.css
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
```

### Form Accessibility

```tsx
// components/forms/form-field.tsx
import { useId } from 'react';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';

interface FormFieldProps {
  label: string;
  error?: string;
  description?: string;
  required?: boolean;
  children?: React.ReactNode;
}

export function FormField({
  label,
  error,
  description,
  required,
  children,
  ...inputProps
}: FormFieldProps & React.InputHTMLAttributes<HTMLInputElement>) {
  const id = useId();
  const descriptionId = `${id}-description`;
  const errorId = `${id}-error`;

  return (
    <div className="space-y-2">
      <Label htmlFor={id}>
        {label}
        {required && (
          <span className="text-destructive ml-1" aria-hidden="true">*</span>
        )}
        {required && <span className="sr-only">(required)</span>}
      </Label>

      {description && (
        <p id={descriptionId} className="text-sm text-muted-foreground">
          {description}
        </p>
      )}

      {children || (
        <Input
          id={id}
          aria-describedby={
            [description && descriptionId, error && errorId]
              .filter(Boolean)
              .join(' ') || undefined
          }
          aria-invalid={!!error}
          aria-required={required}
          {...inputProps}
        />
      )}

      {error && (
        <p id={errorId} className="text-sm text-destructive" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
```

### Data Table Accessibility

```tsx
// components/ui/data-table.tsx
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

interface DataTableProps<T> {
  data: T[];
  columns: Column<T>[];
  caption?: string;
  onRowClick?: (row: T) => void;
}

export function DataTable<T>({
  data,
  columns,
  caption,
  onRowClick,
}: DataTableProps<T>) {
  return (
    <div className="relative overflow-x-auto" role="region" aria-label={caption}>
      <Table>
        {caption && (
          <caption className="sr-only">{caption}</caption>
        )}
        <TableHeader>
          <TableRow>
            {columns.map((column, index) => (
              <TableHead
                key={column.id}
                scope="col"
                aria-sort={column.sortable ? column.sortDirection : undefined}
              >
                {column.sortable ? (
                  <button
                    className="flex items-center gap-1"
                    onClick={() => column.onSort?.()}
                    aria-label={`Sort by ${column.header}`}
                  >
                    {column.header}
                    <SortIcon direction={column.sortDirection} />
                  </button>
                ) : (
                  column.header
                )}
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {data.map((row, rowIndex) => (
            <TableRow
              key={rowIndex}
              onClick={() => onRowClick?.(row)}
              tabIndex={onRowClick ? 0 : undefined}
              onKeyDown={(e) => {
                if (onRowClick && (e.key === 'Enter' || e.key === ' ')) {
                  e.preventDefault();
                  onRowClick(row);
                }
              }}
              role={onRowClick ? 'button' : undefined}
              aria-label={onRowClick ? `View details for row ${rowIndex + 1}` : undefined}
            >
              {columns.map((column) => (
                <TableCell key={column.id}>
                  {column.cell(row)}
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
```

### Skip Navigation

```tsx
// components/layouts/skip-nav.tsx
export function SkipNav() {
  return (
    <a
      href="#main-content"
      className="sr-only focus:not-sr-only focus:fixed focus:top-4 focus:left-4 focus:z-50 focus:px-4 focus:py-2 focus:bg-primary focus:text-primary-foreground focus:rounded-md"
    >
      Skip to main content
    </a>
  );
}

// app/layout.tsx
export default function Layout({ children }) {
  return (
    <html>
      <body>
        <SkipNav />
        <Header />
        <main id="main-content" tabIndex={-1}>
          {children}
        </main>
        <Footer />
      </body>
    </html>
  );
}
```

### Focus Management

```tsx
// hooks/use-focus-trap.ts
import { useEffect, useRef } from 'react';

export function useFocusTrap<T extends HTMLElement>(isActive: boolean) {
  const containerRef = useRef<T>(null);

  useEffect(() => {
    if (!isActive || !containerRef.current) return;

    const container = containerRef.current;
    const focusableElements = container.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    const firstElement = focusableElements[0] as HTMLElement;
    const lastElement = focusableElements[focusableElements.length - 1] as HTMLElement;

    // Focus first element on open
    firstElement?.focus();

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key !== 'Tab') return;

      if (e.shiftKey) {
        if (document.activeElement === firstElement) {
          e.preventDefault();
          lastElement?.focus();
        }
      } else {
        if (document.activeElement === lastElement) {
          e.preventDefault();
          firstElement?.focus();
        }
      }
    };

    container.addEventListener('keydown', handleKeyDown);
    return () => container.removeEventListener('keydown', handleKeyDown);
  }, [isActive]);

  return containerRef;
}

// Usage in modal
export function Modal({ isOpen, onClose, children }) {
  const containerRef = useFocusTrap<HTMLDivElement>(isOpen);

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent ref={containerRef} aria-modal="true" role="dialog">
        {children}
      </DialogContent>
    </Dialog>
  );
}
```

### Announcements for Dynamic Content

```tsx
// components/ui/live-region.tsx
import { useEffect, useState } from 'react';

interface LiveRegionProps {
  message: string;
  politeness?: 'polite' | 'assertive';
}

export function LiveRegion({ message, politeness = 'polite' }: LiveRegionProps) {
  const [announcement, setAnnouncement] = useState('');

  useEffect(() => {
    if (message) {
      // Clear and re-announce to ensure screen readers pick it up
      setAnnouncement('');
      setTimeout(() => setAnnouncement(message), 100);
    }
  }, [message]);

  return (
    <div
      aria-live={politeness}
      aria-atomic="true"
      className="sr-only"
    >
      {announcement}
    </div>
  );
}

// Usage
function SearchResults({ results, isLoading }) {
  return (
    <>
      <LiveRegion
        message={
          isLoading
            ? 'Loading results...'
            : `${results.length} results found`
        }
      />
      {/* Results list */}
    </>
  );
}
```

### Color Contrast Utilities

```tsx
// lib/accessibility/color-contrast.ts
export function getContrastRatio(color1: string, color2: string): number {
  const lum1 = getLuminance(color1);
  const lum2 = getLuminance(color2);
  const lighter = Math.max(lum1, lum2);
  const darker = Math.min(lum1, lum2);
  return (lighter + 0.05) / (darker + 0.05);
}

export function meetsContrastRequirement(
  foreground: string,
  background: string,
  level: 'AA' | 'AAA' = 'AA',
  isLargeText: boolean = false
): boolean {
  const ratio = getContrastRatio(foreground, background);

  if (level === 'AAA') {
    return isLargeText ? ratio >= 4.5 : ratio >= 7;
  }
  // AA
  return isLargeText ? ratio >= 3 : ratio >= 4.5;
}

// Tailwind plugin for contrast checking
// tailwind.config.ts
const contrastPlugin = plugin(({ addUtilities }) => {
  addUtilities({
    '.text-contrast-check': {
      '--tw-text-contrast': 'var(--foreground)',
      '--tw-bg-contrast': 'var(--background)',
    },
  });
});
```

### Mobile Accessibility (React Native)

```tsx
// components/ui/Button.native.tsx
import { Pressable, Text, AccessibilityInfo } from 'react-native';

interface ButtonProps {
  label: string;
  onPress: () => void;
  disabled?: boolean;
  loading?: boolean;
  hint?: string;
}

export function Button({ label, onPress, disabled, loading, hint }: ButtonProps) {
  const accessibilityState = {
    disabled: disabled || loading,
    busy: loading,
  };

  return (
    <Pressable
      onPress={onPress}
      disabled={disabled || loading}
      accessible={true}
      accessibilityLabel={label}
      accessibilityHint={hint}
      accessibilityState={accessibilityState}
      accessibilityRole="button"
      style={({ pressed }) => [
        styles.button,
        pressed && styles.pressed,
        disabled && styles.disabled,
      ]}
    >
      {loading ? (
        <ActivityIndicator accessibilityLabel="Loading" />
      ) : (
        <Text style={styles.label}>{label}</Text>
      )}
    </Pressable>
  );
}

// Reduce motion preference
import { useReducedMotion } from 'react-native-reanimated';

export function AnimatedComponent() {
  const reducedMotion = useReducedMotion();

  const animationConfig = reducedMotion
    ? { duration: 0 }
    : { duration: 300 };

  return (
    <Animated.View style={[styles.container, animatedStyle]}>
      {/* Content */}
    </Animated.View>
  );
}
```

### Testing Configuration

```tsx
// jest.setup.ts
import '@testing-library/jest-dom';
import { toHaveNoViolations } from 'jest-axe';

expect.extend(toHaveNoViolations);

// Example test
import { render } from '@testing-library/react';
import { axe } from 'jest-axe';

describe('Button', () => {
  it('should have no accessibility violations', async () => {
    const { container } = render(<Button>Click me</Button>);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('should be keyboard accessible', () => {
    const handleClick = jest.fn();
    render(<Button onClick={handleClick}>Click me</Button>);

    const button = screen.getByRole('button');
    button.focus();
    fireEvent.keyDown(button, { key: 'Enter' });

    expect(handleClick).toHaveBeenCalled();
  });
});

// Playwright accessibility testing
// e2e/accessibility.spec.ts
import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test.describe('Accessibility', () => {
  test('home page should have no violations', async ({ page }) => {
    await page.goto('/');

    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa'])
      .analyze();

    expect(results.violations).toEqual([]);
  });

  test('form should be accessible', async ({ page }) => {
    await page.goto('/rfqs/new');

    const results = await new AxeBuilder({ page })
      .include('form')
      .analyze();

    expect(results.violations).toEqual([]);
  });
});
```

### ESLint Configuration

```js
// .eslintrc.js
module.exports = {
  extends: [
    'plugin:jsx-a11y/recommended',
  ],
  plugins: ['jsx-a11y'],
  rules: {
    'jsx-a11y/anchor-is-valid': 'error',
    'jsx-a11y/click-events-have-key-events': 'error',
    'jsx-a11y/no-static-element-interactions': 'error',
    'jsx-a11y/label-has-associated-control': 'error',
  },
};
```

### Dependencies
- ADR-UI-001: Next.js 14+ App Router
- ADR-UI-002: Component Library (shadcn/ui)
- ADR-UI-006: React Native with Expo

### Migration Strategy
1. Set up ESLint accessibility rules
2. Configure axe-core testing
3. Audit existing components
4. Fix critical violations
5. Add ARIA attributes
6. Implement focus management
7. Test with screen readers
8. Document accessibility guidelines

---

## Operational Considerations

### Target WCAG Level

#### Compliance Targets

| Platform | Target Level | Timeline | Notes |
|----------|-------------|----------|-------|
| Web (Buyer Portal) | WCAG 2.1 AA | Launch | Full compliance |
| Web (Supplier Dashboard) | WCAG 2.1 AA | Launch | Full compliance |
| Mobile (iOS) | WCAG 2.1 AA + iOS Guidelines | Launch | VoiceOver optimized |
| Mobile (Android) | WCAG 2.1 AA + Material A11y | Launch | TalkBack optimized |
| Future goal | WCAG 2.2 AA | 2026 Q2 | Adds focus appearance |

#### Success Criteria Priority

| Criterion | Priority | Implementation Status |
|-----------|----------|----------------------|
| 1.1.1 Non-text Content | P0 | Required at launch |
| 1.3.1 Info and Relationships | P0 | Required at launch |
| 1.4.3 Contrast (Minimum) | P0 | Required at launch |
| 2.1.1 Keyboard | P0 | Required at launch |
| 2.4.4 Link Purpose | P0 | Required at launch |
| 4.1.2 Name, Role, Value | P0 | Required at launch |
| 1.4.4 Resize Text | P1 | Required at launch |
| 2.4.7 Focus Visible | P1 | Required at launch |
| 1.4.11 Non-text Contrast | P2 | Post-launch |
| 2.5.5 Target Size | P2 | Post-launch (44px mobile) |

### Testing Tooling

#### Automated Testing Stack

| Tool | Purpose | Stage | Configuration |
|------|---------|-------|---------------|
| **jest-axe** | Unit test a11y | Pre-commit | All component tests |
| **eslint-plugin-jsx-a11y** | Static analysis | Pre-commit | Error level |
| **@axe-core/playwright** | E2E a11y | CI/CD | Critical paths |
| **Lighthouse CI** | Page-level audit | CI/CD | Score threshold: 90 |
| **Pa11y** | Automated scanning | Nightly | Full site crawl |

#### Test Configuration

```typescript
// jest.setup.ts
import { toHaveNoViolations } from 'jest-axe';

expect.extend(toHaveNoViolations);

// Configure axe for our specific needs
const axeConfig = {
  rules: {
    // Ensure color contrast meets our stricter requirements
    'color-contrast': { enabled: true },
    // Skip rules handled elsewhere
    'document-title': { enabled: false }, // Tested in E2E
    'html-has-lang': { enabled: false },  // Tested in E2E
  },
};

// Component test example
describe('Button', () => {
  it('meets accessibility standards', async () => {
    const { container } = render(
      <Button onClick={() => {}}>Submit Order</Button>
    );
    const results = await axe(container, axeConfig);
    expect(results).toHaveNoViolations();
  });
});
```

```typescript
// playwright/accessibility.spec.ts
import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test.describe('Accessibility', () => {
  const criticalPages = [
    { path: '/', name: 'Home' },
    { path: '/catalog', name: 'Catalog' },
    { path: '/rfqs/new', name: 'Create RFQ' },
    { path: '/orders', name: 'Orders' },
    { path: '/login', name: 'Login' },
  ];

  for (const page of criticalPages) {
    test(`${page.name} page has no a11y violations`, async ({ page: p }) => {
      await p.goto(page.path);

      const results = await new AxeBuilder({ page: p })
        .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
        .exclude('.third-party-widget') // Exclude uncontrolled content
        .analyze();

      expect(results.violations).toEqual([]);
    });
  }
});
```

#### CI Pipeline Integration

```yaml
# .github/workflows/accessibility.yml
name: Accessibility Checks

on: [pull_request]

jobs:
  a11y-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install dependencies
        run: npm ci

      - name: Run ESLint a11y rules
        run: npm run lint:a11y

      - name: Run jest-axe tests
        run: npm run test:a11y

      - name: Build application
        run: npm run build

      - name: Run Playwright a11y tests
        run: npm run test:e2e:a11y

      - name: Run Lighthouse CI
        uses: treosh/lighthouse-ci-action@v10
        with:
          configPath: ./lighthouserc.json
          uploadArtifacts: true

      - name: Comment a11y report
        uses: actions/github-script@v6
        with:
          script: |
            // Post accessibility summary as PR comment
```

### Localization Support

#### Internationalization Requirements

| Requirement | Implementation | Testing |
|-------------|---------------|---------|
| RTL support | CSS logical properties | Visual regression |
| Text expansion | Flexible layouts, no truncation | German locale test |
| Unicode support | UTF-8 throughout | CJK character tests |
| Number formatting | Intl.NumberFormat | Currency + date tests |
| Screen reader languages | lang attribute per element | Manual verification |

```typescript
// components/localized-text.tsx
export function LocalizedText({ children, lang }: LocalizedTextProps) {
  return (
    <span lang={lang} dir={lang === 'ar' || lang === 'he' ? 'rtl' : 'ltr'}>
      {children}
    </span>
  );
}

// CSS with logical properties for RTL support
.card {
  padding-inline-start: var(--spacing-4);  /* Not padding-left */
  margin-inline-end: var(--spacing-2);     /* Not margin-right */
  border-inline-start: 2px solid;          /* Not border-left */
}
```

### Font Scaling

#### Scaling Requirements

| Platform | Min Scale | Max Scale | Implementation |
|----------|-----------|-----------|----------------|
| Web | 100% | 200% | rem units, responsive breakpoints |
| iOS | 100% | 310% | Dynamic Type support |
| Android | 100% | 200% | sp units for text |

#### Web Implementation

```css
/* Base styles using rem for scaling */
:root {
  font-size: 16px; /* User can change browser settings */
}

body {
  font-size: 1rem;
  line-height: 1.5;
}

/* Minimum touch targets at any scale */
.interactive {
  min-height: 44px;
  min-width: 44px;
}

/* Test at 200% zoom */
@media (min-resolution: 2dppx) {
  /* Adjustments for high-density displays */
}
```

#### Mobile Implementation

```typescript
// React Native Dynamic Type support
import { Text, PixelRatio } from 'react-native';

// Respect system font scaling
const fontScale = PixelRatio.getFontScale();

// Limit extreme scaling for layout stability
const constrainedScale = Math.min(Math.max(fontScale, 0.8), 1.5);

// Accessible text component
export function AccessibleText({ style, ...props }) {
  return (
    <Text
      style={[style, { fontSize: style.fontSize * constrainedScale }]}
      allowFontScaling={true}
      maxFontSizeMultiplier={1.5} // Prevent breaking layouts
      {...props}
    />
  );
}
```

### Keyboard Navigation

#### Navigation Requirements

| Area | Tab Order | Shortcuts | Focus Management |
|------|-----------|-----------|------------------|
| Global nav | Left to right | Alt+1-9 for main sections | Skip link to main |
| Forms | Top to bottom | Enter to submit | First field on open |
| Modals | Trapped focus | Escape to close | Return focus on close |
| Data tables | Row by row | Arrow keys for cells | Announce row/column |
| Search | Input first | / to focus search | Results announced |

#### Implementation Patterns

```typescript
// Skip navigation link
export function SkipLink() {
  return (
    <a
      href="#main-content"
      className="sr-only focus:not-sr-only focus:fixed focus:top-4 focus:left-4 focus:z-50 focus:px-4 focus:py-2 focus:bg-primary focus:text-primary-foreground focus:rounded-md"
    >
      Skip to main content
    </a>
  );
}

// Focus trap for modals
export function Modal({ isOpen, onClose, children }) {
  const modalRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isOpen) return;

    const modal = modalRef.current;
    const focusableElements = modal?.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    const firstElement = focusableElements?.[0] as HTMLElement;
    const lastElement = focusableElements?.[focusableElements.length - 1] as HTMLElement;

    // Focus first element
    firstElement?.focus();

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
        return;
      }

      if (e.key === 'Tab') {
        if (e.shiftKey && document.activeElement === firstElement) {
          e.preventDefault();
          lastElement?.focus();
        } else if (!e.shiftKey && document.activeElement === lastElement) {
          e.preventDefault();
          firstElement?.focus();
        }
      }
    };

    modal?.addEventListener('keydown', handleKeyDown);
    return () => modal?.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  return (
    <div ref={modalRef} role="dialog" aria-modal="true">
      {children}
    </div>
  );
}

// Keyboard shortcuts registry
const keyboardShortcuts = {
  '/': { action: 'focusSearch', description: 'Focus search' },
  'g h': { action: 'goHome', description: 'Go to home' },
  'g o': { action: 'goOrders', description: 'Go to orders' },
  'g r': { action: 'goRfqs', description: 'Go to RFQs' },
  '?': { action: 'showShortcuts', description: 'Show shortcuts' },
};
```

### Accessibility Audit Schedule

| Audit Type | Frequency | Scope | Performed By |
|------------|-----------|-------|--------------|
| Automated (CI) | Every PR | Changed components | Automated tooling |
| Component review | Weekly | New/modified components | Design System Team |
| Page-level audit | Monthly | All critical paths | QA Team |
| Expert review | Quarterly | Full application | External consultant |
| User testing | Semi-annually | End-to-end flows | Users with disabilities |

### Open Questions - Resolved

- **Q:** How often will accessibility audits be scheduled?
  - **A:** We implement a tiered audit schedule:
    1. **Continuous (automated)**: Every PR runs jest-axe, eslint-plugin-jsx-a11y, and Playwright axe-core tests
    2. **Weekly**: Design System Team reviews all new/modified components
    3. **Monthly**: QA team performs manual audit of critical user paths (catalog, RFQ creation, checkout, order tracking)
    4. **Quarterly**: External accessibility consultant performs comprehensive audit with assistive technology testing (NVDA, JAWS, VoiceOver, TalkBack)
    5. **Semi-annually**: User testing sessions with participants who have disabilities (visual, motor, cognitive)
    6. **On-demand**: Any accessibility bugs reported are P1 priority and trigger immediate review

---

## References
- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [Radix UI Accessibility](https://www.radix-ui.com/docs/primitives/overview/accessibility)
- [React Native Accessibility](https://reactnative.dev/docs/accessibility)
- [axe-core](https://github.com/dequelabs/axe-core)
