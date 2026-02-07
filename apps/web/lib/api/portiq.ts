import { apiClient } from "./client";
import type { AICard, AIAction, ContextPanelType } from "@/stores/conversation-store";

export interface PortiQResponse {
  message: string;
  cards?: AICard[];
  actions?: AIAction[];
  context?: { type: ContextPanelType; data: Record<string, unknown> };
  confidence?: number;
}

export interface ActionResult {
  success: boolean;
  message: string;
  data?: Record<string, unknown>;
}

export async function sendPortiQMessage(
  message: string,
  context?: { type: string; data: Record<string, unknown> },
  sessionId?: string
): Promise<PortiQResponse> {
  return apiClient.post<PortiQResponse>("/api/v1/portiq/chat", {
    message,
    context,
    sessionId,
  });
}

export async function executePortiQAction(action: AIAction): Promise<ActionResult> {
  return apiClient.post<ActionResult>("/api/v1/portiq/action", {
    actionId: action.id,
    action: action.action,
    params: action.params,
  });
}
