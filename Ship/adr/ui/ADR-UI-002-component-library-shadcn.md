# ADR-UI-002: Component Library (shadcn/ui)

**Status:** Accepted
**Date:** 2025-01-20
**Technical Area:** Frontend

---

## Context

The platform requires a consistent, accessible component library for building user interfaces across web and admin portals.

### Business Context
UI requirements:
- Consistent look and feel across portals
- Professional, modern appearance
- Accessible to all users
- Fast development velocity
- Customizable for maritime branding

### Technical Context
- Next.js 14 frontend (ADR-UI-001)
- Tailwind CSS for styling
- TypeScript for type safety
- React Server Components compatibility
- Multiple applications sharing components

### Assumptions
- Tailwind CSS preferred for styling
- Component ownership preferred over external dependencies
- Accessibility compliance required
- Team can maintain component library

---

## Decision Drivers

- Accessibility (WCAG compliance)
- Customization flexibility
- Performance
- Developer experience
- Long-term maintainability
- TypeScript support

---

## Considered Options

### Option 1: shadcn/ui
**Description:** Copy-paste components built on Radix UI primitives.

**Pros:**
- Own the code (no external dependency)
- Radix UI for accessibility
- Fully customizable
- Tailwind CSS based
- Excellent TypeScript support
- Active community

**Cons:**
- Manual updates
- Need to maintain components
- Initial setup effort

### Option 2: Material UI (MUI)
**Description:** Popular React component library.

**Pros:**
- Comprehensive component set
- Good documentation
- Large community
- Accessible

**Cons:**
- Opinionated styling
- Bundle size
- CSS-in-JS (Emotion)
- Hard to customize deeply

### Option 3: Chakra UI
**Description:** Accessible component library.

**Pros:**
- Good accessibility
- Easy to use
- Good documentation
- Customizable

**Cons:**
- CSS-in-JS runtime
- Bundle size
- Less control over styling

### Option 4: Custom Components Only
**Description:** Build all components from scratch.

**Pros:**
- Full control
- No dependencies
- Exact fit for needs

**Cons:**
- High development effort
- Accessibility challenges
- Maintenance burden

---

## Decision

**Chosen Option:** shadcn/ui with Radix UI Primitives

We will use shadcn/ui components as our base, customized with our design system. Components are copied into the codebase, giving us full ownership.

### Rationale
shadcn/ui provides beautifully designed, accessible components that we own. Built on Radix UI primitives, they handle complex accessibility requirements. The Tailwind CSS styling aligns with our stack. No external runtime dependencies improve performance.

---

## Consequences

### Positive
- Full component ownership
- Excellent accessibility via Radix
- Tailwind CSS integration
- No runtime dependencies
- Easy to customize

### Negative
- Manual component updates
- **Mitigation:** Track upstream changes, selective updates
- Initial setup time
- **Mitigation:** CLI tools, starter templates

### Risks
- Inconsistent customizations: Design system guidelines, code reviews
- Accessibility regressions: Testing, audit tools
- Component drift: Regular alignment with design system

---

## Implementation Notes

### Component Structure

```
packages/ui/
├── src/
│   ├── components/
│   │   ├── ui/
│   │   │   ├── button.tsx
│   │   │   ├── input.tsx
│   │   │   ├── select.tsx
│   │   │   ├── dialog.tsx
│   │   │   ├── dropdown-menu.tsx
│   │   │   ├── table.tsx
│   │   │   ├── card.tsx
│   │   │   ├── badge.tsx
│   │   │   ├── toast.tsx
│   │   │   └── ...
│   │   ├── forms/
│   │   │   ├── form-field.tsx
│   │   │   ├── form-select.tsx
│   │   │   └── form-textarea.tsx
│   │   └── composite/
│   │       ├── data-table.tsx
│   │       ├── combobox.tsx
│   │       └── command-palette.tsx
│   ├── hooks/
│   │   ├── use-toast.ts
│   │   └── use-media-query.ts
│   ├── lib/
│   │   └── utils.ts
│   └── index.ts
├── tailwind.config.ts
└── package.json
```

### Button Component

```tsx
// packages/ui/src/components/ui/button.tsx
import * as React from 'react';
import { Slot } from '@radix-ui/react-slot';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

const buttonVariants = cva(
  'inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50',
  {
    variants: {
      variant: {
        default: 'bg-primary text-primary-foreground hover:bg-primary/90',
        destructive: 'bg-destructive text-destructive-foreground hover:bg-destructive/90',
        outline: 'border border-input bg-background hover:bg-accent hover:text-accent-foreground',
        secondary: 'bg-secondary text-secondary-foreground hover:bg-secondary/80',
        ghost: 'hover:bg-accent hover:text-accent-foreground',
        link: 'text-primary underline-offset-4 hover:underline',
      },
      size: {
        default: 'h-10 px-4 py-2',
        sm: 'h-9 rounded-md px-3',
        lg: 'h-11 rounded-md px-8',
        icon: 'h-10 w-10',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
  loading?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, loading, children, disabled, ...props }, ref) => {
    const Comp = asChild ? Slot : 'button';
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        disabled={disabled || loading}
        {...props}
      >
        {loading ? (
          <>
            <svg
              className="mr-2 h-4 w-4 animate-spin"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
              />
            </svg>
            Loading...
          </>
        ) : (
          children
        )}
      </Comp>
    );
  }
);
Button.displayName = 'Button';

export { Button, buttonVariants };
```

### Form Components with React Hook Form

```tsx
// packages/ui/src/components/forms/form-field.tsx
import * as React from 'react';
import { useFormContext, Controller } from 'react-hook-form';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { cn } from '@/lib/utils';

interface FormFieldProps {
  name: string;
  label: string;
  type?: string;
  placeholder?: string;
  description?: string;
  required?: boolean;
  className?: string;
}

export function FormField({
  name,
  label,
  type = 'text',
  placeholder,
  description,
  required,
  className,
}: FormFieldProps) {
  const {
    control,
    formState: { errors },
  } = useFormContext();

  const error = errors[name];

  return (
    <div className={cn('space-y-2', className)}>
      <Label htmlFor={name}>
        {label}
        {required && <span className="text-destructive ml-1">*</span>}
      </Label>
      <Controller
        name={name}
        control={control}
        render={({ field }) => (
          <Input
            {...field}
            id={name}
            type={type}
            placeholder={placeholder}
            aria-invalid={!!error}
            aria-describedby={error ? `${name}-error` : description ? `${name}-description` : undefined}
          />
        )}
      />
      {description && !error && (
        <p id={`${name}-description`} className="text-sm text-muted-foreground">
          {description}
        </p>
      )}
      {error && (
        <p id={`${name}-error`} className="text-sm text-destructive">
          {error.message as string}
        </p>
      )}
    </div>
  );
}
```

### Data Table Component

```tsx
// packages/ui/src/components/composite/data-table.tsx
'use client';

import * as React from 'react';
import {
  ColumnDef,
  flexRender,
  getCoreRowModel,
  useReactTable,
  getSortedRowModel,
  SortingState,
  getFilteredRowModel,
  ColumnFiltersState,
} from '@tanstack/react-table';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../ui/table';
import { Input } from '../ui/input';

interface DataTableProps<TData, TValue> {
  columns: ColumnDef<TData, TValue>[];
  data: TData[];
  searchColumn?: string;
  searchPlaceholder?: string;
}

export function DataTable<TData, TValue>({
  columns,
  data,
  searchColumn,
  searchPlaceholder = 'Search...',
}: DataTableProps<TData, TValue>) {
  const [sorting, setSorting] = React.useState<SortingState>([]);
  const [columnFilters, setColumnFilters] = React.useState<ColumnFiltersState>([]);

  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
    onSortingChange: setSorting,
    getSortedRowModel: getSortedRowModel(),
    onColumnFiltersChange: setColumnFilters,
    getFilteredRowModel: getFilteredRowModel(),
    state: {
      sorting,
      columnFilters,
    },
  });

  return (
    <div className="space-y-4">
      {searchColumn && (
        <Input
          placeholder={searchPlaceholder}
          value={(table.getColumn(searchColumn)?.getFilterValue() as string) ?? ''}
          onChange={(event) =>
            table.getColumn(searchColumn)?.setFilterValue(event.target.value)
          }
          className="max-w-sm"
        />
      )}
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <TableHead key={header.id}>
                    {header.isPlaceholder
                      ? null
                      : flexRender(
                          header.column.columnDef.header,
                          header.getContext()
                        )}
                  </TableHead>
                ))}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {table.getRowModel().rows?.length ? (
              table.getRowModel().rows.map((row) => (
                <TableRow
                  key={row.id}
                  data-state={row.getIsSelected() && 'selected'}
                >
                  {row.getVisibleCells().map((cell) => (
                    <TableCell key={cell.id}>
                      {flexRender(
                        cell.column.columnDef.cell,
                        cell.getContext()
                      )}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell
                  colSpan={columns.length}
                  className="h-24 text-center"
                >
                  No results.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
```

### Combobox with Search

```tsx
// packages/ui/src/components/composite/combobox.tsx
'use client';

import * as React from 'react';
import { Check, ChevronsUpDown } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '../ui/button';
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
} from '../ui/command';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '../ui/popover';

interface ComboboxProps {
  options: { value: string; label: string }[];
  value?: string;
  onValueChange: (value: string) => void;
  placeholder?: string;
  searchPlaceholder?: string;
  emptyMessage?: string;
  className?: string;
}

export function Combobox({
  options,
  value,
  onValueChange,
  placeholder = 'Select...',
  searchPlaceholder = 'Search...',
  emptyMessage = 'No results found.',
  className,
}: ComboboxProps) {
  const [open, setOpen] = React.useState(false);

  const selectedOption = options.find((option) => option.value === value);

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          role="combobox"
          aria-expanded={open}
          className={cn('w-full justify-between', className)}
        >
          {selectedOption?.label ?? placeholder}
          <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-full p-0">
        <Command>
          <CommandInput placeholder={searchPlaceholder} />
          <CommandEmpty>{emptyMessage}</CommandEmpty>
          <CommandGroup>
            {options.map((option) => (
              <CommandItem
                key={option.value}
                value={option.value}
                onSelect={() => {
                  onValueChange(option.value);
                  setOpen(false);
                }}
              >
                <Check
                  className={cn(
                    'mr-2 h-4 w-4',
                    value === option.value ? 'opacity-100' : 'opacity-0'
                  )}
                />
                {option.label}
              </CommandItem>
            ))}
          </CommandGroup>
        </Command>
      </PopoverContent>
    </Popover>
  );
}
```

### Tailwind CSS Configuration

```ts
// packages/ui/tailwind.config.ts
import type { Config } from 'tailwindcss';

const config: Config = {
  darkMode: ['class'],
  content: [
    './src/**/*.{ts,tsx}',
  ],
  theme: {
    container: {
      center: true,
      padding: '2rem',
      screens: {
        '2xl': '1400px',
      },
    },
    extend: {
      colors: {
        border: 'hsl(var(--border))',
        input: 'hsl(var(--input))',
        ring: 'hsl(var(--ring))',
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        primary: {
          DEFAULT: 'hsl(var(--primary))',
          foreground: 'hsl(var(--primary-foreground))',
        },
        secondary: {
          DEFAULT: 'hsl(var(--secondary))',
          foreground: 'hsl(var(--secondary-foreground))',
        },
        destructive: {
          DEFAULT: 'hsl(var(--destructive))',
          foreground: 'hsl(var(--destructive-foreground))',
        },
        muted: {
          DEFAULT: 'hsl(var(--muted))',
          foreground: 'hsl(var(--muted-foreground))',
        },
        accent: {
          DEFAULT: 'hsl(var(--accent))',
          foreground: 'hsl(var(--accent-foreground))',
        },
        popover: {
          DEFAULT: 'hsl(var(--popover))',
          foreground: 'hsl(var(--popover-foreground))',
        },
        card: {
          DEFAULT: 'hsl(var(--card))',
          foreground: 'hsl(var(--card-foreground))',
        },
        // Maritime theme colors
        maritime: {
          50: '#f0f9ff',
          100: '#e0f2fe',
          500: '#0ea5e9',
          600: '#0284c7',
          700: '#0369a1',
          800: '#075985',
          900: '#0c4a6e',
        },
      },
      borderRadius: {
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 2px)',
        sm: 'calc(var(--radius) - 4px)',
      },
      keyframes: {
        'accordion-down': {
          from: { height: '0' },
          to: { height: 'var(--radix-accordion-content-height)' },
        },
        'accordion-up': {
          from: { height: 'var(--radix-accordion-content-height)' },
          to: { height: '0' },
        },
      },
      animation: {
        'accordion-down': 'accordion-down 0.2s ease-out',
        'accordion-up': 'accordion-up 0.2s ease-out',
      },
    },
  },
  plugins: [require('tailwindcss-animate')],
};

export default config;
```

### Dependencies
- ADR-UI-001: Next.js 14+ App Router
- ADR-UI-009: Design System & Theming

### Migration Strategy
1. Install shadcn/ui CLI
2. Initialize component library package
3. Add core components (Button, Input, etc.)
4. Add composite components
5. Create form integration components
6. Document component usage
7. Set up Storybook for documentation

---

## Operational Considerations

### Customization & Theming Approach

#### Theme Architecture

```typescript
// CSS custom properties for theming (globals.css)
:root {
  // Maritime brand colors
  --primary: 199 89% 48%;        // Ocean blue #0ea5e9
  --primary-foreground: 0 0% 100%;
  --secondary: 24 95% 53%;       // Warm orange #f97316
  --secondary-foreground: 0 0% 100%;

  // Semantic colors
  --success: 142 71% 45%;
  --warning: 38 92% 50%;
  --error: 0 84% 60%;
  --info: 217 91% 60%;

  // Surface colors
  --background: 210 40% 98%;
  --foreground: 222 47% 11%;
  --card: 0 0% 100%;
  --muted: 210 40% 96%;

  // Component-specific
  --radius: 0.5rem;
  --ring: 199 89% 48%;
}

.dark {
  --primary: 199 89% 65%;
  --background: 222 47% 11%;
  --foreground: 210 40% 98%;
  // ... dark mode overrides
}
```

#### Component Variant Ownership

| Variant Category | Owner | Governance |
|-----------------|-------|------------|
| Base variants (`default`, `outline`, `ghost`) | Design System Team | Requires design review |
| Size variants (`sm`, `md`, `lg`, `icon`) | Design System Team | Must follow 8px grid |
| State variants (`loading`, `disabled`, `error`) | Design System Team | Accessibility reviewed |
| Domain variants (`maritime`, `urgent`, `success`) | Product Team | Extends base variants |
| App-specific variants | Feature Teams | Local to app, documented |

#### Component Extension Pattern

```typescript
// Extending Button with domain-specific variants
// packages/ui/src/components/ui/button.tsx

const buttonVariants = cva(
  'inline-flex items-center justify-center...',
  {
    variants: {
      variant: {
        // Base variants (owned by Design System)
        default: 'bg-primary text-primary-foreground hover:bg-primary/90',
        destructive: 'bg-destructive text-destructive-foreground...',
        outline: 'border border-input bg-background...',
        secondary: 'bg-secondary text-secondary-foreground...',
        ghost: 'hover:bg-accent hover:text-accent-foreground',
        link: 'text-primary underline-offset-4 hover:underline',

        // Domain variants (owned by Product Team)
        urgent: 'bg-warning text-warning-foreground animate-pulse',
        maritime: 'bg-maritime-600 text-white hover:bg-maritime-700',
        'bid-accept': 'bg-success text-success-foreground',
        'bid-reject': 'bg-destructive text-destructive-foreground',
      },
      size: {
        default: 'h-10 px-4 py-2',
        sm: 'h-9 rounded-md px-3',
        lg: 'h-11 rounded-md px-8',
        icon: 'h-10 w-10',
        'touch': 'h-12 px-6 py-3', // Mobile-optimized
      },
    },
    compoundVariants: [
      {
        variant: 'urgent',
        size: 'lg',
        class: 'text-lg font-bold',
      },
    ],
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  }
);
```

### Accessibility Requirements

#### Built-in Accessibility Checklist

| Requirement | Implementation | Testing |
|------------|----------------|---------|
| Keyboard navigation | Radix UI primitives | jest-axe + manual |
| Focus management | `focus-visible` ring styles | Playwright |
| ARIA attributes | Auto-managed by Radix | axe-core audit |
| Color contrast | 4.5:1 minimum (AA) | Contrast checker CI |
| Screen reader support | Semantic HTML + ARIA | NVDA/VoiceOver testing |
| Reduced motion | `prefers-reduced-motion` | Manual verification |

#### Accessibility Patterns in Components

```typescript
// Form field with full accessibility
export function FormField({ label, error, description, required, ...props }) {
  const id = useId();
  const descriptionId = `${id}-description`;
  const errorId = `${id}-error`;

  return (
    <div className="space-y-2">
      <Label htmlFor={id}>
        {label}
        {required && (
          <>
            <span className="text-destructive ml-1" aria-hidden="true">*</span>
            <span className="sr-only">(required)</span>
          </>
        )}
      </Label>

      {description && (
        <p id={descriptionId} className="text-sm text-muted-foreground">
          {description}
        </p>
      )}

      <Input
        id={id}
        aria-describedby={[
          description && descriptionId,
          error && errorId,
        ].filter(Boolean).join(' ') || undefined}
        aria-invalid={!!error}
        aria-required={required}
        {...props}
      />

      {error && (
        <p id={errorId} className="text-sm text-destructive" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
```

#### Component Accessibility Audit Schedule

| Component Category | Audit Frequency | Auditor |
|-------------------|-----------------|---------|
| Form components | Every PR | Automated (jest-axe) |
| Navigation | Monthly | Design System Team |
| Data display | Quarterly | External audit |
| Interactive widgets | Every PR | Automated + manual |

### Upstream Update Process

#### Update Evaluation Workflow

```
1. Monitor shadcn/ui releases (GitHub notifications)
           │
           ▼
2. Review changelog for breaking changes
           │
           ▼
3. Create feature branch: `chore/shadcn-update-{date}`
           │
           ▼
4. Run diff tool: `npx shadcn-ui diff`
           │
           ▼
5. Apply updates selectively per component
           │
           ▼
6. Run test suite:
   - Unit tests (jest)
   - Visual regression (Chromatic)
   - Accessibility audit (axe-core)
   - Integration tests (Playwright)
           │
           ▼
7. Design review for visual changes
           │
           ▼
8. Merge to main via PR with changelog
```

#### Update Decision Matrix

| Change Type | Action | Timeline |
|------------|--------|----------|
| Security fix | Immediate merge | Same day |
| Bug fix | Evaluate + merge | Within sprint |
| New feature | Evaluate need | Backlog |
| Breaking change | Full regression test | Next major release |
| Style change | Design review required | Backlog |

#### Version Tracking

```json
// packages/ui/component-versions.json
{
  "lastUpdated": "2025-01-20",
  "shadcnVersion": "0.8.0",
  "components": {
    "button": { "version": "0.8.0", "customized": true },
    "input": { "version": "0.8.0", "customized": false },
    "dialog": { "version": "0.7.0", "customized": true, "note": "Custom close animation" },
    "data-table": { "version": "0.8.0", "customized": true, "note": "Added export feature" }
  }
}
```

### Open Questions - Resolved

- **Q:** How will upstream updates be evaluated and merged to avoid regressions?
  - **A:** We implement a structured update process:
    1. **Monitoring**: Subscribe to shadcn/ui releases via GitHub watch
    2. **Diff analysis**: Use `npx shadcn-ui diff` to identify changes per component
    3. **Selective updates**: Apply updates component-by-component, not bulk
    4. **Testing gates**: All updates must pass:
       - Unit tests with jest-axe accessibility checks
       - Visual regression tests via Chromatic
       - Integration tests via Playwright
    5. **Design review**: Any visual changes require design team approval
    6. **Version tracking**: Maintain `component-versions.json` documenting customizations
    7. **Rollback plan**: Keep previous component versions in git history for easy revert

---

## References
- [shadcn/ui Documentation](https://ui.shadcn.com/)
- [Radix UI Primitives](https://www.radix-ui.com/)
- [Tailwind CSS](https://tailwindcss.com/)
- [Class Variance Authority](https://cva.style/docs)
