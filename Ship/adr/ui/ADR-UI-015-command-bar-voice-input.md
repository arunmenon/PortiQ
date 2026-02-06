# ADR-UI-015: Command Bar & Voice Input Architecture

**Status:** Accepted
**Date:** 2026-02-06
**Technical Area:** Frontend
**Supersedes:** ADR-UI-011

---

## Context

The PortiQ UX Design Specification positions **natural language as the primary input method** for the platform. Rather than traditional search boxes and navigation menus, users interact with a unified Command Bar that accepts text, voice, and structured commands. This fundamentally changes the search UX pattern from faceted search (ADR-UI-011) to conversational intent recognition.

### Business Context

The traditional search approach (ADR-UI-011) required users to:
- Know specific IMPA codes or product names
- Navigate through faceted filters manually
- Perform multiple searches to refine results
- Switch between search and other actions

The PortiQ Command Bar approach enables:
- **Voice input adoption: > 30%** for mobile/field users
- **Natural language queries** like "Find rope for deck repairs"
- **Action shortcuts** like "Create RFQ for last month's order"
- **Zero-click completions** through AI understanding
- **Unified access** to all platform features

### Technical Context

- Web Speech API for browser voice input
- expo-speech for React Native voice input
- NLU (Natural Language Understanding) service for intent parsing
- Meilisearch backend for product search (preserved from ADR-NF-003)
- Streaming responses for real-time feedback

### Assumptions

- Users prefer natural language over structured queries
- Voice input is viable in maritime/port environments
- NLU can accurately parse procurement intents
- Browser Speech API has sufficient accuracy

---

## Decision Drivers

- Reduce cognitive load for search and navigation
- Enable voice input for mobile/field operations
- Unify all platform actions through single entry point
- Maintain speed for power users (keyboard shortcuts)
- Support both precise (IMPA code) and fuzzy (natural language) searches

---

## Decision

We will implement a **unified Command Bar** as the primary interaction method across web and mobile platforms. The Command Bar accepts text input, voice input, and keyboard shortcuts, routing queries to either product search, action execution, or conversational AI based on intent classification.

---

## Implementation Notes

### Command Bar Component Specification

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│   ┌───────────────────────────────────────────────────────────────────┐    │
│   │ 🎤  Ask PortiQ anything...                              ⌘K       │    │
│   └───────────────────────────────────────────────────────────────────┘    │
│                                                                             │
│   Default State                                                             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│   ┌───────────────────────────────────────────────────────────────────┐    │
│   │ 🎤  Find safety equipment for deck|                       ⌘K     │    │
│   ├───────────────────────────────────────────────────────────────────┤    │
│   │                                                                   │    │
│   │ 🔍 Search Results                                                 │    │
│   │ ┌───────────────────────────────────────────────────────────────┐│    │
│   │ │ 📦 470201 Safety Helmet, White                                ││    │
│   │ │    Deck & Safety > Personal Protection                        ││    │
│   │ └───────────────────────────────────────────────────────────────┘│    │
│   │ ┌───────────────────────────────────────────────────────────────┐│    │
│   │ │ 📦 470301 Safety Harness, Full Body                           ││    │
│   │ │    Deck & Safety > Fall Protection                            ││    │
│   │ └───────────────────────────────────────────────────────────────┘│    │
│   │                                                                   │    │
│   │ ⚡ Quick Actions                                                  │    │
│   │ ┌───────────────────────────────────────────────────────────────┐│    │
│   │ │ ➕ Create RFQ for safety equipment                            ││    │
│   │ └───────────────────────────────────────────────────────────────┘│    │
│   │ ┌───────────────────────────────────────────────────────────────┐│    │
│   │ │ 💬 Ask PortiQ about safety equipment requirements            ││    │
│   │ └───────────────────────────────────────────────────────────────┘│    │
│   │                                                                   │    │
│   │ Press Enter to search • Tab to navigate • Esc to close          │    │
│   └───────────────────────────────────────────────────────────────────┘    │
│                                                                             │
│   Focused State with Suggestions                                           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│   ┌───────────────────────────────────────────────────────────────────┐    │
│   │ 🔴  Listening...                                          [Stop] │    │
│   │                                                                   │    │
│   │     ∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿                       │    │
│   │                                                                   │    │
│   │ "Find safety equipment for..."                                   │    │
│   └───────────────────────────────────────────────────────────────────┘    │
│                                                                             │
│   Voice Active State                                                       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│   ┌───────────────────────────────────────────────────────────────────┐    │
│   │ ● ● ●  Processing...                                             │    │
│   │                                                                   │    │
│   │ Understanding your request                                       │    │
│   └───────────────────────────────────────────────────────────────────┘    │
│                                                                             │
│   Processing State                                                         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Command Bar Implementation

```typescript
// components/portiq/command-bar.tsx
'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { Command } from 'cmdk';
import { useDebounce } from '@/hooks/use-debounce';
import { useVoiceInput } from '@/hooks/use-voice-input';
import { useCommandBarStore } from '@/stores/command-bar-store';
import { classifyIntent, IntentType } from '@/lib/nlu/intent-classifier';
import { searchProducts } from '@/lib/search/meilisearch-client';
import { getCommandSuggestions } from '@/lib/portiq/commands';

interface CommandBarProps {
  onAction: (action: CommandAction) => void;
  onConversation: (message: string) => void;
  placeholder?: string;
  autoFocus?: boolean;
}

export function CommandBar({
  onAction,
  onConversation,
  placeholder = "Ask PortiQ anything...",
  autoFocus = false,
}: CommandBarProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [query, setQuery] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(0);

  const debouncedQuery = useDebounce(query, 150);
  const { results, isLoading, suggestions } = useCommandBarResults(debouncedQuery);

  // Voice input
  const {
    isListening,
    transcript,
    startListening,
    stopListening,
    isSupported: voiceSupported,
  } = useVoiceInput({
    continuous: false,
    onResult: (text) => {
      setQuery(text);
      handleSubmit(text);
    },
  });

  // Keyboard shortcut: ⌘K / Ctrl+K
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setIsOpen(true);
        inputRef.current?.focus();
      }
      if (e.key === 'Escape') {
        setIsOpen(false);
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, []);

  const handleSubmit = useCallback(async (input: string) => {
    if (!input.trim()) return;

    // Classify intent
    const intent = await classifyIntent(input);

    switch (intent.type) {
      case 'search':
        // Direct product search
        onAction({ type: 'search', params: { query: input } });
        break;

      case 'navigation':
        // Navigate to a page
        onAction({ type: 'navigate', params: intent.params });
        break;

      case 'action':
        // Execute an action (create RFQ, etc.)
        onAction({ type: 'execute', params: intent.params });
        break;

      case 'conversation':
      default:
        // Send to PortiQ AI
        onConversation(input);
        break;
    }

    setQuery('');
    setIsOpen(false);
  }, [onAction, onConversation]);

  const handleSelect = useCallback((item: CommandBarItem) => {
    switch (item.type) {
      case 'product':
        onAction({ type: 'navigate', params: { path: `/catalog/products/${item.id}` } });
        break;
      case 'action':
        onAction({ type: 'execute', params: item.action });
        break;
      case 'conversation':
        onConversation(item.prompt || query);
        break;
    }
    setQuery('');
    setIsOpen(false);
  }, [onAction, onConversation, query]);

  return (
    <Command.Dialog
      open={isOpen}
      onOpenChange={setIsOpen}
      label="Command Bar"
      className="fixed inset-x-4 top-[15%] md:inset-x-auto md:left-1/2 md:-translate-x-1/2 md:w-full md:max-w-2xl z-50"
    >
      <div className="bg-popover rounded-xl shadow-2xl border overflow-hidden">
        {/* Input */}
        <div className="flex items-center border-b px-4">
          {isListening ? (
            <div className="flex items-center gap-2 flex-1 py-3">
              <div className="h-3 w-3 rounded-full bg-red-500 animate-pulse" />
              <span className="text-sm text-muted-foreground">Listening...</span>
              <VoiceWaveform className="flex-1 h-8" />
              <Button variant="ghost" size="sm" onClick={stopListening}>
                Stop
              </Button>
            </div>
          ) : (
            <>
              {voiceSupported && (
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={startListening}
                  className="mr-2"
                >
                  <Mic className="h-4 w-4" />
                </Button>
              )}
              <Command.Input
                ref={inputRef}
                value={query}
                onValueChange={setQuery}
                placeholder={placeholder}
                className="flex-1 h-12 text-sm bg-transparent outline-none placeholder:text-muted-foreground"
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !results.length) {
                    handleSubmit(query);
                  }
                }}
              />
              {isLoading && <Loader2 className="h-4 w-4 animate-spin" />}
              <kbd className="hidden md:flex text-xs text-muted-foreground ml-2">⌘K</kbd>
            </>
          )}
        </div>

        {/* Results */}
        <Command.List className="max-h-[400px] overflow-y-auto p-2">
          <Command.Empty className="py-6 text-center text-sm text-muted-foreground">
            {query.length < 2
              ? 'Type to search or ask a question...'
              : 'No results found. Press Enter to ask PortiQ.'}
          </Command.Empty>

          {/* Product Results */}
          {results.products.length > 0 && (
            <Command.Group heading="Products">
              {results.products.map((product) => (
                <Command.Item
                  key={product.id}
                  value={product.impaCode}
                  onSelect={() => handleSelect({ type: 'product', ...product })}
                  className="flex items-start gap-3 px-3 py-2 rounded-md cursor-pointer aria-selected:bg-accent"
                >
                  <Package className="h-4 w-4 mt-0.5 text-muted-foreground" />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs bg-primary/10 text-primary px-1.5 py-0.5 rounded">
                        {product.impaCode}
                      </span>
                    </div>
                    <p className="text-sm font-medium truncate">{product.name}</p>
                    <p className="text-xs text-muted-foreground">{product.category}</p>
                  </div>
                </Command.Item>
              ))}
            </Command.Group>
          )}

          {/* Quick Actions */}
          {suggestions.actions.length > 0 && (
            <Command.Group heading="Quick Actions">
              {suggestions.actions.map((action, i) => (
                <Command.Item
                  key={i}
                  value={action.label}
                  onSelect={() => handleSelect({ type: 'action', action })}
                  className="flex items-center gap-3 px-3 py-2 rounded-md cursor-pointer aria-selected:bg-accent"
                >
                  <Zap className="h-4 w-4 text-primary" />
                  <span className="text-sm">{action.label}</span>
                </Command.Item>
              ))}
            </Command.Group>
          )}

          {/* AI Conversation */}
          {query.length >= 2 && (
            <Command.Group heading="Ask PortiQ">
              <Command.Item
                value="ask-portiq"
                onSelect={() => handleSelect({ type: 'conversation', prompt: query })}
                className="flex items-center gap-3 px-3 py-2 rounded-md cursor-pointer aria-selected:bg-accent"
              >
                <MessageSquare className="h-4 w-4 text-primary" />
                <span className="text-sm">Ask PortiQ: "{query}"</span>
              </Command.Item>
            </Command.Group>
          )}
        </Command.List>

        {/* Footer */}
        <div className="flex items-center justify-between px-4 py-2 border-t text-xs text-muted-foreground">
          <div className="flex items-center gap-4">
            <span><kbd className="px-1 bg-muted rounded">↵</kbd> Select</span>
            <span><kbd className="px-1 bg-muted rounded">↑↓</kbd> Navigate</span>
            <span><kbd className="px-1 bg-muted rounded">Esc</kbd> Close</span>
          </div>
          {voiceSupported && (
            <span><kbd className="px-1 bg-muted rounded">🎤</kbd> Voice input</span>
          )}
        </div>
      </div>
    </Command.Dialog>
  );
}
```

### Voice Input Integration

```typescript
// hooks/use-voice-input.ts
import { useState, useEffect, useCallback, useRef } from 'react';

interface UseVoiceInputOptions {
  continuous?: boolean;
  interimResults?: boolean;
  language?: string;
  onResult?: (transcript: string) => void;
  onError?: (error: Error) => void;
}

interface UseVoiceInputReturn {
  isListening: boolean;
  transcript: string;
  interimTranscript: string;
  startListening: () => void;
  stopListening: () => void;
  resetTranscript: () => void;
  isSupported: boolean;
  error: Error | null;
}

export function useVoiceInput(options: UseVoiceInputOptions = {}): UseVoiceInputReturn {
  const {
    continuous = false,
    interimResults = true,
    language = 'en-US',
    onResult,
    onError,
  } = options;

  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [interimTranscript, setInterimTranscript] = useState('');
  const [error, setError] = useState<Error | null>(null);

  const recognitionRef = useRef<SpeechRecognition | null>(null);

  // Check browser support
  const isSupported = typeof window !== 'undefined' &&
    ('SpeechRecognition' in window || 'webkitSpeechRecognition' in window);

  useEffect(() => {
    if (!isSupported) return;

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new SpeechRecognition();

    recognition.continuous = continuous;
    recognition.interimResults = interimResults;
    recognition.lang = language;

    recognition.onstart = () => {
      setIsListening(true);
      setError(null);
    };

    recognition.onend = () => {
      setIsListening(false);
    };

    recognition.onresult = (event) => {
      let finalTranscript = '';
      let interim = '';

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i];
        if (result.isFinal) {
          finalTranscript += result[0].transcript;
        } else {
          interim += result[0].transcript;
        }
      }

      if (finalTranscript) {
        setTranscript(finalTranscript);
        setInterimTranscript('');
        onResult?.(finalTranscript);
      } else {
        setInterimTranscript(interim);
      }
    };

    recognition.onerror = (event) => {
      const err = new Error(`Speech recognition error: ${event.error}`);
      setError(err);
      setIsListening(false);
      onError?.(err);
    };

    recognitionRef.current = recognition;

    return () => {
      recognition.abort();
    };
  }, [continuous, interimResults, language, onResult, onError, isSupported]);

  const startListening = useCallback(() => {
    if (!recognitionRef.current || isListening) return;

    setTranscript('');
    setInterimTranscript('');
    recognitionRef.current.start();
  }, [isListening]);

  const stopListening = useCallback(() => {
    if (!recognitionRef.current || !isListening) return;
    recognitionRef.current.stop();
  }, [isListening]);

  const resetTranscript = useCallback(() => {
    setTranscript('');
    setInterimTranscript('');
  }, []);

  return {
    isListening,
    transcript,
    interimTranscript,
    startListening,
    stopListening,
    resetTranscript,
    isSupported,
    error,
  };
}
```

### Voice Waveform Visualization

```typescript
// components/ui/voice-waveform.tsx
'use client';

import { useEffect, useRef } from 'react';

interface VoiceWaveformProps {
  className?: string;
  barCount?: number;
  isActive?: boolean;
}

export function VoiceWaveform({
  className,
  barCount = 20,
  isActive = true,
}: VoiceWaveformProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationRef = useRef<number>();
  const analyserRef = useRef<AnalyserNode | null>(null);

  useEffect(() => {
    if (!isActive) return;

    const setupAudio = async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const audioContext = new AudioContext();
        const source = audioContext.createMediaStreamSource(stream);
        const analyser = audioContext.createAnalyser();

        analyser.fftSize = 64;
        source.connect(analyser);
        analyserRef.current = analyser;

        const canvas = canvasRef.current;
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        const bufferLength = analyser.frequencyBinCount;
        const dataArray = new Uint8Array(bufferLength);

        const draw = () => {
          animationRef.current = requestAnimationFrame(draw);

          analyser.getByteFrequencyData(dataArray);

          ctx.clearRect(0, 0, canvas.width, canvas.height);

          const barWidth = canvas.width / barCount;
          const step = Math.floor(bufferLength / barCount);

          for (let i = 0; i < barCount; i++) {
            const value = dataArray[i * step];
            const barHeight = (value / 255) * canvas.height * 0.8;

            const x = i * barWidth + barWidth / 4;
            const y = (canvas.height - barHeight) / 2;

            ctx.fillStyle = 'hsl(var(--primary))';
            ctx.fillRect(x, y, barWidth / 2, barHeight);
          }
        };

        draw();

        return () => {
          stream.getTracks().forEach(track => track.stop());
          audioContext.close();
        };
      } catch (err) {
        console.error('Failed to setup audio:', err);
      }
    };

    const cleanup = setupAudio();

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
      cleanup?.then(fn => fn?.());
    };
  }, [isActive, barCount]);

  return (
    <canvas
      ref={canvasRef}
      className={className}
      width={200}
      height={32}
    />
  );
}
```

### Suggestion Types

```typescript
// lib/nlu/intent-classifier.ts

export type IntentType =
  | 'search'        // Product/catalog search
  | 'navigation'    // Navigate to a page
  | 'action'        // Execute a platform action
  | 'conversation'  // Send to AI for processing

export interface Intent {
  type: IntentType;
  confidence: number;
  params: Record<string, any>;
}

// Pattern-based intent classification (fast, client-side)
const patterns: { pattern: RegExp; type: IntentType; extractor?: (match: RegExpMatchArray) => Record<string, any> }[] = [
  // Direct IMPA code lookup
  {
    pattern: /^(\d{6})$/,
    type: 'search',
    extractor: (match) => ({ impaCode: match[1] }),
  },
  // Navigation commands
  {
    pattern: /^(?:go to|show|open)\s+(dashboard|orders?|rfqs?|catalog|settings|inventory)/i,
    type: 'navigation',
    extractor: (match) => ({ path: `/${match[1].toLowerCase()}` }),
  },
  // RFQ actions
  {
    pattern: /^(?:create|new|start)\s+(?:an?\s+)?rfq/i,
    type: 'action',
    extractor: () => ({ action: 'create_rfq' }),
  },
  {
    pattern: /^(?:quote|submit quote for)\s+(?:rfq[- ]?)?(\d+|RFQ-\d+-\d+)/i,
    type: 'action',
    extractor: (match) => ({ action: 'quote_rfq', rfqId: match[1] }),
  },
  // Search patterns
  {
    pattern: /^(?:find|search|look for)\s+(.+)/i,
    type: 'search',
    extractor: (match) => ({ query: match[1] }),
  },
];

export async function classifyIntent(input: string): Promise<Intent> {
  // Try pattern matching first (fast)
  for (const { pattern, type, extractor } of patterns) {
    const match = input.match(pattern);
    if (match) {
      return {
        type,
        confidence: 0.95,
        params: extractor?.(match) || {},
      };
    }
  }

  // For longer/complex queries, default to conversation
  // Could also call NLU service here for more sophisticated classification
  if (input.length > 50 || input.includes('?')) {
    return {
      type: 'conversation',
      confidence: 0.8,
      params: { message: input },
    };
  }

  // Default to search for short queries
  return {
    type: 'search',
    confidence: 0.7,
    params: { query: input },
  };
}
```

### Processing States

```typescript
// components/ui/ai-thinking-indicator.tsx
interface AIThinkingIndicatorProps {
  variant: 'dots' | 'steps' | 'scanning';
  steps?: ThinkingStep[];
}

interface ThinkingStep {
  label: string;
  status: 'pending' | 'active' | 'complete';
}

export function AIThinkingIndicator({ variant, steps }: AIThinkingIndicatorProps) {
  if (variant === 'dots') {
    return (
      <div className="flex items-center gap-1">
        <span className="h-2 w-2 rounded-full bg-primary animate-bounce" style={{ animationDelay: '0ms' }} />
        <span className="h-2 w-2 rounded-full bg-primary animate-bounce" style={{ animationDelay: '150ms' }} />
        <span className="h-2 w-2 rounded-full bg-primary animate-bounce" style={{ animationDelay: '300ms' }} />
      </div>
    );
  }

  if (variant === 'steps' && steps) {
    return (
      <div className="space-y-2">
        {steps.map((step, i) => (
          <div key={i} className="flex items-center gap-2 text-sm">
            {step.status === 'complete' && <Check className="h-4 w-4 text-green-500" />}
            {step.status === 'active' && <Loader2 className="h-4 w-4 animate-spin text-primary" />}
            {step.status === 'pending' && <Circle className="h-4 w-4 text-muted-foreground" />}
            <span className={cn(
              step.status === 'active' && 'text-primary font-medium',
              step.status === 'complete' && 'text-muted-foreground',
              step.status === 'pending' && 'text-muted-foreground'
            )}>
              {step.label}
            </span>
          </div>
        ))}
      </div>
    );
  }

  if (variant === 'scanning') {
    return (
      <div className="relative h-1 w-full bg-muted rounded-full overflow-hidden">
        <div className="absolute inset-y-0 left-0 w-1/3 bg-primary rounded-full animate-scan" />
      </div>
    );
  }

  return null;
}
```

### Mobile Voice-First Layout

```
┌─────────────────────────────────┐
│  🚢 PortiQ            [🔔] [≡] │
├─────────────────────────────────┤
│                                 │
│                                 │
│                                 │
│                                 │
│        ┌─────────────┐          │
│        │             │          │
│        │     🎤      │          │
│        │             │          │
│        │  Tap to     │          │
│        │  speak      │          │
│        │             │          │
│        └─────────────┘          │
│                                 │
│   "Find provisions for         │
│    MV Pacific Star"            │
│                                 │
│   "Show my pending RFQs"       │
│                                 │
│   "Quote for RFQ 2024-0158"    │
│                                 │
│                                 │
├─────────────────────────────────┤
│ [Type instead...]         ⌨️   │
└─────────────────────────────────┘

Voice-First Mobile Home
```

### React Native Voice Input

```typescript
// apps/mobile/hooks/use-mobile-voice-input.ts
import { useState, useCallback, useEffect } from 'react';
import * as Speech from 'expo-speech';
import { Audio } from 'expo-av';

interface UseMobileVoiceInputOptions {
  language?: string;
  onResult?: (transcript: string) => void;
  onError?: (error: Error) => void;
}

export function useMobileVoiceInput(options: UseMobileVoiceInputOptions = {}) {
  const { language = 'en-US', onResult, onError } = options;

  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [permissionStatus, setPermissionStatus] = useState<'granted' | 'denied' | 'undetermined'>('undetermined');

  useEffect(() => {
    // Request microphone permission
    const requestPermission = async () => {
      const { status } = await Audio.requestPermissionsAsync();
      setPermissionStatus(status === 'granted' ? 'granted' : 'denied');
    };
    requestPermission();
  }, []);

  const startListening = useCallback(async () => {
    if (permissionStatus !== 'granted') {
      onError?.(new Error('Microphone permission not granted'));
      return;
    }

    try {
      setIsListening(true);
      setTranscript('');

      // Note: expo-speech doesn't have built-in speech-to-text
      // In production, you would use a service like:
      // - expo-speech-recognition (community package)
      // - Google Cloud Speech-to-Text
      // - AWS Transcribe
      // - Azure Speech Services

      // For this example, we'll use a placeholder
      // Real implementation would stream audio to STT service

    } catch (err) {
      setIsListening(false);
      onError?.(err as Error);
    }
  }, [permissionStatus, onError]);

  const stopListening = useCallback(() => {
    setIsListening(false);
  }, []);

  return {
    isListening,
    transcript,
    startListening,
    stopListening,
    isSupported: permissionStatus === 'granted',
    permissionStatus,
  };
}
```

### Mobile Voice Button Component

```typescript
// apps/mobile/components/voice-input-button.tsx
import { TouchableOpacity, View, Text, StyleSheet, Animated } from 'react-native';
import { Mic } from 'lucide-react-native';
import { useMobileVoiceInput } from '@/hooks/use-mobile-voice-input';
import { useRef, useEffect } from 'react';

interface VoiceInputButtonProps {
  onResult: (transcript: string) => void;
  size?: 'small' | 'large';
}

export function VoiceInputButton({ onResult, size = 'large' }: VoiceInputButtonProps) {
  const { isListening, startListening, stopListening, isSupported } = useMobileVoiceInput({
    onResult,
  });

  const pulseAnim = useRef(new Animated.Value(1)).current;

  useEffect(() => {
    if (isListening) {
      Animated.loop(
        Animated.sequence([
          Animated.timing(pulseAnim, {
            toValue: 1.2,
            duration: 500,
            useNativeDriver: true,
          }),
          Animated.timing(pulseAnim, {
            toValue: 1,
            duration: 500,
            useNativeDriver: true,
          }),
        ])
      ).start();
    } else {
      pulseAnim.setValue(1);
    }
  }, [isListening, pulseAnim]);

  const buttonSize = size === 'large' ? 80 : 48;

  return (
    <View style={styles.container}>
      <Animated.View
        style={[
          styles.pulseRing,
          {
            width: buttonSize + 20,
            height: buttonSize + 20,
            borderRadius: (buttonSize + 20) / 2,
            transform: [{ scale: pulseAnim }],
            opacity: isListening ? 0.3 : 0,
          },
        ]}
      />
      <TouchableOpacity
        onPress={isListening ? stopListening : startListening}
        disabled={!isSupported}
        style={[
          styles.button,
          {
            width: buttonSize,
            height: buttonSize,
            borderRadius: buttonSize / 2,
          },
          isListening && styles.buttonActive,
          !isSupported && styles.buttonDisabled,
        ]}
      >
        <Mic
          size={size === 'large' ? 32 : 20}
          color={isListening ? '#fff' : '#0369a1'}
        />
      </TouchableOpacity>
      {size === 'large' && (
        <Text style={styles.label}>
          {isListening ? 'Listening...' : 'Tap to speak'}
        </Text>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
  },
  pulseRing: {
    position: 'absolute',
    backgroundColor: '#0369a1',
  },
  button: {
    backgroundColor: '#e0f2fe',
    justifyContent: 'center',
    alignItems: 'center',
    elevation: 4,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
  },
  buttonActive: {
    backgroundColor: '#0369a1',
  },
  buttonDisabled: {
    backgroundColor: '#e5e7eb',
    opacity: 0.5,
  },
  label: {
    marginTop: 12,
    fontSize: 16,
    color: '#6b7280',
  },
});
```

### Keyboard Shortcuts

```typescript
// lib/keyboard-shortcuts.ts
export const KEYBOARD_SHORTCUTS = {
  // Global
  OPEN_COMMAND_BAR: { key: 'k', modifiers: ['meta'] },
  CLOSE: { key: 'Escape' },

  // Navigation
  GO_HOME: { key: 'h', modifiers: ['meta', 'shift'] },
  GO_ORDERS: { key: 'o', modifiers: ['meta', 'shift'] },
  GO_RFQS: { key: 'r', modifiers: ['meta', 'shift'] },

  // Actions
  NEW_RFQ: { key: 'n', modifiers: ['meta'] },
  SEARCH_FOCUS: { key: '/' },

  // Command Bar
  SELECT: { key: 'Enter' },
  NAVIGATE_UP: { key: 'ArrowUp' },
  NAVIGATE_DOWN: { key: 'ArrowDown' },
  VOICE_INPUT: { key: 'Space', modifiers: ['meta'] },
};

export function useKeyboardShortcuts(
  shortcuts: Record<string, () => void>
) {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      for (const [shortcutId, handler] of Object.entries(shortcuts)) {
        const shortcut = KEYBOARD_SHORTCUTS[shortcutId as keyof typeof KEYBOARD_SHORTCUTS];
        if (!shortcut) continue;

        const modifiersMatch =
          (!shortcut.modifiers?.includes('meta') || e.metaKey || e.ctrlKey) &&
          (!shortcut.modifiers?.includes('shift') || e.shiftKey) &&
          (!shortcut.modifiers?.includes('alt') || e.altKey);

        if (e.key === shortcut.key && modifiersMatch) {
          e.preventDefault();
          handler();
          break;
        }
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [shortcuts]);
}
```

### NLU Integration Points

```typescript
// lib/api/nlu.ts

// Server-side NLU processing for complex queries
export async function processNaturalLanguage(
  input: string,
  context?: ConversationContext
): Promise<NLUResult> {
  return apiClient.post('/api/v1/nlu/process', {
    input,
    context,
    capabilities: ['search', 'navigation', 'rfq', 'quote', 'order'],
  });
}

interface NLUResult {
  intent: {
    name: string;
    confidence: number;
  };
  entities: Entity[];
  action?: {
    type: string;
    params: Record<string, any>;
  };
  response?: {
    type: 'direct' | 'conversation';
    content: string;
  };
}

interface Entity {
  type: 'vessel' | 'port' | 'product' | 'impa_code' | 'date' | 'quantity';
  value: string;
  confidence: number;
  span: [number, number];
}
```

---

## Dependencies

- ADR-UI-001: Next.js 14+ App Router
- ADR-UI-002: Component Library (shadcn/ui)
- ADR-UI-006: React Native with Expo (mobile voice)
- ADR-UI-009: Design System & Theming (Command Bar styling)
- ADR-NF-003: Meilisearch Search Engine (product search backend)

---

## Migration Strategy

### From ADR-UI-011 (Traditional Search)

1. **Phase 1: Add Command Bar**
   - Deploy Command Bar alongside existing search
   - Add "Try Command Bar" tooltip on search boxes
   - Maintain existing search functionality

2. **Phase 2: Voice Integration**
   - Enable voice input on web (where supported)
   - Deploy mobile voice-first interface
   - Train users with in-app guidance

3. **Phase 3: Default Experience**
   - Make Command Bar the default search interface
   - Replace search boxes with Command Bar triggers
   - Keep traditional search in settings for power users

### Feature Mapping

| Search UX Feature | Command Bar Equivalent |
|-------------------|------------------------|
| Global search box | Command Bar (⌘K) |
| Product autocomplete | AI-enhanced suggestions |
| Faceted filters | Natural language: "Find rope in deck supplies" |
| IMPA code lookup | Direct code entry: "170101" |
| Search history | Conversation context |

---

## Performance Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| Command Bar open | < 50ms | Keyboard shortcut to visible |
| Search suggestions | < 150ms | Keystroke to suggestions |
| Voice recognition start | < 500ms | Button tap to listening |
| Intent classification | < 100ms | Client-side patterns |
| NLU processing | < 500ms | Server-side complex queries |

---

## Success Metrics

| Metric | Target | Tracking |
|--------|--------|----------|
| Voice input adoption | > 30% | Input method tracking |
| Command Bar usage | > 60% | vs. traditional navigation |
| Intent classification accuracy | > 90% | User corrections tracking |
| Time to action | -40% | vs. traditional navigation |
| Search satisfaction | > 4.5/5 | Post-search surveys |

---

## References

- [Web Speech API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Speech_API)
- [cmdk (Command Menu)](https://cmdk.paco.me/)
- [Voice UI Best Practices](https://developers.google.com/assistant/design)
- [NLU Design Patterns](https://www.nngroup.com/articles/voice-first/)
