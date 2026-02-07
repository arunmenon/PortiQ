import { create } from "zustand";
import { persist } from "zustand/middleware";

export type MessageRole = "user" | "assistant" | "system";

export type CardType = "suggestion" | "rfq_summary" | "quote_comparison" | "vessel_info" | "product_list";

export interface AICard {
  type: CardType;
  title: string;
  data: Record<string, unknown>;
}

export interface AIAction {
  id: string;
  label: string;
  variant: "primary" | "outline";
  action: string;
  params: Record<string, unknown>;
}

export interface Message {
  id: string;
  role: MessageRole;
  content: string;
  cards?: AICard[];
  actions?: AIAction[];
  timestamp: number;
}

export type ContextPanelType = "vessel" | "rfq" | "comparison" | "order";

interface ConversationState {
  messages: Message[];
  context: { type: ContextPanelType | null; data: Record<string, unknown> | null };
  isProcessing: boolean;
  sessionId: string;
  addMessage: (message: Omit<Message, "id" | "timestamp">) => void;
  updateContext: (type: ContextPanelType, data: Record<string, unknown>) => void;
  clearContext: () => void;
  setProcessing: (processing: boolean) => void;
  clearConversation: () => void;
}

export const useConversationStore = create<ConversationState>()(
  persist(
    (set) => ({
      messages: [],
      context: { type: null, data: null },
      isProcessing: false,
      sessionId: crypto.randomUUID(),
      addMessage: (message) =>
        set((state) => ({
          messages: [
            ...state.messages,
            {
              ...message,
              id: crypto.randomUUID(),
              timestamp: Date.now(),
            },
          ].slice(-50),
        })),
      updateContext: (type, data) =>
        set({ context: { type, data } }),
      clearContext: () =>
        set({ context: { type: null, data: null } }),
      setProcessing: (processing) =>
        set({ isProcessing: processing }),
      clearConversation: () =>
        set({
          messages: [],
          context: { type: null, data: null },
          isProcessing: false,
          sessionId: crypto.randomUUID(),
        }),
    }),
    {
      name: "portiq-conversations",
      partialize: (state) => ({
        messages: state.messages,
        sessionId: state.sessionId,
      }),
    }
  )
);
