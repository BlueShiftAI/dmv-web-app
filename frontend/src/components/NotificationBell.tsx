import { useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import { useAuthStore } from "../features/auth/authStore";

interface NotificationItem {
  id: string;
  title: string;
  body: string;
  notification_type: string;
  entity_id: string | null;
  is_read: boolean;
  created_at: string;
}

const POLL_MS = 10_000;

// ── browser notification helper ─────────────────────────────────────────────

let notifPermission: NotificationPermission = "default";

async function requestBrowserPermission() {
  if (!("Notification" in window)) return;
  notifPermission = await Notification.requestPermission();
}

function fireBrowserNotif(title: string, body: string) {
  if (!("Notification" in window)) return;
  if (Notification.permission !== "granted") return;
  new Notification(title, {
    body,
    icon: "/vite.svg",
    tag: "dmv-turn-alert",
  });
}

// ── component ────────────────────────────────────────────────────────────────

export default function NotificationBell() {
  const token = useAuthStore((s) => s.token);
  const [notifs, setNotifs] = useState<NotificationItem[]>([]);
  const [open, setOpen] = useState(false);
  const [permAsked, setPermAsked] = useState(false);
  const prevIds = useRef<Set<string>>(new Set());
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const dropRef = useRef<HTMLDivElement>(null);

  // Don't render if not logged in
  if (!token) return null;

  const unread = notifs.filter((n) => !n.is_read).length;

  // ── request browser notification permission ──────────────────────────────
  const askPermission = async () => {
    await requestBrowserPermission();
    setPermAsked(true);
  };

  // ── close dropdown on outside click ─────────────────────────────────────
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (dropRef.current && !dropRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  // ── poll for notifications ───────────────────────────────────────────────
  useEffect(() => {
    if (!token) return;
    fetchNotifs();
    pollRef.current = setInterval(fetchNotifs, POLL_MS);
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [token]);

  const fetchNotifs = async () => {
    try {
      const r = await api.get<NotificationItem[]>("/api/notifications");
      const data = r.data;
      setNotifs(data);

      // Fire browser notification for newly-arrived "called" notifications
      for (const n of data) {
        if (!prevIds.current.has(n.id) && !n.is_read && n.notification_type === "called") {
          fireBrowserNotif(n.title, n.body);
        }
      }
      prevIds.current = new Set(data.map((n) => n.id));
    } catch {
      // silently fail — bell should not break the app
    }
  };

  // ── mark read ────────────────────────────────────────────────────────────
  const markRead = async (id: string) => {
    await api.post(`/api/notifications/${id}/read`).catch(() => {});
    setNotifs((prev) => prev.map((n) => n.id === id ? { ...n, is_read: true } : n));
  };

  const markAllRead = async () => {
    await api.post("/api/notifications/read_all").catch(() => {});
    setNotifs((prev) => prev.map((n) => ({ ...n, is_read: true })));
  };

  // ── render ───────────────────────────────────────────────────────────────
  return (
    <div className="relative" ref={dropRef}>
      {/* bell button */}
      <button
        onClick={() => setOpen((v) => !v)}
        className="relative p-1 rounded hover:bg-white/10 focus:outline-none focus:ring-2 focus:ring-white/40"
        aria-label={`Notifications${unread > 0 ? `, ${unread} unread` : ""}`}
        aria-haspopup="true"
        aria-expanded={open}
      >
        <span role="img" aria-hidden>🔔</span>
        {unread > 0 && (
          <span
            className="absolute -top-0.5 -right-0.5 h-4 w-4 rounded-full bg-red-500 text-white text-[10px] font-bold flex items-center justify-center"
            aria-live="polite"
          >
            {unread > 9 ? "9+" : unread}
          </span>
        )}
      </button>

      {/* dropdown */}
      {open && (
        <div
          className="absolute right-0 mt-2 w-80 bg-white rounded-lg shadow-xl border border-gray-200 z-50"
          role="dialog"
          aria-label="Notifications panel"
        >
          <div className="flex items-center justify-between px-3 py-2 border-b border-gray-100">
            <h3 className="text-sm font-semibold text-gray-800">Notifications</h3>
            <div className="flex items-center gap-2">
              {unread > 0 && (
                <button
                  onClick={markAllRead}
                  className="text-xs text-brand-600 hover:underline"
                >
                  Mark all read
                </button>
              )}
              {!permAsked && "Notification" in window && Notification.permission === "default" && (
                <button
                  onClick={askPermission}
                  className="text-xs text-gray-500 hover:underline"
                  title="Enable browser turn alerts"
                >
                  🔕 Enable alerts
                </button>
              )}
            </div>
          </div>

          {notifs.length === 0 ? (
            <p className="text-xs text-gray-400 text-center py-6">No notifications yet.</p>
          ) : (
            <ul className="max-h-72 overflow-y-auto divide-y divide-gray-50" role="list">
              {notifs.map((n) => (
                <li
                  key={n.id}
                  className={
                    "px-3 py-2.5 cursor-pointer hover:bg-gray-50 " +
                    (n.is_read ? "opacity-60" : "")
                  }
                  onClick={() => { if (!n.is_read) markRead(n.id); }}
                  role="listitem"
                >
                  <div className="flex items-start gap-2">
                    <span className="text-base leading-none mt-0.5" aria-hidden>
                      {n.notification_type === "called" ? "📢" : "ℹ️"}
                    </span>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-semibold text-gray-800 leading-snug">
                        {n.title}
                        {!n.is_read && (
                          <span className="ml-1 inline-block w-1.5 h-1.5 rounded-full bg-red-500 align-middle" />
                        )}
                      </p>
                      <p className="text-xs text-gray-500 mt-0.5 leading-snug">{n.body}</p>
                      <p className="text-[10px] text-gray-400 mt-0.5">
                        {new Date(n.created_at).toLocaleTimeString("en-US", {
                          hour: "numeric",
                          minute: "2-digit",
                        })}
                      </p>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}

          <div className="px-3 py-2 border-t border-gray-100">
            <p className="text-[10px] text-gray-400 italic">
              In-app alerts only. Alerts work only while this page is open unless browser push is configured.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
