"use client";

import { useEffect, useRef, useState } from "react";
import ChatTimeline from "@/components/ChatTimeline";
import Composer from "@/components/Composer";
import { clearChat, errorText, listMessages, readChatDates } from "@/lib/api";
import { calendarDate, chatTime, count } from "@/lib/format";
import { useIdentity } from "@/lib/identity";
import type { ChatDates, ChatMessage } from "@/lib/types";

// The shared chat where team members send requests. The dispatcher reads it on the Dispatcher page
// and starts dispatch there. app/operations/layout.tsx shows it only to signed-in team members.
export default function ChatPage() {
  const identity = useIdentity();
  const [messages, setMessages] = useState<ChatMessage[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dates, setDates] = useState<ChatDates | null>(null);
  // Clear chat is a demonstration convenience: it asks "Are you sure?" on the page before deleting.
  const [confirmingClear, setConfirmingClear] = useState(false);
  const [clearing, setClearing] = useState(false);
  // Kept apart from error, which the next successful read of the conversation removes.
  const [clearError, setClearError] = useState<string | null>(null);
  // Counts this page's own finished changes: Sends and Clear chat. A read of the conversation that was
  // already on its way when one finished is out of date, so its answer is ignored.
  const ownChanges = useRef(0);

  // The configured dates are read once. If the backend cannot be reached, the note is left out and the
  // conversation's own error says why.
  useEffect(() => {
    readChatDates().then(setDates, () => setDates(null));
  }, []);

  // Everyone shares one conversation, so it is read now and every three seconds. The page shows exactly
  // what the backend returned, so a Clear chat on another device empties this page too.
  useEffect(() => {
    function load() {
      const changesBefore = ownChanges.current;
      listMessages()
        .then((loaded) => {
          if (ownChanges.current === changesBefore) {
            setMessages(loaded);
          }
          setError(null);
        })
        .catch((caught) => setError(`Could not read the conversation: ${errorText(caught)}`));
    }
    load();
    const timer = setInterval(load, 3000);
    return () => clearInterval(timer);
  }, []);

  function addSent(message: ChatMessage) {
    ownChanges.current += 1;
    setMessages((shown) => {
      const list = shown ?? [];
      return list.some((item) => item.message_id === message.message_id) ? list : [...list, message];
    });
  }

  // Deletes every message for everyone, after "Yes, delete". Other open pages empty at their next read.
  async function clear() {
    setClearing(true);
    setClearError(null);
    try {
      await clearChat();
      ownChanges.current += 1;
      setMessages([]);
    } catch (caught) {
      setClearError(`Could not clear the chat: ${errorText(caught)}`);
    } finally {
      setClearing(false);
      setConfirmingClear(false);
    }
  }

  const last = messages?.at(-1);

  return (
    <>
      <div className="page-head">
        <h1>Chat</h1>
        <div className="toolbar">
          {messages && (
            <p className="muted">
              {count(messages.length, "message")}
              {last && `, the last at ${chatTime(last.received_at_utc)}`}
            </p>
          )}
          <button onClick={() => setConfirmingClear(true)} disabled={confirmingClear || !messages?.length}>
            Clear chat
          </button>
        </div>
      </div>
      {confirmingClear && (
        <div className="confirm-clear" role="group" aria-label="Confirm Clear chat">
          <p>
            Are you sure you want to delete all the chat messages up till now ({count(messages?.length ?? 0, "message")})?
            They are deleted for everyone and cannot be recovered. Saved snapshots and dispatch plans stay.
          </p>
          <div className="toolbar">
            <button className="danger" onClick={clear} disabled={clearing}>
              {clearing ? "Deleting..." : "Yes, delete"}
            </button>
            <button onClick={() => setConfirmingClear(false)} disabled={clearing}>
              Cancel
            </button>
          </div>
        </div>
      )}
      {dates && (
        <p className="muted lede">
          Words such as &quot;by Friday&quot; count from {calendarDate(dates.message_date)}, when the supplied chat was
          written, not from today. Plans start from {calendarDate(dates.dispatch_date)}.
        </p>
      )}
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {clearError && (
        <p className="error" role="alert">
          {clearError}
        </p>
      )}
      <section className="conversation" aria-label="Conversation">
        {messages && <ChatTimeline messages={messages} />}
        {!messages && <p className="timeline-empty muted">{error ? "No messages to show." : "Loading messages..."}</p>}
        <Composer sender={identity?.name ?? ""} onSent={addSent} />
      </section>
    </>
  );
}
