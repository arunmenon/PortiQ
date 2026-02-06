# ADR-UI-009: Design System & Theming

**Status:** Accepted
**Date:** 2025-01-20
**Technical Area:** Frontend

---

## Context

The platform requires a consistent design system that works across web and mobile applications with maritime-themed branding.

### Business Context
Design requirements:
- Professional B2B appearance
- Maritime industry branding
- Consistency across platforms
- Accessibility compliance
- Dark mode support
- White-label potential for enterprise

### Technical Context
- Next.js web application (ADR-UI-001)
- React Native mobile app (ADR-UI-006)
- shadcn/ui components (ADR-UI-002)
- Tailwind CSS for web
- Need shared design tokens

### Assumptions
- CSS custom properties for theming
- Tailwind config shared across web
- React Native uses similar tokens
- Design tokens in single source of truth

---

## Decision Drivers

- Cross-platform consistency
- Maintainability
- Customization flexibility
- Developer experience
- Performance

---

## Decision

We will create a shared design system with design tokens defined in a central package, with platform-specific implementations for web (Tailwind/CSS) and mobile (React Native StyleSheet).

---

## Implementation Notes

### Design System Architecture

```
packages/design-system/
├── tokens/
│   ├── colors.ts
│   ├── typography.ts
│   ├── spacing.ts
│   ├── shadows.ts
│   └── index.ts
├── themes/
│   ├── light.ts
│   ├── dark.ts
│   └── index.ts
├── web/
│   ├── tailwind-preset.ts
│   └── css-variables.ts
├── mobile/
│   ├── styles.ts
│   └── theme-provider.tsx
└── index.ts
```

### Design Tokens

```tsx
// packages/design-system/tokens/colors.ts
export const colors = {
  // Brand colors - Maritime theme
  primary: {
    50: '#f0f9ff',
    100: '#e0f2fe',
    200: '#bae6fd',
    300: '#7dd3fc',
    400: '#38bdf8',
    500: '#0ea5e9',  // Primary
    600: '#0284c7',
    700: '#0369a1',
    800: '#075985',
    900: '#0c4a6e',
    950: '#082f49',
  },

  // Secondary - Warm accent
  secondary: {
    50: '#fff7ed',
    100: '#ffedd5',
    200: '#fed7aa',
    300: '#fdba74',
    400: '#fb923c',
    500: '#f97316',  // Secondary
    600: '#ea580c',
    700: '#c2410c',
    800: '#9a3412',
    900: '#7c2d12',
  },

  // Neutrals
  gray: {
    50: '#f9fafb',
    100: '#f3f4f6',
    200: '#e5e7eb',
    300: '#d1d5db',
    400: '#9ca3af',
    500: '#6b7280',
    600: '#4b5563',
    700: '#374151',
    800: '#1f2937',
    900: '#111827',
    950: '#030712',
  },

  // Semantic colors
  success: {
    light: '#dcfce7',
    DEFAULT: '#22c55e',
    dark: '#15803d',
  },
  warning: {
    light: '#fef3c7',
    DEFAULT: '#f59e0b',
    dark: '#b45309',
  },
  error: {
    light: '#fee2e2',
    DEFAULT: '#ef4444',
    dark: '#b91c1c',
  },
  info: {
    light: '#dbeafe',
    DEFAULT: '#3b82f6',
    dark: '#1d4ed8',
  },
};

// packages/design-system/tokens/typography.ts
export const typography = {
  fontFamily: {
    sans: ['Inter', 'system-ui', 'sans-serif'],
    mono: ['JetBrains Mono', 'monospace'],
  },

  fontSize: {
    xs: ['0.75rem', { lineHeight: '1rem' }],
    sm: ['0.875rem', { lineHeight: '1.25rem' }],
    base: ['1rem', { lineHeight: '1.5rem' }],
    lg: ['1.125rem', { lineHeight: '1.75rem' }],
    xl: ['1.25rem', { lineHeight: '1.75rem' }],
    '2xl': ['1.5rem', { lineHeight: '2rem' }],
    '3xl': ['1.875rem', { lineHeight: '2.25rem' }],
    '4xl': ['2.25rem', { lineHeight: '2.5rem' }],
  },

  fontWeight: {
    normal: '400',
    medium: '500',
    semibold: '600',
    bold: '700',
  },
};

// packages/design-system/tokens/spacing.ts
export const spacing = {
  0: '0',
  1: '0.25rem',
  2: '0.5rem',
  3: '0.75rem',
  4: '1rem',
  5: '1.25rem',
  6: '1.5rem',
  8: '2rem',
  10: '2.5rem',
  12: '3rem',
  16: '4rem',
  20: '5rem',
  24: '6rem',
};

// packages/design-system/tokens/shadows.ts
export const shadows = {
  sm: '0 1px 2px 0 rgb(0 0 0 / 0.05)',
  DEFAULT: '0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)',
  md: '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)',
  lg: '0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)',
  xl: '0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1)',
};
```

### Theme Definitions

```tsx
// packages/design-system/themes/light.ts
import { colors } from '../tokens/colors';

export const lightTheme = {
  name: 'light',

  colors: {
    // Background
    background: colors.gray[50],
    backgroundSecondary: '#ffffff',
    backgroundTertiary: colors.gray[100],

    // Foreground
    foreground: colors.gray[900],
    foregroundSecondary: colors.gray[600],
    foregroundMuted: colors.gray[400],

    // Primary
    primary: colors.primary[500],
    primaryForeground: '#ffffff',
    primaryHover: colors.primary[600],

    // Secondary
    secondary: colors.gray[100],
    secondaryForeground: colors.gray[900],
    secondaryHover: colors.gray[200],

    // Accent
    accent: colors.secondary[500],
    accentForeground: '#ffffff',

    // Borders
    border: colors.gray[200],
    borderHover: colors.gray[300],

    // Input
    input: colors.gray[200],
    inputFocus: colors.primary[500],

    // Cards
    card: '#ffffff',
    cardForeground: colors.gray[900],

    // Status
    success: colors.success.DEFAULT,
    successBackground: colors.success.light,
    warning: colors.warning.DEFAULT,
    warningBackground: colors.warning.light,
    error: colors.error.DEFAULT,
    errorBackground: colors.error.light,
    info: colors.info.DEFAULT,
    infoBackground: colors.info.light,
  },

  radius: {
    sm: '0.25rem',
    md: '0.375rem',
    lg: '0.5rem',
    xl: '0.75rem',
    full: '9999px',
  },
};

// packages/design-system/themes/dark.ts
import { colors } from '../tokens/colors';

export const darkTheme = {
  name: 'dark',

  colors: {
    background: colors.gray[950],
    backgroundSecondary: colors.gray[900],
    backgroundTertiary: colors.gray[800],

    foreground: colors.gray[50],
    foregroundSecondary: colors.gray[300],
    foregroundMuted: colors.gray[500],

    primary: colors.primary[400],
    primaryForeground: colors.gray[900],
    primaryHover: colors.primary[300],

    secondary: colors.gray[800],
    secondaryForeground: colors.gray[100],
    secondaryHover: colors.gray[700],

    accent: colors.secondary[400],
    accentForeground: colors.gray[900],

    border: colors.gray[800],
    borderHover: colors.gray[700],

    input: colors.gray[800],
    inputFocus: colors.primary[400],

    card: colors.gray[900],
    cardForeground: colors.gray[50],

    success: colors.success.DEFAULT,
    successBackground: 'rgba(34, 197, 94, 0.1)',
    warning: colors.warning.DEFAULT,
    warningBackground: 'rgba(245, 158, 11, 0.1)',
    error: colors.error.DEFAULT,
    errorBackground: 'rgba(239, 68, 68, 0.1)',
    info: colors.info.DEFAULT,
    infoBackground: 'rgba(59, 130, 246, 0.1)',
  },

  radius: {
    sm: '0.25rem',
    md: '0.375rem',
    lg: '0.5rem',
    xl: '0.75rem',
    full: '9999px',
  },
};
```

### Tailwind Preset for Web

```tsx
// packages/design-system/web/tailwind-preset.ts
import { colors, typography, spacing, shadows } from '../tokens';

export const tailwindPreset = {
  theme: {
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
          ...colors.primary,
        },
        secondary: {
          DEFAULT: 'hsl(var(--secondary))',
          foreground: 'hsl(var(--secondary-foreground))',
          ...colors.secondary,
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
        card: {
          DEFAULT: 'hsl(var(--card))',
          foreground: 'hsl(var(--card-foreground))',
        },
        success: colors.success,
        warning: colors.warning,
        error: colors.error,
        info: colors.info,
        gray: colors.gray,
      },
      fontFamily: typography.fontFamily,
      fontSize: typography.fontSize,
      fontWeight: typography.fontWeight,
      spacing,
      boxShadow: shadows,
      borderRadius: {
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 2px)',
        sm: 'calc(var(--radius) - 4px)',
      },
    },
  },
};
```

### CSS Variables for Web

```tsx
// packages/design-system/web/css-variables.ts
import { lightTheme, darkTheme } from '../themes';

function colorToHsl(hex: string): string {
  // Convert hex to HSL string for CSS
  // Implementation omitted for brevity
  return hex;
}

export function generateCssVariables(theme: typeof lightTheme): string {
  return `
    --background: ${colorToHsl(theme.colors.background)};
    --foreground: ${colorToHsl(theme.colors.foreground)};
    --card: ${colorToHsl(theme.colors.card)};
    --card-foreground: ${colorToHsl(theme.colors.cardForeground)};
    --primary: ${colorToHsl(theme.colors.primary)};
    --primary-foreground: ${colorToHsl(theme.colors.primaryForeground)};
    --secondary: ${colorToHsl(theme.colors.secondary)};
    --secondary-foreground: ${colorToHsl(theme.colors.secondaryForeground)};
    --muted: ${colorToHsl(theme.colors.foregroundMuted)};
    --muted-foreground: ${colorToHsl(theme.colors.foregroundSecondary)};
    --accent: ${colorToHsl(theme.colors.accent)};
    --accent-foreground: ${colorToHsl(theme.colors.accentForeground)};
    --destructive: ${colorToHsl(theme.colors.error)};
    --destructive-foreground: #ffffff;
    --border: ${colorToHsl(theme.colors.border)};
    --input: ${colorToHsl(theme.colors.input)};
    --ring: ${colorToHsl(theme.colors.primary)};
    --radius: ${theme.radius.lg};
  `;
}

// globals.css
export const globalStyles = `
  :root {
    ${generateCssVariables(lightTheme)}
  }

  .dark {
    ${generateCssVariables(darkTheme)}
  }
`;
```

### Mobile Theme Provider

```tsx
// packages/design-system/mobile/theme-provider.tsx
import React, { createContext, useContext, useState, useEffect } from 'react';
import { useColorScheme } from 'react-native';
import { lightTheme, darkTheme } from '../themes';

type Theme = typeof lightTheme;

interface ThemeContextValue {
  theme: Theme;
  isDark: boolean;
  toggleTheme: () => void;
  setTheme: (mode: 'light' | 'dark' | 'system') => void;
}

const ThemeContext = createContext<ThemeContextValue | null>(null);

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const systemColorScheme = useColorScheme();
  const [mode, setMode] = useState<'light' | 'dark' | 'system'>('system');

  const isDark = mode === 'system'
    ? systemColorScheme === 'dark'
    : mode === 'dark';

  const theme = isDark ? darkTheme : lightTheme;

  const toggleTheme = () => {
    setMode((prev) => (prev === 'light' ? 'dark' : 'light'));
  };

  return (
    <ThemeContext.Provider value={{ theme, isDark, toggleTheme, setTheme: setMode }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within ThemeProvider');
  }
  return context;
}
```

### Mobile Styles

```tsx
// packages/design-system/mobile/styles.ts
import { StyleSheet } from 'react-native';
import { spacing, typography } from '../tokens';

export function createStyles<T extends StyleSheet.NamedStyles<T>>(
  stylesFn: (theme: Theme) => T
) {
  return (theme: Theme) => StyleSheet.create(stylesFn(theme));
}

// Common styles
export const commonStyles = createStyles((theme) => ({
  container: {
    flex: 1,
    backgroundColor: theme.colors.background,
  },
  card: {
    backgroundColor: theme.colors.card,
    borderRadius: parseFloat(theme.radius.lg) * 16,
    padding: parseFloat(spacing[4]) * 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 2,
    elevation: 2,
  },
  title: {
    fontSize: parseFloat(typography.fontSize['2xl'][0]) * 16,
    fontWeight: typography.fontWeight.bold,
    color: theme.colors.foreground,
  },
  subtitle: {
    fontSize: parseFloat(typography.fontSize.lg[0]) * 16,
    fontWeight: typography.fontWeight.semibold,
    color: theme.colors.foreground,
  },
  body: {
    fontSize: parseFloat(typography.fontSize.base[0]) * 16,
    color: theme.colors.foregroundSecondary,
  },
  caption: {
    fontSize: parseFloat(typography.fontSize.sm[0]) * 16,
    color: theme.colors.foregroundMuted,
  },
}));

// Usage example
export function useStyles<T extends StyleSheet.NamedStyles<T>>(
  stylesFn: (theme: Theme) => T
): T {
  const { theme } = useTheme();
  return React.useMemo(() => StyleSheet.create(stylesFn(theme)), [theme]);
}
```

### Using the Design System

```tsx
// Web component example
// components/ui/button.tsx
import { cn } from '@/lib/utils';

export function Button({ variant = 'default', ...props }) {
  return (
    <button
      className={cn(
        'inline-flex items-center justify-center rounded-md text-sm font-medium',
        'ring-offset-background transition-colors',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
        variant === 'default' && 'bg-primary text-primary-foreground hover:bg-primary/90',
        variant === 'secondary' && 'bg-secondary text-secondary-foreground hover:bg-secondary/80',
      )}
      {...props}
    />
  );
}

// Mobile component example
// components/ui/Button.tsx
import { Pressable, Text } from 'react-native';
import { useStyles, useTheme } from '@ship-chandlery/design-system/mobile';

export function Button({ variant = 'default', children, ...props }) {
  const { theme } = useTheme();
  const styles = useStyles((t) => ({
    button: {
      paddingVertical: 12,
      paddingHorizontal: 16,
      borderRadius: parseFloat(t.radius.md) * 16,
      alignItems: 'center',
      justifyContent: 'center',
    },
    default: {
      backgroundColor: t.colors.primary,
    },
    secondary: {
      backgroundColor: t.colors.secondary,
    },
    text: {
      fontSize: 14,
      fontWeight: '500',
    },
    defaultText: {
      color: t.colors.primaryForeground,
    },
    secondaryText: {
      color: t.colors.secondaryForeground,
    },
  }));

  return (
    <Pressable
      style={[styles.button, styles[variant]]}
      {...props}
    >
      <Text style={[styles.text, styles[`${variant}Text`]]}>
        {children}
      </Text>
    </Pressable>
  );
}
```

### Dependencies
- ADR-UI-001: Next.js 14+ App Router
- ADR-UI-002: Component Library (shadcn/ui)
- ADR-UI-006: React Native with Expo

### Migration Strategy
1. Create design-system package
2. Define design tokens
3. Create theme definitions
4. Generate Tailwind preset
5. Set up CSS variables
6. Create mobile theme provider
7. Update existing components
8. Document usage guidelines

---

## Operational Considerations

### Token Taxonomy

#### Token Hierarchy

```
┌─────────────────────────────────────────────────────────────────┐
│                       Token Architecture                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Level 1: Primitive Tokens (Raw Values)                         │
│  ├── colors.blue.500 = "#0ea5e9"                                │
│  ├── spacing.4 = "1rem"                                         │
│  └── fontSize.base = "1rem"                                     │
│                                                                  │
│  Level 2: Semantic Tokens (Purpose)                             │
│  ├── color.primary = colors.blue.500                            │
│  ├── color.background = colors.gray.50                          │
│  └── spacing.component.padding = spacing.4                      │
│                                                                  │
│  Level 3: Component Tokens (Scoped)                             │
│  ├── button.background = color.primary                          │
│  ├── button.padding = spacing.component.padding                 │
│  └── card.radius = radius.lg                                    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

#### Token Naming Convention

| Category | Pattern | Example |
|----------|---------|---------|
| Colors | `color.{semantic}.{variant?}` | `color.primary`, `color.primary.hover` |
| Spacing | `spacing.{context}.{size}` | `spacing.layout.page`, `spacing.component.sm` |
| Typography | `font.{property}.{variant}` | `font.size.lg`, `font.weight.bold` |
| Borders | `border.{property}.{variant}` | `border.radius.md`, `border.width.thin` |
| Shadows | `shadow.{size}` | `shadow.sm`, `shadow.lg` |
| Z-index | `z.{context}` | `z.modal`, `z.tooltip` |

#### Token Categories

```typescript
// packages/design-system/tokens/index.ts
export const tokens = {
  // Primitive tokens - never use directly in components
  primitives: {
    colors: {
      blue: { 50: '#f0f9ff', 100: '#e0f2fe', /* ... */ 900: '#0c4a6e' },
      orange: { 50: '#fff7ed', /* ... */ },
      gray: { 50: '#f9fafb', /* ... */ 950: '#030712' },
    },
    spacing: {
      0: '0', 1: '0.25rem', 2: '0.5rem', 4: '1rem', 8: '2rem', /* ... */
    },
    fontSize: {
      xs: '0.75rem', sm: '0.875rem', base: '1rem', lg: '1.125rem', /* ... */
    },
  },

  // Semantic tokens - use in component definitions
  semantic: {
    color: {
      primary: { value: '{primitives.colors.blue.500}', description: 'Primary brand color' },
      secondary: { value: '{primitives.colors.orange.500}', description: 'Secondary accent' },
      background: { value: '{primitives.colors.gray.50}', description: 'Page background' },
      foreground: { value: '{primitives.colors.gray.900}', description: 'Primary text' },
      muted: { value: '{primitives.colors.gray.500}', description: 'Secondary text' },
      border: { value: '{primitives.colors.gray.200}', description: 'Default border' },
      error: { value: '#ef4444', description: 'Error states' },
      success: { value: '#22c55e', description: 'Success states' },
      warning: { value: '#f59e0b', description: 'Warning states' },
    },
    spacing: {
      page: { value: '{primitives.spacing.8}', description: 'Page padding' },
      section: { value: '{primitives.spacing.6}', description: 'Section spacing' },
      component: { value: '{primitives.spacing.4}', description: 'Component padding' },
      element: { value: '{primitives.spacing.2}', description: 'Element spacing' },
    },
  },

  // Component tokens - scoped to specific components
  component: {
    button: {
      paddingX: '{semantic.spacing.component}',
      paddingY: '{primitives.spacing.2}',
      radius: '{primitives.radius.md}',
      fontSize: '{primitives.fontSize.sm}',
    },
    card: {
      padding: '{semantic.spacing.component}',
      radius: '{primitives.radius.lg}',
      shadow: '{primitives.shadow.sm}',
    },
    input: {
      height: '2.5rem',
      paddingX: '{primitives.spacing.3}',
      radius: '{primitives.radius.md}',
      borderWidth: '1px',
    },
  },
};
```

### Theme Change Governance

#### Change Request Process

```
1. Design Request
   └── Designer creates RFC in design-system repo
       ├── Token(s) to change
       ├── Before/after visual comparison
       ├── Affected components list
       └── Accessibility impact assessment

2. Review
   └── Design System Team reviews (48h SLA)
       ├── Visual consistency check
       ├── Cross-platform verification (web + mobile)
       └── Accessibility verification (contrast ratios)

3. Implementation
   └── Developer creates PR
       ├── Token value changes
       ├── Component updates (if needed)
       ├── Storybook screenshots
       └── Visual regression tests

4. Release
   └── Follows semantic versioning
       ├── Patch: Bug fixes, minor adjustments
       ├── Minor: New tokens, non-breaking changes
       └── Major: Breaking changes, deprecations
```

#### Approval Matrix

| Change Type | Approvers | Timeline |
|------------|-----------|----------|
| New primitive token | Design Lead | 1 week |
| New semantic token | Design Lead + Dev Lead | 1 week |
| Modify existing token | Design Lead + affected team leads | 2 weeks |
| Deprecate token | Design System Team + all stakeholders | 1 month notice |
| Theme-wide change | CPO + Design Lead + Engineering Lead | 1 quarter |

### Documentation Requirements

#### Token Documentation Format

```typescript
// Each token must include:
interface TokenDocumentation {
  name: string;              // Token name
  value: string;             // Current value
  description: string;       // What it's used for
  usage: string[];           // Example use cases
  doNot: string[];           // Anti-patterns
  relatedTokens: string[];   // Related tokens
  changelog: {
    version: string;
    change: string;
    date: string;
  }[];
}

// Example
const primaryColorDoc: TokenDocumentation = {
  name: 'color.primary',
  value: '#0ea5e9',
  description: 'Primary brand color used for main interactive elements',
  usage: [
    'Primary buttons',
    'Active navigation items',
    'Links',
    'Focus rings',
  ],
  doNot: [
    'Do not use for body text',
    'Do not use as background for large areas',
    'Do not combine with color.secondary in same component',
  ],
  relatedTokens: ['color.primary.hover', 'color.primary.foreground'],
  changelog: [
    { version: '1.2.0', change: 'Adjusted for WCAG AA contrast', date: '2025-01-15' },
  ],
};
```

#### Storybook Documentation

```typescript
// stories/tokens/colors.stories.tsx
export default {
  title: 'Design System/Tokens/Colors',
};

export const ColorPalette = () => (
  <div className="grid gap-8">
    {Object.entries(tokens.semantic.color).map(([name, token]) => (
      <div key={name} className="flex items-center gap-4">
        <div
          className="w-16 h-16 rounded-lg"
          style={{ backgroundColor: resolveToken(token.value) }}
        />
        <div>
          <code className="text-sm font-mono">color.{name}</code>
          <p className="text-sm text-muted-foreground">{token.description}</p>
        </div>
      </div>
    ))}
  </div>
);
```

### Linting & Enforcement

#### ESLint Rules

```javascript
// .eslintrc.js
module.exports = {
  plugins: ['design-tokens'],
  rules: {
    // Prevent hardcoded colors
    'design-tokens/no-hardcoded-colors': 'error',

    // Prevent hardcoded spacing
    'design-tokens/no-hardcoded-spacing': 'error',

    // Enforce semantic token usage over primitives
    'design-tokens/prefer-semantic-tokens': 'warn',

    // Prevent deprecated tokens
    'design-tokens/no-deprecated-tokens': 'error',
  },
};

// Custom rule implementation
// eslint-plugin-design-tokens/rules/no-hardcoded-colors.js
module.exports = {
  meta: {
    type: 'problem',
    docs: { description: 'Disallow hardcoded color values' },
    fixable: 'code',
  },
  create(context) {
    const colorPattern = /#[0-9a-fA-F]{3,8}|rgb\(|hsl\(/;

    return {
      Literal(node) {
        if (typeof node.value === 'string' && colorPattern.test(node.value)) {
          context.report({
            node,
            message: 'Use design tokens instead of hardcoded colors',
          });
        }
      },
    };
  },
};
```

#### Stylelint Rules

```javascript
// stylelint.config.js
module.exports = {
  plugins: ['stylelint-design-tokens'],
  rules: {
    'design-tokens/no-undeclared-tokens': true,
    'design-tokens/prefer-css-variables': true,
    'color-no-hex': true, // Force CSS variable usage
    'declaration-property-value-disallowed-list': {
      'color': ['/^#/', '/^rgb/'],
      'background-color': ['/^#/', '/^rgb/'],
    },
  },
};
```

#### CI/CD Quality Gates

```yaml
# .github/workflows/design-system-check.yml
name: Design System Quality

on: [pull_request]

jobs:
  lint-tokens:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install dependencies
        run: npm ci

      - name: Lint for token violations
        run: npm run lint:tokens

      - name: Check token documentation
        run: npm run check:token-docs

      - name: Visual regression tests
        run: npm run test:visual

      - name: Accessibility contrast check
        run: npm run check:contrast
```

### Theme Release Ownership & Cadence

#### Ownership

| Role | Responsibility |
|------|---------------|
| **Design System Lead** | Token strategy, major decisions, release approval |
| **Design System Team** | Day-to-day maintenance, PR reviews, documentation |
| **Platform Design Lead** | Web-specific token implementation |
| **Mobile Design Lead** | Mobile-specific token implementation |
| **Product Teams** | Request new tokens, report issues |

#### Release Cadence

| Release Type | Frequency | Content |
|--------------|-----------|---------|
| **Patch** (1.2.x) | As needed | Bug fixes, typo corrections |
| **Minor** (1.x.0) | Monthly | New tokens, non-breaking additions |
| **Major** (x.0.0) | Quarterly | Breaking changes, deprecations |
| **Emergency** | As needed | Critical bug fixes, security |

### Open Questions - Resolved

- **Q:** Who owns theme releases and the update cadence?
  - **A:** Theme releases are governed as follows:
    1. **Primary Owner**: Design System Lead (reports to CPO)
    2. **Day-to-day**: Design System Team (2-3 engineers + 1 designer)
    3. **Release cadence**:
       - Patches: As needed (same-day for critical fixes)
       - Minor releases: Monthly on first Monday
       - Major releases: Quarterly aligned with product releases
    4. **Approval requirements**:
       - Patches: Design System Team member
       - Minor: Design System Lead
       - Major: Design System Lead + Engineering Lead + CPO
    5. **Communication**: Release notes published to #design-system Slack channel and internal documentation site

---

## PortiQ AI Component Library

The PortiQ AI-native UX introduces specialized components for conversation-first interactions. These components extend the design system with AI-specific patterns, states, and animations.

### Component Architecture

```
packages/design-system/components/ai/
├── CommandBar/
│   ├── CommandBar.tsx
│   ├── CommandBarInput.tsx
│   ├── CommandBarSuggestions.tsx
│   └── VoiceWaveform.tsx
├── Conversation/
│   ├── ConversationBubble.tsx
│   ├── AIMessage.tsx
│   ├── UserMessage.tsx
│   └── SystemMessage.tsx
├── ActionCard/
│   ├── ActionCard.tsx
│   ├── ConfirmAction.tsx
│   ├── AdjustAction.tsx
│   └── SuggestionAction.tsx
├── Indicators/
│   ├── ConfidenceIndicator.tsx
│   ├── AIThinkingIndicator.tsx
│   ├── WinProbabilityBadge.tsx
│   └── ProcessingDots.tsx
├── Panels/
│   ├── ContextPanel.tsx
│   ├── VesselContext.tsx
│   ├── RFQContext.tsx
│   └── ComparisonContext.tsx
├── Upload/
│   ├── DocumentDropZone.tsx
│   └── UploadProgress.tsx
├── Voice/
│   ├── VoiceInputButton.tsx
│   └── VoiceWaveform.tsx
└── Quote/
    └── QuoteOptimizationCard.tsx
```

### CommandBar Component

The primary interaction point for PortiQ's conversation-first UX.

```tsx
// packages/design-system/components/ai/CommandBar/CommandBar.tsx
import { forwardRef } from 'react';
import { cn } from '@/lib/utils';

interface CommandBarProps {
  state: 'default' | 'focused' | 'voice-active' | 'processing';
  placeholder?: string;
  value: string;
  onChange: (value: string) => void;
  onVoiceToggle?: () => void;
  suggestions?: CommandSuggestion[];
  onSuggestionSelect?: (suggestion: CommandSuggestion) => void;
}

export const CommandBar = forwardRef<HTMLInputElement, CommandBarProps>(
  ({ state, placeholder, value, onChange, onVoiceToggle, suggestions, onSuggestionSelect }, ref) => {
    return (
      <div
        className={cn(
          'relative flex items-center gap-3 rounded-xl border px-4 py-3',
          'transition-all duration-200',
          state === 'default' && 'border-border bg-card',
          state === 'focused' && 'border-primary bg-card shadow-lg ring-2 ring-primary/20',
          state === 'voice-active' && 'border-secondary bg-secondary/5 shadow-lg ring-2 ring-secondary/30',
          state === 'processing' && 'border-primary/50 bg-primary/5'
        )}
      >
        <SearchIcon className="h-5 w-5 text-muted-foreground" />

        <input
          ref={ref}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder ?? "Ask PortiQ anything..."}
          className={cn(
            'flex-1 bg-transparent text-foreground placeholder:text-muted-foreground',
            'focus:outline-none'
          )}
          disabled={state === 'processing'}
        />

        {state === 'processing' && <AIThinkingIndicator variant="dots" />}

        <VoiceInputButton
          state={state === 'voice-active' ? 'listening' : 'idle'}
          onToggle={onVoiceToggle}
        />

        {state === 'focused' && suggestions?.length > 0 && (
          <CommandBarSuggestions
            suggestions={suggestions}
            onSelect={onSuggestionSelect}
          />
        )}
      </div>
    );
  }
);

// Design tokens for CommandBar
export const commandBarTokens = {
  height: {
    default: '56px',
    compact: '44px',
  },
  radius: 'var(--radius-xl)',
  padding: {
    x: 'var(--spacing-4)',
    y: 'var(--spacing-3)',
  },
  states: {
    default: {
      border: 'var(--border)',
      background: 'var(--card)',
    },
    focused: {
      border: 'var(--primary)',
      ring: 'var(--primary)/20',
      shadow: 'var(--shadow-lg)',
    },
    voiceActive: {
      border: 'var(--secondary)',
      background: 'var(--secondary)/5',
      ring: 'var(--secondary)/30',
    },
    processing: {
      border: 'var(--primary)/50',
      background: 'var(--primary)/5',
    },
  },
};
```

### ConversationBubble Component

Message bubbles for the conversation interface with distinct styling per sender type.

```tsx
// packages/design-system/components/ai/Conversation/ConversationBubble.tsx
interface ConversationBubbleProps {
  type: 'user' | 'ai' | 'system';
  children: React.ReactNode;
  timestamp?: Date;
  actions?: React.ReactNode;
  isStreaming?: boolean;
}

export function ConversationBubble({
  type,
  children,
  timestamp,
  actions,
  isStreaming,
}: ConversationBubbleProps) {
  return (
    <div
      className={cn(
        'flex gap-3 p-4 rounded-lg',
        type === 'user' && 'bg-primary text-primary-foreground ml-12',
        type === 'ai' && 'bg-muted mr-12',
        type === 'system' && 'bg-info/10 text-info-foreground border border-info/20 mx-4'
      )}
    >
      {type === 'ai' && (
        <div className="flex-shrink-0">
          <PortiQAvatar size="sm" />
        </div>
      )}

      <div className="flex-1 space-y-2">
        <div className={cn('prose prose-sm', isStreaming && 'animate-pulse')}>
          {children}
        </div>

        {actions && (
          <div className="flex flex-wrap gap-2 mt-3">
            {actions}
          </div>
        )}

        {timestamp && (
          <span className="text-xs text-muted-foreground">
            {formatTime(timestamp)}
          </span>
        )}
      </div>
    </div>
  );
}

// Design tokens
export const conversationBubbleTokens = {
  user: {
    background: 'var(--primary)',
    foreground: 'var(--primary-foreground)',
    marginLeft: 'var(--spacing-12)',
  },
  ai: {
    background: 'var(--muted)',
    foreground: 'var(--foreground)',
    marginRight: 'var(--spacing-12)',
  },
  system: {
    background: 'var(--info)/10',
    foreground: 'var(--info-foreground)',
    border: 'var(--info)/20',
  },
  borderRadius: 'var(--radius-lg)',
  padding: 'var(--spacing-4)',
  gap: 'var(--spacing-3)',
};
```

### ActionCard Component

Interactive cards for AI-suggested actions with confirm, adjust, question, and suggestion variants.

```tsx
// packages/design-system/components/ai/ActionCard/ActionCard.tsx
interface ActionCardProps {
  type: 'confirm' | 'adjust' | 'question' | 'suggestion';
  title: string;
  description?: string;
  confidence?: number;
  primaryAction?: { label: string; onClick: () => void };
  secondaryAction?: { label: string; onClick: () => void };
  children?: React.ReactNode;
}

export function ActionCard({
  type,
  title,
  description,
  confidence,
  primaryAction,
  secondaryAction,
  children,
}: ActionCardProps) {
  const icons = {
    confirm: CheckCircleIcon,
    adjust: AdjustmentsIcon,
    question: QuestionMarkCircleIcon,
    suggestion: LightBulbIcon,
  };
  const Icon = icons[type];

  return (
    <div
      className={cn(
        'rounded-lg border p-4 space-y-3',
        type === 'confirm' && 'border-success/30 bg-success/5',
        type === 'adjust' && 'border-warning/30 bg-warning/5',
        type === 'question' && 'border-info/30 bg-info/5',
        type === 'suggestion' && 'border-primary/30 bg-primary/5'
      )}
    >
      <div className="flex items-start gap-3">
        <Icon
          className={cn(
            'h-5 w-5 mt-0.5',
            type === 'confirm' && 'text-success',
            type === 'adjust' && 'text-warning',
            type === 'question' && 'text-info',
            type === 'suggestion' && 'text-primary'
          )}
        />
        <div className="flex-1">
          <div className="flex items-center justify-between">
            <h4 className="font-medium">{title}</h4>
            {confidence !== undefined && (
              <ConfidenceIndicator level={confidence} size="sm" />
            )}
          </div>
          {description && (
            <p className="text-sm text-muted-foreground mt-1">{description}</p>
          )}
        </div>
      </div>

      {children}

      {(primaryAction || secondaryAction) && (
        <div className="flex gap-2 pt-2">
          {secondaryAction && (
            <Button variant="outline" size="sm" onClick={secondaryAction.onClick}>
              {secondaryAction.label}
            </Button>
          )}
          {primaryAction && (
            <Button size="sm" onClick={primaryAction.onClick}>
              {primaryAction.label}
            </Button>
          )}
        </div>
      )}
    </div>
  );
}

// Design tokens
export const actionCardTokens = {
  confirm: {
    border: 'var(--success)/30',
    background: 'var(--success)/5',
    icon: 'var(--success)',
  },
  adjust: {
    border: 'var(--warning)/30',
    background: 'var(--warning)/5',
    icon: 'var(--warning)',
  },
  question: {
    border: 'var(--info)/30',
    background: 'var(--info)/5',
    icon: 'var(--info)',
  },
  suggestion: {
    border: 'var(--primary)/30',
    background: 'var(--primary)/5',
    icon: 'var(--primary)',
  },
};
```

### ConfidenceIndicator Component

Visual representation of AI confidence levels.

```tsx
// packages/design-system/components/ai/Indicators/ConfidenceIndicator.tsx
interface ConfidenceIndicatorProps {
  level: 'high' | 'medium' | 'low' | 'processing' | number;
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
}

export function ConfidenceIndicator({
  level,
  size = 'md',
  showLabel = true,
}: ConfidenceIndicatorProps) {
  const numericLevel = typeof level === 'number' ? level : null;
  const category = typeof level === 'string'
    ? level
    : level >= 0.8 ? 'high' : level >= 0.5 ? 'medium' : 'low';

  if (category === 'processing') {
    return (
      <div className="flex items-center gap-1.5">
        <div className="flex gap-0.5">
          {[0, 1, 2].map((i) => (
            <div
              key={i}
              className="h-2 w-2 rounded-full bg-primary animate-pulse"
              style={{ animationDelay: `${i * 150}ms` }}
            />
          ))}
        </div>
        {showLabel && (
          <span className="text-xs text-muted-foreground">Analyzing...</span>
        )}
      </div>
    );
  }

  return (
    <div className="flex items-center gap-1.5">
      <div
        className={cn(
          'flex items-center gap-0.5',
          size === 'sm' && 'h-3',
          size === 'md' && 'h-4',
          size === 'lg' && 'h-5'
        )}
      >
        {[0, 1, 2].map((i) => (
          <div
            key={i}
            className={cn(
              'rounded-full',
              size === 'sm' && 'h-1.5 w-1.5',
              size === 'md' && 'h-2 w-2',
              size === 'lg' && 'h-2.5 w-2.5',
              i === 0 && 'bg-current',
              i === 1 && (category === 'high' || category === 'medium' ? 'bg-current' : 'bg-current/30'),
              i === 2 && (category === 'high' ? 'bg-current' : 'bg-current/30'),
              category === 'high' && 'text-success',
              category === 'medium' && 'text-warning',
              category === 'low' && 'text-error'
            )}
          />
        ))}
      </div>
      {showLabel && (
        <span
          className={cn(
            'text-xs font-medium',
            category === 'high' && 'text-success',
            category === 'medium' && 'text-warning',
            category === 'low' && 'text-error'
          )}
        >
          {numericLevel ? `${Math.round(numericLevel * 100)}%` : category}
        </span>
      )}
    </div>
  );
}

// Design tokens
export const confidenceIndicatorTokens = {
  high: { color: 'var(--success)', label: 'High confidence' },
  medium: { color: 'var(--warning)', label: 'Review recommended' },
  low: { color: 'var(--error)', label: 'Needs verification' },
  processing: { color: 'var(--primary)', label: 'Analyzing...' },
  dotSize: { sm: '6px', md: '8px', lg: '10px' },
};
```

### ContextPanel Component

Side panel displaying current context (vessel, RFQ, comparison, or order).

```tsx
// packages/design-system/components/ai/Panels/ContextPanel.tsx
interface ContextPanelProps {
  type: 'vessel' | 'rfq' | 'comparison' | 'order';
  data: VesselContext | RFQContext | ComparisonContext | OrderContext;
  onClose?: () => void;
  collapsed?: boolean;
}

export function ContextPanel({ type, data, onClose, collapsed }: ContextPanelProps) {
  const headers = {
    vessel: { icon: ShipIcon, label: 'Active Vessel' },
    rfq: { icon: FileTextIcon, label: 'Current RFQ' },
    comparison: { icon: ScaleIcon, label: 'Quote Comparison' },
    order: { icon: PackageIcon, label: 'Order Details' },
  };
  const { icon: Icon, label } = headers[type];

  return (
    <aside
      className={cn(
        'border-l bg-card transition-all duration-200',
        collapsed ? 'w-12' : 'w-80'
      )}
    >
      <div className="flex items-center justify-between p-4 border-b">
        <div className="flex items-center gap-2">
          <Icon className="h-4 w-4 text-muted-foreground" />
          {!collapsed && <span className="font-medium text-sm">{label}</span>}
        </div>
        {onClose && !collapsed && (
          <Button variant="ghost" size="icon" onClick={onClose}>
            <XIcon className="h-4 w-4" />
          </Button>
        )}
      </div>

      {!collapsed && (
        <div className="p-4 space-y-4">
          {type === 'vessel' && <VesselContextContent data={data as VesselContext} />}
          {type === 'rfq' && <RFQContextContent data={data as RFQContext} />}
          {type === 'comparison' && <ComparisonContextContent data={data as ComparisonContext} />}
          {type === 'order' && <OrderContextContent data={data as OrderContext} />}
        </div>
      )}
    </aside>
  );
}

// Design tokens
export const contextPanelTokens = {
  width: { expanded: '320px', collapsed: '48px' },
  background: 'var(--card)',
  border: 'var(--border)',
  headerHeight: '56px',
  padding: 'var(--spacing-4)',
};
```

### DocumentDropZone Component

Drag-and-drop zone for document uploads with AI processing states.

```tsx
// packages/design-system/components/ai/Upload/DocumentDropZone.tsx
interface DocumentDropZoneProps {
  state: 'default' | 'dragover' | 'uploading' | 'processing';
  onDrop: (files: File[]) => void;
  accept?: string[];
  maxSize?: number;
  progress?: number;
  processingMessage?: string;
}

export function DocumentDropZone({
  state,
  onDrop,
  accept = ['application/pdf', 'image/*', 'application/vnd.ms-excel'],
  maxSize = 10 * 1024 * 1024,
  progress,
  processingMessage,
}: DocumentDropZoneProps) {
  return (
    <div
      className={cn(
        'relative rounded-xl border-2 border-dashed p-8 text-center transition-all duration-200',
        state === 'default' && 'border-border hover:border-primary/50 hover:bg-primary/5',
        state === 'dragover' && 'border-primary bg-primary/10 scale-[1.02]',
        state === 'uploading' && 'border-primary/50 bg-primary/5',
        state === 'processing' && 'border-secondary bg-secondary/5'
      )}
      onDragOver={(e) => e.preventDefault()}
      onDrop={(e) => {
        e.preventDefault();
        onDrop(Array.from(e.dataTransfer.files));
      }}
    >
      {state === 'default' && (
        <>
          <CloudUploadIcon className="h-12 w-12 mx-auto text-muted-foreground" />
          <p className="mt-4 text-sm text-muted-foreground">
            Drop requisition documents or <button className="text-primary underline">browse</button>
          </p>
          <p className="mt-1 text-xs text-muted-foreground">
            PDF, images, Excel up to {Math.round(maxSize / 1024 / 1024)}MB
          </p>
        </>
      )}

      {state === 'dragover' && (
        <>
          <CloudUploadIcon className="h-12 w-12 mx-auto text-primary animate-bounce" />
          <p className="mt-4 text-sm font-medium text-primary">
            Drop to upload
          </p>
        </>
      )}

      {state === 'uploading' && (
        <>
          <div className="h-12 w-12 mx-auto">
            <CircularProgress value={progress ?? 0} />
          </div>
          <p className="mt-4 text-sm text-muted-foreground">
            Uploading... {progress}%
          </p>
        </>
      )}

      {state === 'processing' && (
        <>
          <AIThinkingIndicator variant="scanning" size="lg" />
          <p className="mt-4 text-sm font-medium text-secondary">
            {processingMessage ?? 'PortiQ is analyzing your document...'}
          </p>
        </>
      )}
    </div>
  );
}

// Design tokens
export const documentDropZoneTokens = {
  borderRadius: 'var(--radius-xl)',
  borderWidth: '2px',
  padding: 'var(--spacing-8)',
  states: {
    default: {
      border: 'var(--border)',
      hoverBorder: 'var(--primary)/50',
      hoverBackground: 'var(--primary)/5',
    },
    dragover: {
      border: 'var(--primary)',
      background: 'var(--primary)/10',
      scale: '1.02',
    },
    uploading: {
      border: 'var(--primary)/50',
      background: 'var(--primary)/5',
    },
    processing: {
      border: 'var(--secondary)',
      background: 'var(--secondary)/5',
    },
  },
};
```

### VoiceInputButton Component

Microphone button with visual feedback for voice input states.

```tsx
// packages/design-system/components/ai/Voice/VoiceInputButton.tsx
interface VoiceInputButtonProps {
  state: 'idle' | 'listening' | 'processing';
  onToggle?: () => void;
  size?: 'sm' | 'md' | 'lg';
}

export function VoiceInputButton({
  state,
  onToggle,
  size = 'md',
}: VoiceInputButtonProps) {
  return (
    <button
      onClick={onToggle}
      className={cn(
        'relative rounded-full flex items-center justify-center transition-all duration-200',
        size === 'sm' && 'h-8 w-8',
        size === 'md' && 'h-10 w-10',
        size === 'lg' && 'h-14 w-14',
        state === 'idle' && 'bg-muted text-muted-foreground hover:bg-primary hover:text-primary-foreground',
        state === 'listening' && 'bg-secondary text-secondary-foreground animate-pulse',
        state === 'processing' && 'bg-primary/20 text-primary'
      )}
      disabled={state === 'processing'}
    >
      {state === 'listening' && (
        <span className="absolute inset-0 rounded-full bg-secondary/30 animate-ping" />
      )}

      <MicrophoneIcon
        className={cn(
          'relative z-10',
          size === 'sm' && 'h-4 w-4',
          size === 'md' && 'h-5 w-5',
          size === 'lg' && 'h-6 w-6'
        )}
      />
    </button>
  );
}

// Design tokens
export const voiceInputButtonTokens = {
  size: { sm: '32px', md: '40px', lg: '56px' },
  iconSize: { sm: '16px', md: '20px', lg: '24px' },
  states: {
    idle: {
      background: 'var(--muted)',
      foreground: 'var(--muted-foreground)',
      hoverBackground: 'var(--primary)',
      hoverForeground: 'var(--primary-foreground)',
    },
    listening: {
      background: 'var(--secondary)',
      foreground: 'var(--secondary-foreground)',
      ringColor: 'var(--secondary)/30',
    },
    processing: {
      background: 'var(--primary)/20',
      foreground: 'var(--primary)',
    },
  },
};
```

### AIThinkingIndicator Component

Visual feedback for AI processing with multiple animation variants.

```tsx
// packages/design-system/components/ai/Indicators/AIThinkingIndicator.tsx
interface AIThinkingIndicatorProps {
  variant: 'dots' | 'steps' | 'scanning';
  size?: 'sm' | 'md' | 'lg';
  steps?: { label: string; completed: boolean }[];
}

export function AIThinkingIndicator({
  variant,
  size = 'md',
  steps,
}: AIThinkingIndicatorProps) {
  if (variant === 'dots') {
    return (
      <div className="flex items-center gap-1">
        {[0, 1, 2].map((i) => (
          <div
            key={i}
            className={cn(
              'rounded-full bg-primary animate-bounce',
              size === 'sm' && 'h-1.5 w-1.5',
              size === 'md' && 'h-2 w-2',
              size === 'lg' && 'h-3 w-3'
            )}
            style={{ animationDelay: `${i * 100}ms` }}
          />
        ))}
      </div>
    );
  }

  if (variant === 'steps' && steps) {
    return (
      <div className="space-y-2">
        {steps.map((step, i) => (
          <div key={i} className="flex items-center gap-2 text-sm">
            {step.completed ? (
              <CheckCircleIcon className="h-4 w-4 text-success" />
            ) : (
              <div className="h-4 w-4 rounded-full border-2 border-primary border-t-transparent animate-spin" />
            )}
            <span className={step.completed ? 'text-muted-foreground' : 'text-foreground'}>
              {step.label}
            </span>
          </div>
        ))}
      </div>
    );
  }

  if (variant === 'scanning') {
    return (
      <div
        className={cn(
          'relative flex items-center justify-center',
          size === 'sm' && 'h-8 w-8',
          size === 'md' && 'h-12 w-12',
          size === 'lg' && 'h-16 w-16'
        )}
      >
        <div className="absolute inset-0 rounded-full border-2 border-primary/30" />
        <div className="absolute inset-0 rounded-full border-2 border-primary border-t-transparent animate-spin" />
        <DocumentIcon className="h-1/2 w-1/2 text-primary" />
      </div>
    );
  }

  return null;
}

// Design tokens
export const aiThinkingIndicatorTokens = {
  dots: {
    gap: 'var(--spacing-1)',
    color: 'var(--primary)',
    animationDuration: '600ms',
  },
  steps: {
    gap: 'var(--spacing-2)',
    completedColor: 'var(--success)',
    activeColor: 'var(--primary)',
  },
  scanning: {
    borderColor: 'var(--primary)',
    animationDuration: '1000ms',
  },
};
```

### WinProbabilityBadge Component

Displays supplier win probability for quote opportunities.

```tsx
// packages/design-system/components/ai/Indicators/WinProbabilityBadge.tsx
interface WinProbabilityBadgeProps {
  probability: number; // 0-100
  size?: 'sm' | 'md' | 'lg';
  showTrend?: boolean;
  trend?: 'up' | 'down' | 'stable';
}

export function WinProbabilityBadge({
  probability,
  size = 'md',
  showTrend,
  trend,
}: WinProbabilityBadgeProps) {
  const level = probability >= 70 ? 'high' : probability >= 40 ? 'medium' : 'low';

  return (
    <div
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 font-medium',
        size === 'sm' && 'text-xs',
        size === 'md' && 'text-sm',
        size === 'lg' && 'text-base px-3 py-1.5',
        level === 'high' && 'bg-success/10 text-success',
        level === 'medium' && 'bg-warning/10 text-warning',
        level === 'low' && 'bg-error/10 text-error'
      )}
    >
      <span>{probability}%</span>
      {showTrend && trend && (
        <>
          {trend === 'up' && <TrendingUpIcon className="h-3 w-3" />}
          {trend === 'down' && <TrendingDownIcon className="h-3 w-3" />}
          {trend === 'stable' && <MinusIcon className="h-3 w-3" />}
        </>
      )}
    </div>
  );
}

// Design tokens
export const winProbabilityBadgeTokens = {
  high: { background: 'var(--success)/10', foreground: 'var(--success)', threshold: 70 },
  medium: { background: 'var(--warning)/10', foreground: 'var(--warning)', threshold: 40 },
  low: { background: 'var(--error)/10', foreground: 'var(--error)', threshold: 0 },
  borderRadius: 'var(--radius-full)',
};
```

### QuoteOptimizationCard Component

Displays quote optimization strategies for suppliers.

```tsx
// packages/design-system/components/ai/Quote/QuoteOptimizationCard.tsx
interface QuoteOptimizationCardProps {
  strategy: 'aggressive' | 'balanced' | 'premium';
  price: number;
  winProbability: number;
  margin: number;
  reasoning: string;
  onSelect: () => void;
  isRecommended?: boolean;
  isSelected?: boolean;
}

export function QuoteOptimizationCard({
  strategy,
  price,
  winProbability,
  margin,
  reasoning,
  onSelect,
  isRecommended,
  isSelected,
}: QuoteOptimizationCardProps) {
  const icons = {
    aggressive: ZapIcon,
    balanced: ScaleIcon,
    premium: StarIcon,
  };
  const labels = {
    aggressive: 'Aggressive',
    balanced: 'Balanced',
    premium: 'Premium',
  };
  const Icon = icons[strategy];

  return (
    <button
      onClick={onSelect}
      className={cn(
        'relative w-full rounded-lg border p-4 text-left transition-all duration-200',
        'hover:border-primary hover:shadow-md',
        isSelected && 'border-primary ring-2 ring-primary/20',
        !isSelected && 'border-border'
      )}
    >
      {isRecommended && (
        <span className="absolute -top-2 left-4 px-2 py-0.5 text-xs font-medium bg-primary text-primary-foreground rounded-full">
          Recommended
        </span>
      )}

      <div className="flex items-start gap-3">
        <div
          className={cn(
            'rounded-lg p-2',
            strategy === 'aggressive' && 'bg-warning/10 text-warning',
            strategy === 'balanced' && 'bg-primary/10 text-primary',
            strategy === 'premium' && 'bg-secondary/10 text-secondary'
          )}
        >
          <Icon className="h-5 w-5" />
        </div>

        <div className="flex-1">
          <h4 className="font-medium">{labels[strategy]}</h4>
          <div className="mt-2 grid grid-cols-3 gap-4 text-sm">
            <div>
              <span className="text-muted-foreground">Price</span>
              <p className="font-semibold">{formatCurrency(price)}</p>
            </div>
            <div>
              <span className="text-muted-foreground">Win %</span>
              <p className="font-semibold">{winProbability}%</p>
            </div>
            <div>
              <span className="text-muted-foreground">Margin</span>
              <p className="font-semibold">{margin}%</p>
            </div>
          </div>
          <p className="mt-2 text-xs text-muted-foreground">{reasoning}</p>
        </div>

        {isSelected && (
          <CheckCircleIcon className="h-5 w-5 text-primary flex-shrink-0" />
        )}
      </div>
    </button>
  );
}

// Design tokens
export const quoteOptimizationCardTokens = {
  aggressive: { icon: 'var(--warning)', background: 'var(--warning)/10' },
  balanced: { icon: 'var(--primary)', background: 'var(--primary)/10' },
  premium: { icon: 'var(--secondary)', background: 'var(--secondary)/10' },
  borderRadius: 'var(--radius-lg)',
  selectedRing: 'var(--primary)/20',
};
```

### AI Component Animation Specifications

```tsx
// packages/design-system/animations/ai-animations.ts
export const aiAnimations = {
  // Command bar focus transition
  commandBarFocus: {
    duration: '200ms',
    easing: 'ease-out',
    properties: ['border-color', 'box-shadow', 'background-color'],
  },

  // Conversation bubble entrance
  bubbleEntrance: {
    duration: '300ms',
    easing: 'cubic-bezier(0.16, 1, 0.3, 1)',
    keyframes: {
      from: { opacity: 0, transform: 'translateY(10px)' },
      to: { opacity: 1, transform: 'translateY(0)' },
    },
  },

  // AI streaming text
  streamingText: {
    cursor: {
      animation: 'blink 1s step-end infinite',
      keyframes: {
        '0%, 100%': { opacity: 1 },
        '50%': { opacity: 0 },
      },
    },
  },

  // Thinking dots bounce
  thinkingDots: {
    duration: '600ms',
    easing: 'ease-in-out',
    keyframes: {
      '0%, 100%': { transform: 'translateY(0)' },
      '50%': { transform: 'translateY(-4px)' },
    },
  },

  // Document scanning rotation
  scanningRotation: {
    duration: '1000ms',
    easing: 'linear',
    iteration: 'infinite',
  },

  // Voice listening pulse
  voiceListeningPulse: {
    duration: '1500ms',
    easing: 'ease-out',
    iteration: 'infinite',
    keyframes: {
      '0%': { transform: 'scale(1)', opacity: 1 },
      '100%': { transform: 'scale(1.5)', opacity: 0 },
    },
  },

  // Action card selection
  cardSelection: {
    duration: '150ms',
    easing: 'ease-out',
    properties: ['border-color', 'box-shadow'],
  },

  // Drop zone scale on drag
  dropZoneScale: {
    duration: '200ms',
    easing: 'ease-out',
    properties: ['transform', 'border-color', 'background-color'],
  },
};
```

### AI Component Accessibility Requirements

| Component | ARIA Role | Keyboard Support | Screen Reader |
|-----------|-----------|-----------------|---------------|
| CommandBar | `combobox` | Arrow keys, Enter, Escape | Announce suggestions count |
| ConversationBubble | `article` | Tab to focus | Read sender type + content |
| ActionCard | `button` | Enter/Space to activate | Describe action type + confidence |
| ConfidenceIndicator | `status` | — | Announce level ("High confidence") |
| ContextPanel | `complementary` | Tab navigation | Announce context type |
| DocumentDropZone | `button` | Enter to open picker | Announce drop zone state |
| VoiceInputButton | `button` | Space to toggle | Announce "Start/Stop listening" |
| AIThinkingIndicator | `status` | — | Announce processing state |

### Mobile React Native Variants

All AI components have React Native equivalents with platform-appropriate interactions:

```tsx
// packages/design-system/mobile/ai/CommandBar.native.tsx
import { TextInput, Pressable, View } from 'react-native';
import Animated, { useAnimatedStyle, withSpring } from 'react-native-reanimated';

export function CommandBar({ state, ...props }: CommandBarProps) {
  const animatedStyle = useAnimatedStyle(() => ({
    borderColor: withSpring(state === 'focused' ? tokens.primary : tokens.border),
    transform: [{ scale: withSpring(state === 'voice-active' ? 1.02 : 1) }],
  }));

  return (
    <Animated.View style={[styles.container, animatedStyle]}>
      {/* Native implementation */}
    </Animated.View>
  );
}
```

---

## References
- [Design Tokens](https://www.designtokens.org/)
- [Tailwind CSS Theming](https://tailwindcss.com/docs/customizing-colors)
- [shadcn/ui Theming](https://ui.shadcn.com/docs/theming)
- [ADR-UI-013: PortiQ Buyer Experience](./ADR-UI-013-portiq-buyer-experience.md)
- [ADR-UI-014: PortiQ Supplier Experience](./ADR-UI-014-portiq-supplier-experience.md)
- [ADR-UI-015: Command Bar & Voice Input](./ADR-UI-015-command-bar-voice-input.md)
