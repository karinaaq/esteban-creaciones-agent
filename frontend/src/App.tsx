import {
  FormEvent,
  KeyboardEvent,
  useEffect,
  useRef,
  useState,
} from "react";
import { ChatHistoryMessage, ChatResponse, sendChat } from "./api/chat";

const SESSION_KEY = "esteban.chat.session_id";

/** Poné tus archivos en frontend/public/brand/ (pueden tener fondo opaco). */
const LOGO_SRC = "/brand/logo.png";
const BANNER_SRC = "/brand/banner.jpg";

type UiMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  intent?: string | null;
  agent?: string | null;
};

function historyToUi(history: ChatHistoryMessage[]): UiMessage[] {
  return history
    .filter((m) => m.role === "user" || m.role === "assistant")
    .map((m, i) => ({
      id: `${m.created_at ?? i}-${m.role}`,
      role: m.role as "user" | "assistant",
      content: m.content,
      intent: m.intent,
      agent: m.agent,
    }));
}

export function App() {
  const [sessionId, setSessionId] = useState(
    () => localStorage.getItem(SESSION_KEY) ?? "",
  );
  const [messages, setMessages] = useState<UiMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastMeta, setLastMeta] = useState<ChatResponse | null>(null);
  const [hasLogo, setHasLogo] = useState(true);
  const [hasBanner, setHasBanner] = useState(true);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, busy]);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const text = draft.trim();
    if (!text || busy) return;

    setError(null);
    setDraft("");
    setBusy(true);
    setMessages((prev) => [
      ...prev,
      { id: `local-${Date.now()}`, role: "user", content: text },
    ]);

    try {
      const res = await sendChat(text, sessionId);
      localStorage.setItem(SESSION_KEY, res.session_id);
      setSessionId(res.session_id);
      setLastMeta(res);
      if (res.history?.length) {
        setMessages(historyToUi(res.history));
      } else {
        setMessages((prev) => [
          ...prev,
          {
            id: `asst-${Date.now()}`,
            role: "assistant",
            content: res.reply,
            intent: res.intent,
            agent: res.agent,
          },
        ]);
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : "No pude enviar el mensaje";
      setError(msg);
      setMessages((prev) => prev.slice(0, -1));
      setDraft(text);
    } finally {
      setBusy(false);
      inputRef.current?.focus();
    }
  }

  function newConversation() {
    localStorage.removeItem(SESSION_KEY);
    setSessionId("");
    setMessages([]);
    setLastMeta(null);
    setError(null);
    inputRef.current?.focus();
  }

  function onKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void onSubmit(e as unknown as FormEvent);
    }
  }

  return (
    <div className="page">
      <div className="atmosphere" aria-hidden="true" />
      <div className="grain" aria-hidden="true" />

      <header className="brand-bar">
        <div className="brand-block">
          {hasLogo ? (
            <div className="brand-logo-chip" aria-hidden={!hasLogo}>
              <img
                src={LOGO_SRC}
                alt=""
                onError={() => setHasLogo(false)}
              />
            </div>
          ) : null}
          <div className="brand-text">
            <p className="brand-mark">Esteban Creaciones</p>
            <p className="brand-line">Trabajos manuales · conversación</p>
          </div>
        </div>
        <button
          type="button"
          className="new-session-btn"
          onClick={newConversation}
          title="Empieza una sesión nueva (limpia el chat)"
        >
          Nueva conversación
        </button>
      </header>

      <main className="stage">
        {messages.length === 0 && !busy ? (
          <section className="welcome" aria-label="Bienvenida">
            {hasBanner ? (
              <div className="welcome-banner">
                <img
                  src={BANNER_SRC}
                  alt=""
                  onError={() => setHasBanner(false)}
                />
              </div>
            ) : null}
            <h1 className="welcome-title">
              Esteban <span className="accent">Creaciones</span>
            </h1>
            <p className="welcome-sub">
              Preguntá por plazos, productos o ideas. Te respondo con lo que
              tenemos en el taller.
            </p>
            <div className="suggestions">
              {[
                "¿Cuánto tarda un centro de mesa?",
                "Quiero encargar un centro de mesa",
                "¿Hacen carpetas creativas?",
              ].map((s) => (
                <button
                  key={s}
                  type="button"
                  className="suggestion"
                  onClick={() => {
                    setDraft(s);
                    inputRef.current?.focus();
                  }}
                >
                  {s}
                </button>
              ))}
            </div>
          </section>
        ) : (
          <section className="thread" aria-live="polite">
            {messages.map((m) => (
              <article
                key={m.id}
                className={`bubble ${m.role === "user" ? "bubble-user" : "bubble-bot"}`}
              >
                <p className="bubble-role">
                  {m.role === "user" ? "Vos" : "Esteban Creaciones"}
                  {m.intent ? <span className="intent">{m.intent}</span> : null}
                </p>
                <p className="bubble-text">{m.content}</p>
              </article>
            ))}
            {busy ? (
              <article className="bubble bubble-bot bubble-pending">
                <p className="bubble-role">Esteban Creaciones</p>
                <p className="bubble-text thinking">
                  <span />
                  <span />
                  <span />
                </p>
              </article>
            ) : null}
            <div ref={bottomRef} />
          </section>
        )}

        <form className="composer" onSubmit={onSubmit}>
          {error ? <p className="error">{error}</p> : null}
          <label className="sr-only" htmlFor="chat-input">
            Mensaje
          </label>
          <textarea
            id="chat-input"
            ref={inputRef}
            rows={2}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder="Escribí tu mensaje…"
            disabled={busy}
            maxLength={4000}
          />
          <div className="composer-row">
            <p className="session-hint">
              {sessionId
                ? `Sesión ${sessionId.slice(0, 8)}…`
                : "Sesión nueva al enviar"}
              {lastMeta?.sources?.length
                ? ` · ${lastMeta.sources.length} fuente${lastMeta.sources.length === 1 ? "" : "s"}`
                : ""}
            </p>
            <button type="submit" className="send-btn" disabled={busy || !draft.trim()}>
              Enviar
            </button>
          </div>
        </form>
      </main>
    </div>
  );
}
