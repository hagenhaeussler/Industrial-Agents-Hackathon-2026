import { Blobatar } from "@blobatar/react";
import { Send } from "lucide-react";
import { useLayoutEffect, useRef, useState } from "react";
import type { CoworkerChat } from "./useCoworkers";

/** A private browser-session conversation with one simulated coworker. */
export function DirectMessages({ chat }: { chat: CoworkerChat }) {
  const { selected, selectedCoworker } = chat;
  const list = useRef<HTMLOListElement>(null);
  const pinned = useRef(true);
  const previousMember = useRef<string | undefined>(undefined);
  const [newMessages, setNewMessages] = useState(false);
  const lastMessageId = chat.messages.at(-1)?.id;
  const pendingInHistory = chat.pending && chat.messages.some((message) => message.id === chat.pending?.requestId && message.role === "user");

  useLayoutEffect(() => {
    if (previousMember.current !== selected?.id) {
      previousMember.current = selected?.id;
      pinned.current = true;
    }
    if (pinned.current && list.current) {
      list.current.scrollTop = list.current.scrollHeight;
      setNewMessages(false);
    } else if (lastMessageId) setNewMessages(true);
  }, [selected?.id, lastMessageId]);

  const unavailable = !chat.loading && !chat.error && !chat.chatAvailable;
  const disabled = chat.loading || !chat.chatAvailable || chat.busy || !!chat.pending || chat.expired;
  const location = selectedCoworker?.position.spaceName;

  return (
    <section aria-label="Direct messages" className="flex min-h-0 flex-1 flex-col">
      <div className="border-b border-line px-4 py-3">
        <h2 className="text-[15px] font-[800]">{selected?.name ?? "AI coworkers"}</h2>
        <p className="mt-1 text-xs text-muted">AI simulation. Chats stay in this building session.</p>
        {selected && <p className="mt-2 text-[13px]">{selected.role}</p>}
        {selectedCoworker && (
          <div className="mt-1 text-xs text-muted">
            <p className="break-words">{location}</p>
            <p className="mt-1 break-words">{selectedCoworker.activity}</p>
            {selectedCoworker.journey && <p className="mt-1 break-words">Destination: {selectedCoworker.journey.destinationName}</p>}
          </div>
        )}
      </div>

      {chat.loading && <p role="status" className="px-4 py-3 text-[13px] text-muted">Loading coworkers…</p>}
      {chat.error && (
        <div role="alert" className="border-b border-line px-4 py-3 text-[13px]">
          <p className="break-words text-danger">{chat.error}</p>
          <button type="button" onClick={chat.reload} disabled={chat.loading || chat.busy} className="mt-2 rounded-[8px] bg-field px-3 py-2 font-[650] disabled:opacity-50">
            {chat.expired ? "Start new session" : "Retry connection"}
          </button>
        </div>
      )}
      {unavailable && <p role="status" className="border-b border-line px-4 py-3 text-[13px]">{chat.unavailableReason ?? "AI chat is not available in this preview."}</p>}

      <ol
        ref={list}
        aria-label={selected ? `Messages with ${selected.name}` : "Messages"}
        aria-busy={chat.loading}
        onScroll={() => {
          const element = list.current;
          if (!element) return;
          pinned.current = element.scrollHeight - element.scrollTop - element.clientHeight < 64;
          if (pinned.current) setNewMessages(false);
        }}
        className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto overscroll-contain p-4"
      >
        {!selected && <li className="text-[13px] text-muted">Choose a coworker in the sidebar to open their chat.</li>}
        {selected && chat.messages.length === 0 && !chat.loading && (
          <li className="text-[13px] text-muted">Ask about the building or their current location.</li>
        )}
        {chat.messages.map((message) => (
          <li key={message.id} className="flex gap-2.5">
            <span className="mt-0.5 grid size-8 shrink-0 place-items-center rounded-[10px] bg-field" aria-hidden="true">
              <Blobatar name={message.role === "user" ? "alain00" : message.memberId} size={26} />
            </span>
            <div className="min-w-0 flex-1">
              <p className="text-[13px] font-[750]">
                {message.role === "user" ? "You" : `${selected?.name ?? "Coworker"} · AI`}
                <time dateTime={new Date(message.createdAt).toISOString()} className="ml-2 text-[11px] font-normal text-muted">
                  {new Date(message.createdAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                </time>
              </p>
              <p className="mt-1 whitespace-pre-wrap text-[13px] leading-relaxed [overflow-wrap:anywhere]">{message.text}</p>
            </div>
          </li>
        ))}
      </ol>
      {newMessages && <button type="button" onClick={() => {
        if (list.current) list.current.scrollTop = list.current.scrollHeight;
        pinned.current = true;
        setNewMessages(false);
      }} className="mx-4 mb-2 rounded-[8px] bg-field py-2 text-xs font-[650]">New messages. Go to latest</button>}

      {chat.pending && (
        <div className="mx-4 mb-2 rounded-[10px] bg-field p-3 text-[13px]">
          {!pendingInHistory && <p className="whitespace-pre-wrap [overflow-wrap:anywhere]">{chat.pending.text}</p>}
          {chat.pending.status === "sending" ? (
            <p role="status" className="mt-2 text-xs text-muted">Waiting for {selected?.name.split(" ")[0]}'s reply…</p>
          ) : (
            <div role="alert" className="mt-2">
              <p className="break-words text-danger">{chat.pending.error}</p>
              <p className="mt-1 text-xs text-muted">The reply was not confirmed. Retry the same message safely.</p>
              <button type="button" onClick={chat.retry} disabled={chat.busy} className="mt-2 rounded-[8px] bg-white px-3 py-2 font-[650] disabled:opacity-50">Retry message</button>
            </div>
          )}
        </div>
      )}
      {selected && <form onSubmit={(event) => { event.preventDefault(); chat.send(); }} className="m-3 flex items-end gap-2 rounded-[14px] border border-[#d8dcd0] p-1.5">
        <textarea
          rows={2}
          maxLength={2000}
          value={chat.draft}
          onChange={(event) => chat.setDraft(event.target.value)}
          disabled={disabled}
          aria-label={`Message ${selected.name}`}
          placeholder={`Message ${selected.name.split(" ")[0]}`}
          className="max-h-32 min-w-0 flex-1 resize-y bg-transparent px-2 py-1.5 text-[13px] outline-none focus-visible:ring-2 focus-visible:ring-ink disabled:opacity-50"
        />
        <button type="submit" aria-label="Send direct message" disabled={disabled || !chat.draft.trim()} className="grid size-8 shrink-0 place-items-center rounded-[10px] bg-ink text-white disabled:opacity-40">
          <Send size={15} />
        </button>
      </form>}
    </section>
  );
}
