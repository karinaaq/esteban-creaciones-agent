export type ChatHistoryMessage = {
  role: string;
  content: string;
  intent: string | null;
  agent: string | null;
  created_at: string | null;
};

export type ChatSource = {
  chunk_id: string;
  source_id: string;
  title: string;
  score: number;
};

export type ChatResponse = {
  reply: string;
  intent: string;
  agent: string;
  session_id: string;
  history: ChatHistoryMessage[];
  sources: ChatSource[];
  metadata: Record<string, unknown>;
};

const API_BASE = (import.meta.env.VITE_API_BASE ?? "").replace(/\/$/, "");

export async function sendChat(
  message: string,
  sessionId: string,
): Promise<ChatResponse> {
  const res = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message,
      session_id: sessionId || "",
    }),
  });

  if (!res.ok) {
    let detail = `Error ${res.status}`;
    try {
      const data = (await res.json()) as { detail?: unknown };
      if (typeof data.detail === "string") detail = data.detail;
      else if (data.detail != null) detail = JSON.stringify(data.detail);
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }

  return (await res.json()) as ChatResponse;
}
