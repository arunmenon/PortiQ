"use client";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { ActionCard } from "./action-card";
import type { Message, AIAction } from "@/stores/conversation-store";

interface AIMessageProps {
  message: Message;
  onAction?: (action: AIAction) => void;
  className?: string;
}

export function AIMessage({ message, onAction, className }: AIMessageProps) {
  return (
    <div className={cn("flex items-start gap-3", className)}>
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10">
        <span className="text-sm font-medium text-primary">AI</span>
      </div>
      <div className="max-w-[80%] space-y-2">
        <div className="rounded-lg border bg-card px-4 py-2.5">
          <p className="text-sm whitespace-pre-wrap">{message.content}</p>
        </div>

        {message.cards?.map((card, i) => (
          <ActionCard key={i} card={card} />
        ))}

        {message.actions && message.actions.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {message.actions.map((action) => (
              <Button
                key={action.id}
                variant={action.variant === "primary" ? "default" : "outline"}
                size="sm"
                onClick={() => onAction?.(action)}
              >
                {action.label}
              </Button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
