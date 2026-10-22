import { type FormEvent, type KeyboardEvent, useRef, useState } from "react";
import { errorText, sendMessage } from "@/lib/api";
import type { ChatMessage } from "@/lib/types";

const NAME_KEY = "chat-name";

type Props = { onSent: (message: ChatMessage) => void };

// Writes one message. Send only saves it for everyone: it makes no model call. When saving fails,
// the draft stays so it can be sent again. While it sends, the text box is read-only: the saved
// answer clears the box, which would also erase anything typed in the meantime.
// The page renders it in the browser only (next/dynamic, ssr: false), because it reads sessionStorage.
export default function Composer({ onSent }: Props) {
  // The name is remembered for this browser tab only, as in the mock chat. It is not an account.
  const [sender, setSender] = useState(() => sessionStorage.getItem(NAME_KEY) ?? "");
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // One ID per send attempt of this draft. Retrying an unchanged draft reuses it, so the backend
  // saves the message once even if an earlier attempt reached it; editing the draft starts a new one.
  const submissionId = useRef<string | null>(null);

  function changeSender(value: string) {
    setSender(value);
    sessionStorage.setItem(NAME_KEY, value);
  }

  function changeText(value: string) {
    setText(value);
    submissionId.current = null;
  }

  async function send(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    submissionId.current ??= crypto.randomUUID();
    setSending(true);
    setError(null);
    try {
      const saved = await sendMessage({ submission_id: submissionId.current, sender, raw_text: text });
      submissionId.current = null;
      setText("");
      onSent(saved);
    } catch (caught) {
      setError(errorText(caught));
    } finally {
      setSending(false);
    }
  }

  // Enter starts a new line, as in the original messages; Ctrl+Enter or Cmd+Enter sends.
  function sendOnShortcut(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
      event.currentTarget.form?.requestSubmit();
    }
  }

  return (
    <form className="composer" onSubmit={send}>
      <div className="composer-row">
        <label>
          Your name
          <input value={sender} onChange={(event) => changeSender(event.target.value)} autoComplete="name" />
        </label>
        <span className="hint">One line, no colon.</span>
      </div>
      <label className="message-field">
        Message
        <textarea
          rows={3}
          value={text}
          readOnly={sending}
          onChange={(event) => changeText(event.target.value)}
          onKeyDown={sendOnShortcut}
          placeholder="For example: Can someone place ORD-107? 2000 cardigans, due Mar 16."
        />
      </label>
      <div className="composer-row">
        <button className="primary" disabled={sending || !sender.trim() || !text.trim()}>
          {sending ? "Sending..." : "Send"}
        </button>
        <span className="hint">Saves the message for everyone. It is not processed until you process the conversation.</span>
      </div>
      {error && (
        <p className="error" role="alert">
          Not sent: {error} Your message is still here.
        </p>
      )}
    </form>
  );
}
