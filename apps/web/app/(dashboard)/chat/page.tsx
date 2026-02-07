"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Sparkles, Trash2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import { useConversationStore } from "@/stores/conversation-store";
import { usePortiQChat, usePortiQAction } from "@/hooks/use-portiq-chat";
import { AIMessage } from "@/components/portiq/ai-message";
import { UserMessage } from "@/components/portiq/user-message";
import { ChatInput } from "@/components/portiq/chat-input";
import { ContextPanel } from "@/components/portiq/context-panel";
import { ThinkingIndicator } from "@/components/portiq/thinking-indicator";

export default function ChatPage() {
  return (
    <Suspense fallback={null}>
      <ChatPageContent />
    </Suspense>
  );
}

function ChatPageContent() {
  const searchParams = useSearchParams();
  const initialQuery = searchParams.get("q");
  const initialQuerySent = useRef(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [contextOpen, setContextOpen] = useState(false);

  const { messages, isProcessing, context, clearConversation } = useConversationStore();
  const { sendMessage } = usePortiQChat();
  const { executeAction } = usePortiQAction();

  // Auto-send initial query from command bar (delay for Zustand hydration)
  useEffect(() => {
    if (initialQuery && !initialQuerySent.current) {
      initialQuerySent.current = true;
      const timer = setTimeout(() => {
        sendMessage(initialQuery);
      }, 500);
      return () => clearTimeout(timer);
    }
  }, [initialQuery, sendMessage]);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isProcessing]);

  const hasContext = context.type !== null;

  return (
    <div className="flex h-full flex-col -m-6">
      {/* Header */}
      <div className="flex items-center justify-between border-b px-4 py-2">
        <div className="flex items-center gap-2">
          <Sparkles className="h-5 w-5 text-primary" />
          <h1 className="font-semibold">PortiQ Assistant</h1>
        </div>
        <div className="flex items-center gap-2">
          {/* Mobile context toggle */}
          {hasContext && (
            <Sheet open={contextOpen} onOpenChange={setContextOpen}>
              <SheetTrigger asChild>
                <Button variant="outline" size="sm" className="lg:hidden">
                  Context
                </Button>
              </SheetTrigger>
              <SheetContent side="right" className="w-80 p-0">
                <ContextPanel onClose={() => setContextOpen(false)} />
              </SheetContent>
            </Sheet>
          )}
          <Button
            variant="ghost"
            size="icon"
            onClick={clearConversation}
            title="Clear conversation"
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Main content */}
      <div className="flex flex-1 overflow-hidden">
        {/* Conversation panel */}
        <div className="flex flex-1 flex-col">
          <ScrollArea className="flex-1 px-4">
            <div className="mx-auto max-w-3xl space-y-6 py-6">
              {messages.length === 0 && !isProcessing && (
                <div className="flex flex-col items-center justify-center py-20 text-center">
                  <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary/10 mb-4">
                    <Sparkles className="h-8 w-8 text-primary" />
                  </div>
                  <h2 className="text-xl font-semibold mb-2">How can I help?</h2>
                  <p className="text-sm text-muted-foreground max-w-md">
                    Ask about products, create RFQs, compare quotes, or get procurement insights for your fleet.
                  </p>
                  <div className="mt-6 flex flex-wrap justify-center gap-2">
                    {[
                      "What safety equipment do I need for a bulk carrier?",
                      "Compare prices for marine paint",
                      "Create an RFQ for engine spares",
                    ].map((suggestion) => (
                      <Button
                        key={suggestion}
                        variant="outline"
                        size="sm"
                        onClick={() => sendMessage(suggestion)}
                      >
                        {suggestion}
                      </Button>
                    ))}
                  </div>
                </div>
              )}

              {messages.map((message) =>
                message.role === "user" ? (
                  <UserMessage key={message.id} message={message} />
                ) : (
                  <AIMessage
                    key={message.id}
                    message={message}
                    onAction={executeAction}
                  />
                )
              )}

              {isProcessing && <ThinkingIndicator variant="dots" />}

              <div ref={messagesEndRef} />
            </div>
          </ScrollArea>

          <ChatInput onSubmit={sendMessage} disabled={isProcessing} />
        </div>

        {/* Context panel - desktop */}
        <ContextPanel className="hidden lg:block w-80" />
      </div>
    </div>
  );
}
