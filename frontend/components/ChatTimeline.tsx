import { chatDateTime, chatTime } from "@/lib/format";
import type { ChatMessage } from "@/lib/types";

// emptyText replaces the Chat page's wording where there is no composer below, as on the Dispatcher page.
type Props = { messages: ChatMessage[]; emptyText?: string };

// The shared conversation in the order the backend saved it, with each message's original text.
// The newest message stays in view: .timeline scrolls from the bottom (globals.css).
export default function ChatTimeline({ messages, emptyText = "No messages yet. Write the first request below." }: Props) {
  if (messages.length === 0) {
    return <p className="timeline-empty muted">{emptyText}</p>;
  }
  return (
    <div className="timeline">
      <ol aria-label="Messages">
        {messages.map((message) => (
          <li key={message.message_id} id={`message-${message.message_id}`}>
            <p className="message-meta">
              <time dateTime={message.received_at_utc} title={chatDateTime(message.received_at_utc)}>
                {chatTime(message.received_at_utc)}
              </time>
              <strong>{message.sender}</strong>
              <span className="muted">#{message.message_id}</span>
            </p>
            <p className="spoken message-text">{message.raw_text}</p>
          </li>
        ))}
      </ol>
    </div>
  );
}
