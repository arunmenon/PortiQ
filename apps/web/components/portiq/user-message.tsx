"use client";

import { cn } from "@/lib/utils";
import type { Message } from "@/stores/conversation-store";

interface UserMessageProps {
  message: Message;
  className?: string;
}

export function UserMessage({ message, className }: UserMessageProps) {
  return (
    <div className={cn("flex items-start gap-3 justify-end", className)}>
      <div className="rounded-lg bg-primary px-4 py-2.5 text-primary-foreground max-w-[80%]">
        <p className="text-sm whitespace-pre-wrap">{message.content}</p>
      </div>
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-secondary">
        <span className="text-sm font-medium">U</span>
      </div>
    </div>
  );
}
