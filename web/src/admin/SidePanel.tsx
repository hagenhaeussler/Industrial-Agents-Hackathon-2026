import type { Building, RouteView } from "@locora/view";
import { Blobatar } from "@blobatar/react";
import { Accessibility, Hash, LocateFixed, QrCode, Send, X } from "lucide-react";
import { useState, type FormEvent } from "react";
import { Avatar } from "../avatar/Avatar";
import type { Step } from "../route/directions";
import { spaceName } from "../route/places";
import { TurnIcon } from "../phone/TurnIcon";
import { ChatInput, Transcript } from "../voice/ConversationLog";
import { MicButton } from "../voice/MicButton";
import type { BuildingVoice } from "../voice/useBuildingVoice";
import { memberName, type Channel, type Post } from "./team";
import type { Position } from "./Workspace";

export type PanelTab = "assistant" | "route" | "activity";

const PHASE_TEXT = {
  off: "Ask about rooms, equipment or routes.",
  connecting: "Connecting…",
  listening: "Listening",
  speaking: "Speaking",
  error: "Voice is not available.",
};

/** The right panel: the voice assistant, the current route and team activity. */
export function SidePanel(props: {
  tab: PanelTab;
  onTab: (tab: PanelTab) => void;
  voice: BuildingVoice;
  document: Building;
  position: Position | undefined;
  destination: string | undefined;
  stepFree: boolean;
  onStepFree: (value: boolean) => void;
  onPickPosition: () => void;
  onClearRoute: () => void;
  route: RouteView | undefined;
  routeLoading: boolean;
  steps: Step[];
  onShare: () => void;
  channel: Channel;
  posts: Post[];
  onPost: (text: string) => void;
}) {
  const tabs: { tab: PanelTab; label: string }[] = [
    { tab: "assistant", label: "Locora" },
    { tab: "route", label: "Route" },
    { tab: "activity", label: "Activity" },
  ];
  return (
    <aside className="my-2 mr-2 flex min-h-0 flex-col overflow-hidden rounded-[14px] bg-white">
      <div role="tablist" aria-label="Panel" className="flex gap-1 border-b border-line p-2">
        {tabs.map(({ tab, label }) => (
          <button
            key={tab}
            type="button"
            role="tab"
            aria-selected={props.tab === tab}
            onClick={() => props.onTab(tab)}
            className={`flex-1 rounded-[10px] py-2 text-[13px] font-[700] ${props.tab === tab ? "bg-field text-ink" : "text-muted"}`}
          >
            {label}
          </button>
        ))}
      </div>
      {props.tab === "assistant" && <AssistantTab voice={props.voice} />}
      {props.tab === "route" && <RouteTab {...props} />}
      {props.tab === "activity" && <ActivityTab channel={props.channel} posts={props.posts} onPost={props.onPost} />}
    </aside>
  );
}

function AssistantTab({ voice }: { voice: BuildingVoice }) {
  const live = voice.phase === "listening" || voice.phase === "speaking";
  return (
    <div className="flex min-h-0 flex-1 flex-col p-4">
      <div className="flex items-center gap-3">
        <Avatar phase={voice.phase} level={voice.level} size={72} />
        <div className="min-w-0 flex-1">
          <h2 className="text-[16px] font-[800] tracking-[-0.3px]">Locora</h2>
          <p className="text-xs text-muted">{voice.error ?? PHASE_TEXT[voice.phase]}</p>
        </div>
        <MicButton phase={voice.phase} onStart={() => void voice.start()} onStop={voice.stop} />
      </div>
      <div className="mt-4 flex min-h-0 flex-1 flex-col">
        <Transcript entries={voice.entries} empty="Start the conversation with the mic. Routes Locora plans appear in the view." />
      </div>
      <ChatInput enabled={live} onSend={voice.send} />
    </div>
  );
}

function RouteTab(props: Parameters<typeof SidePanel>[0]) {
  const { document, position, destination, route, steps } = props;
  const reachable = route?.route.reachable;
  return (
    <div className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto p-4">
      <div className="grid gap-1.5 rounded-[16px] bg-field p-2">
        <button type="button" onClick={props.onPickPosition} className="flex items-center gap-2.5 rounded-[11px] bg-white px-3 py-2.5 text-left">
          <LocateFixed size={16} className="text-muted" />
          <span className="min-w-0 flex-1">
            <span className="block text-[11px] text-muted">From</span>
            <span className="block truncate text-[13px] font-[650]">
              {position ? spaceName(document, position.spaceId) : "Click to set your position"}
            </span>
          </span>
        </button>
        <div className="flex items-center gap-2.5 rounded-[11px] bg-white px-3 py-2.5">
          <TurnIcon turn="arrive" size={16} />
          <span className="min-w-0 flex-1">
            <span className="block text-[11px] text-muted">To</span>
            <span className="block truncate text-[13px] font-[650]">
              {destination ? spaceName(document, destination) : "Select a room and choose Route here"}
            </span>
          </span>
          {destination && (
            <button type="button" onClick={props.onClearRoute} aria-label="Clear destination" className="grid size-7 place-items-center rounded-[8px] bg-field">
              <X size={14} />
            </button>
          )}
        </div>
      </div>
      <label className="flex items-center gap-2.5 rounded-[12px] border border-line px-3 py-2.5 text-[13px] font-[650]">
        <Accessibility size={17} />
        <span className="flex-1">Step-free route</span>
        <input type="checkbox" checked={props.stepFree} onChange={(event) => props.onStepFree(event.target.checked)} className="size-4 accent-ink" />
      </label>

      {props.routeLoading && <p className="text-xs text-muted">Finding the route…</p>}
      {reachable === false && <p className="rounded-[12px] bg-[#fbeeee] p-3 text-[13px]">There is no route with these settings.</p>}
      {reachable && route && (
        <>
          <div className="flex items-end justify-between">
            <p className="text-[28px] leading-none font-[800] tracking-[-1px]">
              {Math.round(route.route.length_m ?? 0)} <span className="text-sm font-[650]">m</span>
            </p>
            <p className="text-xs text-muted">{steps.length} steps</p>
          </div>
          <ol className="grid">
            {steps.map((step, index) => (
              <li key={index} className="flex items-center gap-2.5 border-b border-line py-2 last:border-0">
                <span className="grid size-7 shrink-0 place-items-center rounded-full bg-field">
                  <TurnIcon turn={step.turn} size={14} />
                </span>
                <span className="min-w-0">
                  <span className="block text-[13px] font-[650]">{step.instruction}</span>
                  <span className="block text-[11px] text-muted">{step.floorName}</span>
                </span>
              </li>
            ))}
          </ol>
          <button
            type="button"
            onClick={props.onShare}
            className="flex items-center justify-center gap-2 rounded-[12px] bg-ink px-4 py-3 text-[13px] font-[650] text-white"
          >
            <QrCode size={16} /> Send to phone
          </button>
        </>
      )}
    </div>
  );
}

function ActivityTab({ channel, posts, onPost }: { channel: Channel; posts: Post[]; onPost: (text: string) => void }) {
  const [text, setText] = useState("");
  const shown = posts.filter((post) => post.channel === channel);
  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (!text.trim()) return;
    onPost(text.trim());
    setText("");
  };
  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <h2 className="flex items-center gap-1.5 px-4 pt-3 text-[15px] font-[800]">
        <Hash size={16} />
        {channel}
      </h2>
      <ol className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto p-4">
        {shown.map((post) => (
          <li key={post.id} className="flex gap-2.5">
            <span className="mt-0.5 grid size-8 shrink-0 place-items-center rounded-[10px] bg-field">
              <Blobatar name={post.author === "you" ? "alain00" : post.author} size={26} />
            </span>
            <div className="min-w-0">
              <p className="text-[13px]">
                <strong className="font-[750]">{memberName(post.author)}</strong>{" "}
                <span className="text-[11px] text-muted">{post.time}</span>
              </p>
              <p className="text-[13px] leading-snug">{post.text}</p>
            </div>
          </li>
        ))}
      </ol>
      <form onSubmit={submit} className="m-3 flex items-center gap-2 rounded-[14px] border border-[#d8dcd0] p-1.5">
        <input
          value={text}
          onChange={(event) => setText(event.target.value)}
          placeholder={`Message #${channel}`}
          aria-label={`Message #${channel}`}
          className="min-w-0 flex-1 bg-transparent px-2 py-1.5 text-[13px] outline-none"
        />
        <button type="submit" aria-label="Post" className="grid size-8 place-items-center rounded-[10px] bg-ink text-white">
          <Send size={15} />
        </button>
      </form>
    </div>
  );
}
