import { type FormEvent, type KeyboardEvent, useRef, useState } from "react";
import { errorText, sendMessage, transcribe } from "@/lib/api";
import type { ChatMessage } from "@/lib/types";

const NAME_KEY = "chat-name";
// One request per recording: recording stops by itself after a minute.
const MAX_RECORDING_MS = 60_000;
// Chinese characters in a transcript mean the worker spoke Mandarin.
const CHINESE = /[一-鿿]/;

type Props = { onSent: (message: ChatMessage) => void };

// Writes one message. Send only saves it for everyone: it makes no model call. When saving fails,
// the draft stays so it can be sent again. While it sends, the text box is read-only: the saved
// answer clears the box, which would also erase anything typed in the meantime.
// Record turns speech into text in the message box, to be checked and edited; it never sends by itself.
// The page renders it in the browser only (next/dynamic, ssr: false), because it reads sessionStorage.
export default function Composer({ onSent }: Props) {
  // The name is remembered for this browser tab only, as in the mock chat. It is not an account.
  const [sender, setSender] = useState(() => sessionStorage.getItem(NAME_KEY) ?? "");
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [recorder, setRecorder] = useState<MediaRecorder | null>(null);
  const [transcribing, setTranscribing] = useState(false);
  const [voiceNote, setVoiceNote] = useState<string | null>(null);
  const [voiceError, setVoiceError] = useState<string | null>(null);
  // One ID per send attempt of this draft. Retrying an unchanged draft reuses it, so the backend
  // saves the message once even if an earlier attempt reached it; editing the draft starts a new one.
  const submissionId = useRef<string | null>(null);
  const stopTimer = useRef<number | undefined>(undefined);
  const listening = recorder !== null || transcribing;
  const canSend = !sending && !listening && sender.trim() !== "" && text.trim() !== "";

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
      setVoiceNote(null);
      onSent(saved);
    } catch (caught) {
      setError(errorText(caught));
    } finally {
      setSending(false);
    }
  }

  // Enter starts a new line, as in the original messages; Ctrl+Enter or Cmd+Enter sends. requestSubmit
  // ignores a disabled Send button, so the shortcut checks the same rule itself.
  function sendOnShortcut(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && (event.ctrlKey || event.metaKey) && canSend) {
      event.currentTarget.form?.requestSubmit();
    }
  }

  async function startRecording() {
    setVoiceError(null);
    setVoiceNote(null);
    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (caught) {
      setVoiceError(`The microphone is unavailable: ${errorText(caught)} Type the message instead.`);
      return;
    }
    // Chrome and Firefox record WebM, Safari MP4; the transcription model accepts both.
    const mimeType = MediaRecorder.isTypeSupported("audio/webm") ? "audio/webm" : "audio/mp4";
    const started = new MediaRecorder(stream, { mimeType });
    const chunks: Blob[] = [];
    started.ondataavailable = (event) => chunks.push(event.data);
    started.onstop = () => {
      window.clearTimeout(stopTimer.current);
      // Releasing the tracks turns the microphone off.
      stream.getTracks().forEach((track) => track.stop());
      setRecorder(null);
      addTranscript(new Blob(chunks, { type: mimeType }), mimeType === "audio/webm" ? "speech.webm" : "speech.mp4");
    };
    started.start();
    setRecorder(started);
    stopTimer.current = window.setTimeout(() => started.stop(), MAX_RECORDING_MS);
  }

  // The transcript joins whatever is already typed. The worker checks it before Send: a misheard order
  // ID, quantity or date is never corrected automatically.
  async function addTranscript(audio: Blob, fileName: string) {
    setTranscribing(true);
    try {
      const heard = (await transcribe(audio, fileName)).text.trim();
      if (!heard) {
        setVoiceError("No speech was recognised. Record again or type the message.");
        return;
      }
      setText((current) => (current.trim() ? `${current.trimEnd()} ${heard}` : heard));
      submissionId.current = null;
      setVoiceNote(
        CHINESE.test(heard)
          ? "Check the transcript before Send. Mandarin is experimental: when translation is switched on, Send saves an English machine translation for processing."
          : "Check the transcript before Send, especially order IDs, quantities and dates.",
      );
    } catch (caught) {
      setVoiceError(`Not transcribed: ${errorText(caught)}`);
    } finally {
      setTranscribing(false);
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
          placeholder="For example: Please place ORD-045, 150 vests, due Apr 09."
        />
      </label>
      {recorder && <p role="status">Recording. Speak one request, then stop; it stops by itself after a minute.</p>}
      {transcribing && <p role="status">Transcribing...</p>}
      {voiceNote && <p className="hint">{voiceNote}</p>}
      {voiceError && <p className="error">{voiceError}</p>}
      <div className="composer-row">
        <button className="primary" disabled={!canSend}>
          {sending ? "Sending..." : "Send"}
        </button>
        {/* type="button": inside the form, a plain button would submit it. */}
        <button type="button" disabled={sending || transcribing} onClick={recorder ? () => recorder.stop() : startRecording}>
          {recorder ? "Stop recording" : "Record"}
        </button>
        <span className="hint">Saves the message for everyone. Nothing is processed until you start the dispatch workflow.</span>
      </div>
      {error && (
        <p className="error" role="alert">
          Not sent: {error} Your message is still here.
        </p>
      )}
    </form>
  );
}
