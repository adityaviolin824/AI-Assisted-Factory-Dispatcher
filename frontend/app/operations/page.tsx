"use client";

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import ChatTimeline from "@/components/ChatTimeline";
import ProcessPanel from "@/components/ProcessPanel";
import { errorText, listMessages } from "@/lib/api";
import { chatTime } from "@/lib/format";
import type { ChatMessage } from "@/lib/types";

// The composer reads the remembered name from sessionStorage, which exists only in the browser.
const Composer = dynamic(() => import("@/components/Composer"), { ssr: false });

// The shared chat where staff send requests, and the start of a run: Send, then Process conversation.
export default function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Everyone shares one conversation, so it is read now and every three seconds. Messages are only
  // ever added, so a reply older than the list on screen (started before a Send) is ignored.
  useEffect(() => {
    function load() {
      listMessages()
        .then((loaded) => {
          setMessages((shown) => (shown && shown.length > loaded.length ? shown : loaded));
          setError(null);
        })
        .catch((caught) => setError(`Could not read the conversation: ${errorText(caught)}`));
    }
    load();
    const timer = setInterval(load, 3000);
    return () => clearInterval(timer);
  }, []);

  function addSent(message: ChatMessage) {
    setMessages((shown) => {
      const list = shown ?? [];
      return list.some((item) => item.message_id === message.message_id) ? list : [...list, message];
    });
  }

  const last = messages?.at(-1);

  return (
    <>
      <div className="page-head">
        <h1>Chat</h1>
        {messages && (
          <p className="muted">
            {messages.length} messages{last && `, the last at ${chatTime(last.received_at_utc)}`}
          </p>
        )}
      </div>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      <div className="chat-layout">
        <section className="conversation" aria-label="Conversation">
          {messages && <ChatTimeline messages={messages} />}
          {!messages && <p className="timeline-empty muted">{error ? "No messages to show." : "Loading messages..."}</p>}
          <Composer onSent={addSent} />
        </section>
        <ProcessPanel messageCount={messages?.length ?? 0} />
      </div>
    </>
  );
}
