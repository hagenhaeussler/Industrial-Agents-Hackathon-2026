import type { Building, BuildingScene, Overlay, PathPoint } from "@locora/view";
import { ConversationProvider } from "@elevenlabs/react";
import { Accessibility, MapPin, Search, Settings } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { useBuilding, useRoute, type RouteRequest } from "../api/buildings";
import type { Fix } from "../camera/localize";
import { navigate } from "../router";
import { directions, type Step } from "../route/directions";
import { guidePath, readGuideLink } from "../route/link";
import { spaceName } from "../route/places";
import { stopsAhead } from "../route/progress";
import { Sheet } from "../ui/Sheet";
import { FloorPlanView } from "../views/FloorPlanView";
import { ChatInput, Transcript } from "../voice/ConversationLog";
import { useBuildingVoice } from "../voice/useBuildingVoice";
import { AgentDock } from "./AgentDock";
import { CameraLayer } from "./CameraLayer";
import { Compass } from "./Compass";
import type { GuideMode } from "./ModeSwitch";
import { PlacePicker } from "./PlacePicker";
import { RouteBanner } from "./RouteBanner";

/** The phone guide at `/b/:buildingId`, opened from a QR code or a shared link. */
export function PhoneGuide({ buildingId, query }: { buildingId: string; query: URLSearchParams }) {
  const building = useBuilding(buildingId);
  if (building.isPending) return <Notice text="Loading the building…" />;
  if (building.isError) return <Notice text={building.error.message} />;
  return (
    <ConversationProvider>
      <Guide buildingId={buildingId} query={query} document={building.data.document} scene={building.data.scene} />
    </ConversationProvider>
  );
}

function storedMode(): GuideMode {
  const stored = localStorage.getItem("guide-mode");
  return stored === "steps" ? "steps" : "map";
}

const toFloorPoint = (point: PathPoint) => ({ floorId: point.floor_id, x: point.x, y: point.y });

/** Camera fixes in a row that must agree on a new room before it becomes the start. One fix can land next door. */
const ROOM_FIXES = 2;

function Guide({
  buildingId,
  query,
  document,
  scene,
}: {
  buildingId: string;
  query: URLSearchParams;
  document: Building;
  scene: BuildingScene;
}) {
  const link = readGuideLink(query);
  const destinationId = link.to.at(-1);
  const request: RouteRequest | undefined =
    link.from && destinationId ? { stops: [link.from, ...link.to], stepFree: link.stepFree } : undefined;
  const route = useRoute(buildingId, request);
  const steps = useMemo(() => (route.data ? directions(route.data, document) : []), [route.data, document]);

  const [mode, setMode] = useState<GuideMode>(storedMode);
  const [stepIndex, setStepIndex] = useState(0);
  const [picker, setPicker] = useState<"from" | "to">();
  const [panel, setPanel] = useState<"chat" | "settings">();
  const [fix, setFix] = useState<Fix>();
  const roomStreak = useRef<{ spaceId: string; count: number }>(undefined);
  const step: Step | undefined = steps[Math.min(stepIndex, steps.length - 1)];

  useEffect(() => {
    setStepIndex(0);
  }, [route.data]);
  useEffect(() => {
    localStorage.setItem("guide-mode", mode);
    // A camera position is only current while the camera runs.
    if (mode !== "camera") {
      setFix(undefined);
      roomStreak.current = undefined;
    }
  }, [mode]);

  const update = (next: Partial<RouteRequest>) => {
    const stops = next.stops ?? [link.from ?? "", ...link.to];
    navigate(guidePath(buildingId, { stops, stepFree: next.stepFree ?? link.stepFree }), true);
  };

  const position = link.from ? { id: link.from, name: spaceName(document, link.from) ?? link.from } : undefined;
  const destination = destinationId ? { id: destinationId, name: spaceName(document, destinationId) ?? destinationId } : undefined;
  const voice = useBuildingVoice({ buildingId, position, destination }, (planned) =>
    update({ stops: planned.stops, stepFree: planned.stepFree }),
  );

  const ground = scene.floors.find((floor) => floor.level === 0) ?? scene.floors[0]!;
  const startFloor = document.spaces.find((space) => space.id === link.from)?.floor_id ?? ground.id;
  const [viewFloor, setViewFloor] = useState(startFloor);
  useEffect(() => {
    setViewFloor(step?.at.floor_id ?? startFloor);
  }, [step, startFloor]);

  // A camera position counts while the camera view is open. Elsewhere the confirmed step marks the position.
  const located = mode === "camera" ? fix : undefined;
  const marker: Overlay["position"] = located
    ? { floorId: located.floorId, x: located.x, y: located.y, headingDeg: located.headingDeg }
    : step && toFloorPoint(step.at);
  const onFix = (next: Fix) => {
    setFix(next);
    const count = roomStreak.current?.spaceId === next.spaceId ? roomStreak.current.count + 1 : 1;
    roomStreak.current = { spaceId: next.spaceId, count };
    if (count !== ROOM_FIXES || next.spaceId === link.from) return;
    // A confirmed new room becomes the start, and the route is planned again with the stops still ahead.
    const ahead = stopsAhead(route.data?.route, next.spaceId, link.to);
    if (link.to.length > 0 && ahead.length === 0) return; // arrived
    update({ stops: [next.spaceId, ...ahead] });
  };

  const overlay: Overlay = useMemo(
    () => ({
      route: route.data?.path.map(toFloorPoint),
      position: marker,
      highlightIds: destinationId ? [destinationId] : [],
    }),
    [route.data, marker?.floorId, marker?.x, marker?.y, marker?.headingDeg, destinationId],
  );

  return (
    <main className="relative h-svh min-h-[600px] w-full overflow-hidden isolate">
      {mode === "map" && (
        <FloorPlanView
          scene={scene}
          floorId={viewFloor}
          overlay={overlay}
          options={{ assets: false }}
          focus={step && step.at.floor_id === viewFloor ? { x: step.at.x, y: step.at.y, width: 36 } : undefined}
          className="absolute inset-0 -z-10 bg-paper"
        />
      )}
      {mode === "camera" && <CameraLayer turn={step?.turn} buildingId={buildingId} onFix={onFix} />}
      {mode === "steps" && (
        <StepList steps={steps} current={stepIndex} onSelect={setStepIndex} empty={!request} />
      )}

      <div className="absolute inset-x-3.5 top-[max(14px,env(safe-area-inset-top))] mx-auto max-w-[620px]">
        {step && destination ? (
          <RouteBanner
            step={step}
            index={stepIndex}
            count={steps.length}
            destination={destination.name}
            lengthM={route.data?.route.length_m ?? null}
            onPrevious={() => setStepIndex((index) => Math.max(0, index - 1))}
            onNext={() => setStepIndex((index) => Math.min(steps.length - 1, index + 1))}
            onOpen={() => setMode("steps")}
          />
        ) : (
          <PlanBar
            position={position?.name}
            destination={destination?.name}
            unreachable={route.data?.route.reachable === false}
            loading={route.isFetching}
            onFrom={() => setPicker("from")}
            onTo={() => setPicker("to")}
          />
        )}
        <div className="mt-2 flex items-start justify-between gap-2">
          <div className={`flex flex-col gap-2 ${mode === "steps" ? "invisible" : ""}`}>
            <button
              type="button"
              onClick={() => setPanel("settings")}
              aria-label="Settings"
              className="float grid size-11 place-items-center rounded-[13px]"
            >
              <Settings size={20} />
            </button>
            <Compass />
          </div>
          {mode === "map" && scene.floors.length > 1 && (
            <FloorDots scene={scene} floorId={viewFloor} onChange={setViewFloor} />
          )}
          {mode === "camera" && marker && (
            <button
              type="button"
              onClick={() => setMode("map")}
              aria-label="Open map"
              className="float h-[132px] w-[148px] overflow-hidden rounded-[14px] p-1.5"
            >
              <FloorPlanView
                scene={scene}
                floorId={marker.floorId}
                overlay={overlay}
                options={{ interactive: false, labels: false, assets: false }}
                focus={{ x: marker.x, y: marker.y, width: 28 }}
                className="size-full rounded-[9px] bg-paper"
              />
            </button>
          )}
        </div>
      </div>

      <AgentDock
        voice={voice}
        mode={mode}
        onMode={setMode}
        arrived={step?.turn === "arrive" && stepIndex === steps.length - 1}
        onOpenChat={() => setPanel("chat")}
      />

      <PlacePicker
        building={document}
        open={picker !== undefined}
        title={picker === "from" ? "Where are you?" : "Where to?"}
        onClose={() => setPicker(undefined)}
        onPick={(place) => {
          setPicker(undefined);
          if (picker === "from") update({ stops: [place.spaceId, ...link.to] });
          else update({ stops: [link.from ?? "", place.spaceId] });
        }}
      />
      <Sheet
        open={panel === "chat"}
        onClose={() => setPanel(undefined)}
        title="Ask Locora"
        className="flex-col [&[open]]:flex [&[open]]:h-[min(660px,84svh)]"
      >
        <Transcript entries={voice.entries} empty="Tap the mic below to start. You can talk or type." />
        <ChatInput enabled={voice.phase === "listening" || voice.phase === "speaking"} onSend={voice.send} />
      </Sheet>
      <Sheet open={panel === "settings"} onClose={() => setPanel(undefined)} title="Settings" subtitle={document.building.name}>
        <GuideSettings
          stepFree={link.stepFree}
          onStepFree={(stepFree) => update({ stepFree })}
          onChangeStart={() => {
            setPanel(undefined);
            setPicker("from");
          }}
        />
      </Sheet>
    </main>
  );
}

/** Start and destination before a route exists. */
function PlanBar(props: {
  position?: string;
  destination?: string;
  unreachable: boolean;
  loading: boolean;
  onFrom: () => void;
  onTo: () => void;
}) {
  return (
    <div className="float grid gap-1 rounded-[20px] p-2">
      <button type="button" onClick={props.onFrom} className="flex items-center gap-3 rounded-[14px] px-2 py-2 text-left">
        <MapPin size={18} className="text-muted" />
        <span className="text-[13px] font-[650]">{props.position ?? "Where are you?"}</span>
      </button>
      <button type="button" onClick={props.onTo} className="flex items-center gap-3 rounded-[14px] bg-field px-2 py-3 text-left">
        <Search size={18} />
        <span className="text-[17px] font-[750] tracking-[-0.5px]">{props.destination ?? "Where to?"}</span>
      </button>
      {(props.unreachable || props.loading) && (
        <p className="px-2 pb-1 text-xs text-muted">
          {props.loading ? "Finding the route…" : "There is no route with the current settings."}
        </p>
      )}
    </div>
  );
}

/** The floor shown on the map, as small numbered circles. */
function FloorDots({ scene, floorId, onChange }: { scene: BuildingScene; floorId: string; onChange: (id: string) => void }) {
  return (
    <div role="radiogroup" aria-label="Floor" className="float flex flex-col-reverse gap-1 rounded-full p-1">
      {scene.floors.map((floor) => (
        <button
          key={floor.id}
          type="button"
          role="radio"
          aria-checked={floor.id === floorId}
          aria-label={floor.name}
          onClick={() => onChange(floor.id)}
          className={`grid size-9 place-items-center rounded-full text-xs font-[750] ${
            floor.id === floorId ? "bg-ink text-white" : "text-ink"
          }`}
        >
          {floor.level}
        </button>
      ))}
    </div>
  );
}

function StepList({
  steps,
  current,
  onSelect,
  empty,
}: {
  steps: Step[];
  current: number;
  onSelect: (index: number) => void;
  empty: boolean;
}) {
  return (
    <div className="absolute inset-0 -z-10 overflow-y-auto bg-paper px-3.5 pt-[132px] pb-[200px]">
      <ol className="float mx-auto grid max-w-[620px] rounded-[20px] px-4 py-2">
        {steps.map((item, index) => (
          <li key={index} className="border-b border-line last:border-0">
            <button
              type="button"
              onClick={() => onSelect(index)}
              aria-current={index === current ? "step" : undefined}
              className="flex w-full items-center gap-3 py-3 text-left"
            >
              <span
                className={`grid size-8 shrink-0 place-items-center rounded-full text-xs font-[750] ${
                  index === current ? "bg-accent" : index < current ? "bg-ink text-white" : "bg-field"
                }`}
              >
                {index + 1}
              </span>
              <span className="grid gap-0.5">
                <strong className="text-[14px] font-[650]">{item.instruction}</strong>
                <span className="text-[11px] text-muted">{item.floorName}</span>
              </span>
            </button>
          </li>
        ))}
        {steps.length === 0 && (
          <li className="py-6 text-center text-sm text-muted">
            {empty ? "Choose where you are and where to go." : "No steps for this route."}
          </li>
        )}
      </ol>
    </div>
  );
}

function GuideSettings({
  stepFree,
  onStepFree,
  onChangeStart,
}: {
  stepFree: boolean;
  onStepFree: (value: boolean) => void;
  onChangeStart: () => void;
}) {
  return (
    <div className="grid gap-3 pb-2">
      <label className="flex items-center gap-3 rounded-[15px] bg-field p-3.5">
        <Accessibility size={20} />
        <span className="flex-1 text-sm font-[650]">Step-free route</span>
        <input
          type="checkbox"
          checked={stepFree}
          onChange={(event) => onStepFree(event.target.checked)}
          className="size-5 accent-ink"
        />
      </label>
      <button type="button" onClick={onChangeStart} className="flex items-center gap-3 rounded-[15px] bg-field p-3.5 text-left">
        <MapPin size={20} />
        <span className="text-sm font-[650]">Change where you are</span>
      </button>
      <section className="mt-2 grid gap-1.5 text-xs leading-relaxed text-muted">
        <h3 className="font-[750] text-ink">About Locora</h3>
        <p>Your position comes from the QR code, the steps you confirm, or the camera view.</p>
        <p>
          In the camera view, the guide sends a still image about once per second to the localization server to find
          your position. Images are not stored.
        </p>
        <p>Routes and answers come from the building data. Locora answers questions about this building only.</p>
      </section>
    </div>
  );
}

function Notice({ text }: { text: string }) {
  return <p className="grid h-svh place-items-center p-6 text-center text-sm text-muted">{text}</p>;
}
