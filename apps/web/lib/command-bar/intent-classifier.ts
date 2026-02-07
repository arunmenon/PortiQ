export type IntentType = "search" | "navigation" | "action" | "conversation";

export function classifyIntent(input: string): IntentType {
  const trimmed = input.trim().toLowerCase();

  // navigation — starts with `/` or `go to` or `open`
  if (trimmed.startsWith("/") || trimmed.startsWith("go to") || trimmed.startsWith("open")) {
    return "navigation";
  }

  // action — starts with create, add, new, export, import
  if (/^(create|add|new|export|import)\b/.test(trimmed)) {
    return "action";
  }

  // conversation — questions (contains ?, who, what, why, how, when, where, which, can, should, is there, do we)
  // or long text (>= 60 chars)
  if (trimmed.length >= 60 || /\?|^(who|what|why|how|when|where|which|can|should|is there|do we|tell me)\b/.test(trimmed)) {
    return "conversation";
  }

  // search — default for short queries
  return "search";
}
