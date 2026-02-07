"use client";

import { useMutation } from "@tanstack/react-query";
import { useConversationStore } from "@/stores/conversation-store";
import { sendPortiQMessage, executePortiQAction, type PortiQResponse, type ActionResult } from "@/lib/api/portiq";
import type { AIAction } from "@/stores/conversation-store";

export function usePortiQChat() {
  const { addMessage, setProcessing, updateContext, sessionId, context } = useConversationStore();

  const chatMutation = useMutation<PortiQResponse, Error, string>({
    mutationFn: (message: string) =>
      sendPortiQMessage(
        message,
        context.type ? { type: context.type, data: context.data ?? {} } : undefined,
        sessionId
      ),
    onMutate: (message) => {
      addMessage({ role: "user", content: message });
      setProcessing(true);
    },
    onSuccess: (response) => {
      addMessage({
        role: "assistant",
        content: response.message,
        cards: response.cards,
        actions: response.actions,
      });
      if (response.context) {
        updateContext(response.context.type, response.context.data);
      }
    },
    onError: (error: unknown) => {
      const apiError = error as { error?: { message?: string } };
      const message = apiError?.error?.message || (error instanceof Error ? error.message : "Service unavailable");
      addMessage({
        role: "assistant",
        content: `I'm unable to connect to the PortiQ AI service right now. Please try again later.\n\nError: ${message}`,
      });
    },
    onSettled: () => {
      setProcessing(false);
    },
  });

  return {
    sendMessage: chatMutation.mutate,
    isLoading: chatMutation.isPending,
  };
}

export function usePortiQAction() {
  const { addMessage, setProcessing } = useConversationStore();

  const actionMutation = useMutation<ActionResult, Error, AIAction>({
    mutationFn: executePortiQAction,
    onMutate: (action) => {
      addMessage({ role: "system", content: `Executing: ${action.label}...` });
      setProcessing(true);
    },
    onSuccess: (result) => {
      addMessage({
        role: "assistant",
        content: result.message,
      });
    },
    onError: (error) => {
      addMessage({
        role: "assistant",
        content: `Action failed: ${error.message}`,
      });
    },
    onSettled: () => {
      setProcessing(false);
    },
  });

  return {
    executeAction: actionMutation.mutate,
    isExecuting: actionMutation.isPending,
  };
}
