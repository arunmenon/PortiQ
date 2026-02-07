"use client";

import { useState, useRef, useEffect } from "react";
import { Send, Mic } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

interface ChatInputProps {
  onSubmit: (message: string) => void;
  disabled?: boolean;
  initialValue?: string;
  className?: string;
}

export function ChatInput({ onSubmit, disabled = false, initialValue = "", className }: ChatInputProps) {
  const [value, setValue] = useState(initialValue);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (initialValue) {
      setValue(initialValue);
    }
  }, [initialValue]);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  function handleSubmit() {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSubmit(trimmed);
    setValue("");
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  }

  return (
    <div className={cn("border-t bg-card px-4 py-3", className)}>
      <div className="mx-auto flex max-w-3xl items-end gap-2">
        <Button
          variant="ghost"
          size="icon"
          className="shrink-0 text-muted-foreground"
          disabled
          title="Voice input coming soon"
        >
          <Mic className="h-5 w-5" />
        </Button>

        <div className="relative flex-1">
          <textarea
            ref={inputRef}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type your response or ask a follow-up question..."
            disabled={disabled}
            rows={1}
            className="w-full resize-none rounded-lg border bg-background px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50"
            style={{ minHeight: "40px", maxHeight: "120px" }}
          />
        </div>

        <Button
          size="icon"
          onClick={handleSubmit}
          disabled={disabled || !value.trim()}
          className="shrink-0"
        >
          <Send className="h-4 w-4" />
        </Button>

        <kbd className="hidden sm:inline-flex pointer-events-none h-5 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium text-muted-foreground shrink-0">
          Cmd+K
        </kbd>
      </div>
    </div>
  );
}
