import { useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import { useAuthStore } from "../features/auth/authStore";

// ── types ────────────────────────────────────────────────────────────────────

interface Message {
  id: string;
  role: "user" | "assistant";
  text: string;
  simulated?: boolean;
}

interface ChatResponse {
  reply: string;
  session_id: string;
  orchestrate_enabled: boolean;
  simulated: boolean;
  disclaimer: string;
}

// ── simple markdown-like renderer (bold, bullet lists, italics) ──────────────

function renderMarkdown(text: string): React.ReactNode[] {
  const lines = text.split("\n");
  const elements: React.ReactNode[] = [];
  let key = 0;

  for (const line of lines) {
    if (line.trim() === "") {
      elements.push(<br key={key++} />);
      continue;
    }

    // Bullet list item
    if (line.trimStart().startsWith("•") || line.trimStart().startsWith("-")) {
      const content = line.replace(/^[\s•\-]+/, "");
      elements.push(
        <div key={key++} className="flex gap-1.5 items-start">
          <span className="mt-0.5 text-brand-400 flex-shrink-0">•</span>
          <span>{renderInline(content)}</span>
        </div>
      );
      continue;
    }

    // Numbered list
    const numMatch = line.match(/^(\d+)\.\s+(.*)/);
    if (numMatch) {
      elements.push(
        <div key={key++} className="flex gap-1.5 items-start">
          <span className="mt-0.5 text-brand-400 flex-shrink-0 font-mono text-xs">{numMatch[1]}.</span>
          <span>{renderInline(numMatch[2])}</span>
        </div>
      );
      continue;
    }

    elements.push(<p key={key++}>{renderInline(line)}</p>);
  }
  return elements;
}

function renderInline(text: string): React.ReactNode {
  // **bold** and _italic_ and `code`
  const parts = text.split(/(\*\*[^*]+\*\*|_[^_]+_|`[^`]+`)/);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={i}>{part.slice(2, -2)}</strong>;
    }
    if (part.startsWith("_") && part.endsWith("_")) {
      return <em key={i} className="text-gray-500">{part.slice(1, -1)}</em>;
    }
    if (part.startsWith("`") && part.endsWith("`")) {
      return <code key={i} className="font-mono text-xs bg-gray-100 px-0.5 rounded">{part.slice(1, -1)}</code>;
    }
    return part;
  });
}

// ── component ─────────────────────────────────────────────────────────────────

const WELCOME: Message = {
  id: "welcome",
  role: "assistant",
  text: (
    "Hi! I'm the **DMV Registration Assistant**. I can help you with:\n" +
    "• Required documents for private-party registration\n" +
    "• How to book or cancel a demo appointment\n" +
    "• Current simulated wait times\n" +
    "• Tax and ownership lookup results\n\n" +
    "What can I help you with today?"
  ),
  simulated: true,
};

const SUGGESTIONS = [
  "What documents do I need?",
  "How long is the wait?",
  "How do I book an appointment?",
  "What is Form 400?",
];

export default function AssistantWidget() {
  const token = useAuthStore((s) => s.token);
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([WELCOME]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [orchestrateEnabled, setOrchestrateEnabled] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Focus input when opened
  useEffect(() => {
    if (open) setTimeout(() => inputRef.current?.focus(), 50);
  }, [open]);

  // Don't render if not logged in
  if (!token) return null;

  const send = async (text: string) => {
    if (!text.trim() || loading) return;

    const userMsg: Message = {
      id: Date.now().toString(),
      role: "user",
      text: text.trim(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const r = await api.post<ChatResponse>("/api/orchestrate/chat", {
        message: text.trim(),
        session_id: sessionId,
        history: messages
          .filter((m) => m.id !== "welcome")
          .map((m) => ({ role: m.role, content: m.text })),
      });
      const data = r.data;
      setSessionId(data.session_id);
      setOrchestrateEnabled(data.orchestrate_enabled);

      const asstMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        text: data.reply,
        simulated: data.simulated,
      };
      setMessages((prev) => [...prev, asstMsg]);
    } catch (e: any) {
      const errMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        text: "_Sorry, I couldn't reach the assistant. Please try again._",
        simulated: true,
      };
      setMessages((prev) => [...prev, errMsg]);
    } finally {
      setLoading(false);
    }
  };

  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send(input);
    }
  };

  return (
    <>
      {/* floating button */}
      <button
        onClick={() => setOpen((v) => !v)}
        className={
          "fixed bottom-5 right-5 z-50 w-14 h-14 rounded-full shadow-lg flex items-center justify-center text-2xl transition-transform " +
          (open ? "bg-brand-700 scale-95" : "bg-brand-600 hover:bg-brand-700 hover:scale-105")
        }
        aria-label={open ? "Close assistant" : "Open DMV assistant"}
        aria-expanded={open}
      >
        {open ? "✕" : "💬"}
      </button>

      {/* chat panel */}
      {open && (
        <div
          className="fixed bottom-24 right-5 z-50 w-80 sm:w-96 flex flex-col rounded-2xl shadow-2xl border border-gray-200 bg-white overflow-hidden"
          style={{ maxHeight: "70vh" }}
          role="dialog"
          aria-label="DMV Registration Assistant"
        >
          {/* header */}
          <div className="bg-brand-700 text-white px-4 py-3 flex items-center justify-between">
            <div>
              <p className="font-semibold text-sm">DMV Registration Assistant</p>
              <p className="text-xs text-blue-200">
                {orchestrateEnabled ? "Powered by IBM watsonx Orchestrate" : "Demo mode"}
              </p>
            </div>
            <button
              onClick={() => setOpen(false)}
              className="text-blue-200 hover:text-white text-lg leading-none"
              aria-label="Close assistant"
            >
              ✕
            </button>
          </div>

          {/* disclaimer banner */}
          <div className="bg-yellow-50 border-b border-yellow-200 px-3 py-1.5 text-[10px] text-yellow-700">
            Educational prototype. Not affiliated with the SCDMV. All data simulated.
          </div>

          {/* messages */}
          <div className="flex-1 overflow-y-auto p-3 space-y-3 text-sm">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={
                  "flex " + (msg.role === "user" ? "justify-end" : "justify-start")
                }
              >
                <div
                  className={
                    "max-w-[85%] rounded-2xl px-3 py-2 leading-relaxed space-y-0.5 " +
                    (msg.role === "user"
                      ? "bg-brand-600 text-white rounded-br-sm"
                      : "bg-gray-100 text-gray-800 rounded-bl-sm")
                  }
                >
                  {renderMarkdown(msg.text)}
                  {msg.simulated && msg.role === "assistant" && (
                    <p className="text-[10px] text-gray-400 mt-1 italic">Demo mode</p>
                  )}
                </div>
              </div>
            ))}

            {loading && (
              <div className="flex justify-start">
                <div className="bg-gray-100 rounded-2xl rounded-bl-sm px-3 py-2">
                  <span className="flex gap-1">
                    <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                    <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                    <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                  </span>
                </div>
              </div>
            )}

            <div ref={bottomRef} />
          </div>

          {/* suggestions (only on first message) */}
          {messages.length === 1 && (
            <div className="px-3 pb-2 flex flex-wrap gap-1.5">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => send(s)}
                  className="text-xs bg-gray-100 hover:bg-brand-50 hover:text-brand-700 border border-gray-200 rounded-full px-2 py-1 transition"
                >
                  {s}
                </button>
              ))}
            </div>
          )}

          {/* input */}
          <div className="border-t border-gray-200 px-3 py-2 flex gap-2 items-center">
            <input
              ref={inputRef}
              type="text"
              className="flex-1 text-sm border border-gray-200 rounded-full px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-brand-400"
              placeholder="Ask me anything…"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKey}
              disabled={loading}
              aria-label="Chat message input"
            />
            <button
              onClick={() => send(input)}
              disabled={loading || !input.trim()}
              className="bg-brand-600 hover:bg-brand-700 disabled:opacity-40 text-white rounded-full w-8 h-8 flex items-center justify-center text-sm transition flex-shrink-0"
              aria-label="Send message"
            >
              ↑
            </button>
          </div>
        </div>
      )}
    </>
  );
}
