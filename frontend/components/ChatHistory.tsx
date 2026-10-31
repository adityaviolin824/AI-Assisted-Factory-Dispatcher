import { useEffect, useState } from "react";
import ChatTimeline from "@/components/ChatTimeline";
import { errorText, listMessages } from "@/lib/api";
import { count } from "@/lib/format";
import type { ChatMessage } from "@/lib/types";

// The whole shared conversation for the dispatcher, read once each time the panel opens. It is
// read-only: messages are sent from the Chat page.
export default function ChatHistory() {
  const [messages, setMessages] = useState<ChatMessage[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listMessages().then(setMessages, (caught) => setError(`Could not read the chat: ${errorText(caught)}`));
  }, []);

  return (
    <section className="chat-history" aria-label="Chat history">
      <div className="chat-history-head">
        <h2>Chat history</h2>
        {messages && <span className="muted">{count(messages.length, "message")}</span>}
        <p className="hint">
          Every message since the last Clear chat. A saved run&apos;s source messages stay in its task details.
        </p>
      </div>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {!messages && !error && <p className="timeline-empty muted">Loading messages...</p>}
      {messages && <ChatTimeline messages={messages} emptyText="The chat has no messages." />}
    </section>
  );
}
