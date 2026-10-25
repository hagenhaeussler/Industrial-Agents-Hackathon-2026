import { Check, Send } from "lucide-react";
import { useEffect, useRef, useState, type FormEvent } from "react";
import type { TranscriptEntry } from "./transcript";

/** The conversation so far. Tool calls show as short activity lines. */
export function Transcript({ entries, empty }: { entries: TranscriptEntry[]; empty: string }) {
  const list = useRef<HTMLOListElement>(null);
  useEffect(() => {
    list.current?.scrollTo({ top: list.current.scrollHeight });
  }, [entries]);
  if (entries.length === 0) return <p className="py-6 text-center text-sm text-muted">{empty}</p>;
  return (
    <ol ref={list} role="log" aria-live="polite" className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto pb-3">
      {entries.map((entry) =>
        entry.kind === "tool" ? (
          <li key={entry.key} className="flex items-center gap-2 px-1 text-[11px] font-[650] text-muted">
            <Check size={13} className={entry.state === "success" ? "text-accent-deep" : ""} />
            {entry.name}
            {entry.state === "failure" && " (failed)"}
          </li>
        ) : (
          <li key={entry.key} className={`max-w-[88%] ${entry.role === "user" ? "self-end" : "self-start"}`}>
            <p
              className={`rounded-[16px] px-4 py-3 text-[13px] leading-relaxed ${
                entry.role === "user" ? "rounded-br-[4px] bg-ink text-white" : "rounded-bl-[4px] bg-field"
              }`}
            >
              {entry.text}
            </p>
          </li>
        ),
      )}
    </ol>
  );
}

export function ChatInput({ enabled, onSend, onTyping }: {
  enabled: boolean;
  onSend: (text: string) => void;
  onTyping: () => void;
}) {
  const [text, setText] = useState("");
  const submit = (event: FormEvent) => {
    event.preventDefault();
    onSend(text);
    setText("");
  };
  return (
    <form onSubmit={submit} className="flex items-center gap-2 rounded-[17px] border border-[#d8dcd0] p-1.5">
      <label className="sr-only" htmlFor="chat-message">
        Message
      </label>
      <input
        id="chat-message"
        value={text}
        onFocus={onTyping}
        onChange={(event) => {
          onTyping();
          setText(event.target.value);
        }}
        disabled={!enabled}
        maxLength={1000}
        autoComplete="off"
        placeholder={enabled ? "Type a question" : "Start the conversation to type"}
        className="min-w-0 flex-1 bg-transparent px-2 py-2 text-base outline-none"
      />
      <button
        type="submit"
        disabled={!enabled || !text.trim()}
        aria-label="Send"
        className="grid size-10 place-items-center rounded-[12px] bg-ink text-white"
      >
        <Send size={18} />
      </button>
    </form>
  );
}
