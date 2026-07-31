import { useCallback, useEffect, useState } from "react";
import { listMessages, markMessageDelivered } from "../api";
import { timeAgo } from "../format";

export default function MessagesView({ onChanged }) {
  const [messages, setMessages] = useState([]);
  const [showDelivered, setShowDelivered] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const refresh = useCallback(() => {
    setLoading(true);
    listMessages(showDelivered ? undefined : false)
      .then((data) => {
        setMessages(data);
        setError(null);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [showDelivered]);

  useEffect(refresh, [refresh]);

  async function toggleDelivered(msg) {
    try {
      await markMessageDelivered(msg.id, !msg.delivered);
      refresh();
      onChanged?.();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="panel-view">
      <header className="panel-header">
        <h2>Messages</h2>
        <p className="panel-note">
          Taken when a caller asked for someone who didn't pick up.
        </p>
        <label className="toggle">
          <input
            type="checkbox"
            checked={showDelivered}
            onChange={(e) => setShowDelivered(e.target.checked)}
          />
          Include delivered
        </label>
      </header>

      {error && <div className="error-banner">{error}</div>}

      {loading && messages.length === 0 ? (
        <div className="empty-state">Loading…</div>
      ) : messages.length === 0 ? (
        <div className="empty-state">
          {showDelivered ? "No messages yet." : "No messages waiting."}
        </div>
      ) : (
        <ul className="message-list">
          {messages.map((m) => (
            <li key={m.id} className={`message-card${m.delivered ? " delivered" : ""}`}>
              <div className="message-top">
                <div>
                  <span className="caller-name">{m.caller_name || "Unknown caller"}</span>
                  {m.callback_phone && (
                    <span className="caller-phone"> · {m.callback_phone}</span>
                  )}
                </div>
                <span className="nowrap">{timeAgo(m.created_at)}</span>
              </div>

              <p className="message-text">{m.message_text}</p>

              <div className="message-meta">
                {m.for_staff_name && <span>For: <strong>{m.for_staff_name}</strong></span>}
                {m.case_number && <span>Case #{m.case_number}</span>}
                <button className="link-button" onClick={() => toggleDelivered(m)}>
                  {m.delivered ? "Mark undelivered" : "Mark delivered"}
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
