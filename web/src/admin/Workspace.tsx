import { compileScene, type Building, type Overlay, type PickResult } from "@building/view";
import { ConversationProvider } from "@elevenlabs/react";
import { useCallback, useMemo, useRef, useState } from "react";
import { useBuilding, useRoute, type RouteRequest } from "../api/buildings";
import { directions } from "../route/directions";
import { spaceName } from "../route/places";
import { BuildingView3DView, type View3DHandle } from "../views/BuildingView3DView";
import { FloorPlanView } from "../views/FloorPlanView";
import { useBuildingVoice } from "../voice/useBuildingVoice";
import { CanvasTools, SelectionCard, type Tool } from "./CanvasTools";
import { applyMoves, type Move } from "./moves";
import { SettingsDialog } from "./SettingsDialog";
import { ShareDialog } from "./ShareDialog";
import { Sidebar, type View } from "./Sidebar";
import { SidePanel, type PanelTab } from "./SidePanel";
import { SEED_POSTS, type Channel, type Post } from "./team";
import { TopBar } from "./TopBar";

/** Something selected in the building: a space or a piece of equipment. */
export interface Selection {
  kind: "space" | "asset";
  id: string;
  floorId: string;
}

/** Where the user is: a space, and the clicked point inside it when known. */
export interface Position {
  spaceId: string;
  floorId: string;
  x?: number;
  y?: number;
}

/** The desktop workspace at `/admin/:buildingId`. */
export function Workspace({ buildingId }: { buildingId: string; query: URLSearchParams }) {
  const building = useBuilding(buildingId);
  if (building.isPending) return <p className="grid h-svh place-items-center text-sm text-muted">Loading the building…</p>;
  if (building.isError) return <p className="grid h-svh place-items-center text-sm text-danger">{building.error.message}</p>;
  return (
    <ConversationProvider>
      <WorkspaceView buildingId={buildingId} document={building.data.document} />
    </ConversationProvider>
  );
}

function WorkspaceView({ buildingId, document: stored }: { buildingId: string; document: Building }) {
  const [moves, setMoves] = useState<Move[]>([]);
  const document = useMemo(() => applyMoves(stored, moves), [stored, moves]);
  const scene = useMemo(() => compileScene(document), [document]);

  const [view, setView] = useState<View>("model");
  const [tab, setTab] = useState<PanelTab>("assistant");
  const [channel, setChannel] = useState<Channel>("facility-ops");
  const [posts, setPosts] = useState<Post[]>(SEED_POSTS);
  const [tool, setTool] = useState<Tool>("select");
  const [focusFloor, setFocusFloor] = useState<string | null>(null);
  const [selection, setSelection] = useState<Selection>();
  const [position, setPosition] = useState<Position>();
  const [destination, setDestination] = useState<string>();
  const [stepFree, setStepFree] = useState(false);
  const [labels, setLabels] = useState(true);
  const [assets, setAssets] = useState(true);
  const [dialog, setDialog] = useState<"share" | "settings">();
  const camera = useRef<View3DHandle>(null);

  const request: RouteRequest | undefined =
    position && destination ? { stops: [position.spaceId, destination], stepFree } : undefined;
  const route = useRoute(buildingId, request);
  const steps = useMemo(() => (route.data ? directions(route.data, document) : []), [route.data, document]);

  const log = (text: string) =>
    setPosts((current) => [
      ...current,
      { id: crypto.randomUUID(), channel: "facility-ops", author: "you", text, time: clock() },
    ]);

  const placeOf = (spaceId: string) => ({ id: spaceId, name: spaceName(document, spaceId) ?? spaceId });
  const voice = useBuildingVoice(
    { buildingId, position: position && placeOf(position.spaceId), destination: destination ? placeOf(destination) : undefined },
    (planned) => {
      const [from, ...rest] = planned.stops;
      const floorId = document.spaces.find((space) => space.id === from)?.floor_id;
      if (from && floorId) setPosition({ spaceId: from, floorId });
      setDestination(rest.at(-1));
      setStepFree(planned.stepFree ?? false);
    },
  );

  const spaceAt = (pick: PickResult) =>
    pick.kind === "space" ? pick.id : document.assets.find((asset) => asset.id === pick.id)?.space_id;

  const onPick = useCallback(
    (pick: PickResult | null) => {
      if (!pick) return setSelection(undefined);
      if (tool === "position") {
        const spaceId = spaceAt(pick);
        if (spaceId) setPosition({ spaceId, floorId: pick.floorId, x: pick.x, y: pick.y });
        setTool("select");
        return;
      }
      if (tool === "move" && selection?.kind === "asset") {
        const spaceId = spaceAt(pick);
        if (spaceId) {
          setMoves((current) => [...current, { assetId: selection.id, floorId: pick.floorId, spaceId, x: pick.x, y: pick.y }]);
          const name = document.assets.find((asset) => asset.id === selection.id)?.name ?? "Equipment";
          log(`Moved ${name} to ${spaceName(document, spaceId) ?? spaceId}.`);
        }
        setTool("select");
        return;
      }
      if (pick.kind === "space" || pick.kind === "asset") setSelection({ kind: pick.kind, id: pick.id, floorId: pick.floorId });
    },
    [tool, selection, document],
  );

  const positionPoint = (): Overlay["position"] => {
    if (!position) return undefined;
    if (position.x !== undefined && position.y !== undefined) return { floorId: position.floorId, x: position.x, y: position.y };
    const shape = scene.floors.flatMap((floor) => floor.spaces).find((space) => space.id === position.spaceId);
    return shape ? { floorId: position.floorId, x: shape.labelPoint[0], y: shape.labelPoint[1] } : undefined;
  };

  const overlay: Overlay = useMemo(
    () => ({
      route: route.data?.path.map((point) => ({ floorId: point.floor_id, x: point.x, y: point.y })),
      position: positionPoint(),
      highlightIds: [selection?.id, destination].filter((id): id is string => id !== undefined),
    }),
    [route.data, position, selection, destination, scene],
  );

  const selectionPoint = (found: Selection) =>
    found.kind === "asset"
      ? document.assets.find((asset) => asset.id === found.id)?.position
      : scene.floors.flatMap((floor) => floor.spaces).find((space) => space.id === found.id)?.labelPoint;

  const ground = scene.floors.find((floor) => floor.level === 0) ?? scene.floors[0]!;
  const planFloor = focusFloor ?? selection?.floorId ?? position?.floorId ?? ground.id;

  return (
    <div className="grid h-svh grid-cols-[64px_240px_minmax(0,1fr)_372px] bg-rail text-ink">
      <Sidebar
        building={document}
        view={view}
        onView={(next) => {
          setView(next);
          if (next === "routes") setTab("route");
        }}
        channel={tab === "activity" ? channel : undefined}
        onChannel={(next) => {
          setChannel(next);
          setTab("activity");
        }}
        positionName={position ? spaceName(document, position.spaceId) : undefined}
        onSettings={() => setDialog("settings")}
      />
      <main className="m-2 ml-0 flex min-w-0 flex-col overflow-hidden rounded-[14px] bg-paper">
        <TopBar
          document={document}
          view={view}
          floors={scene.floors}
          focusFloor={focusFloor}
          onFocusFloor={setFocusFloor}
          onFind={(found) => {
            setSelection(found);
            setFocusFloor(found.floorId);
            const point = selectionPoint(found);
            if (point) camera.current?.centerOn(found.floorId, point[0], point[1]);
          }}
          onShare={() => setDialog("share")}
        />
        <div className="relative min-h-0 flex-1">
          {view === "plans" ? (
            <FloorPlanView
              scene={scene}
              floorId={planFloor}
              overlay={overlay}
              onPick={onPick}
              options={{ labels, assets }}
              className="absolute inset-0"
            />
          ) : (
            <BuildingView3DView
              ref={camera}
              scene={scene}
              focusFloorId={focusFloor}
              overlay={overlay}
              onPick={onPick}
              options={{ labels, assets }}
              className="absolute inset-0"
            />
          )}
          <CanvasTools
            onResetView={view === "plans" ? undefined : () => camera.current?.reset()}
            tool={tool}
            onTool={setTool}
            canMove={selection?.kind === "asset"}
            labels={labels}
            onLabels={setLabels}
            assets={assets}
            onAssets={setAssets}
          />
          {selection && (
            <SelectionCard
              document={document}
              selection={selection}
              isPosition={position?.spaceId === selection.id}
              onClose={() => setSelection(undefined)}
              onHere={(spaceId) => setPosition({ spaceId, floorId: selection.floorId })}
              onRoute={(spaceId) => {
                setDestination(spaceId);
                setTab("route");
              }}
              onMove={() => setTool("move")}
            />
          )}
        </div>
      </main>
      <SidePanel
        tab={tab}
        onTab={setTab}
        voice={voice}
        document={document}
        position={position}
        destination={destination}
        stepFree={stepFree}
        onStepFree={setStepFree}
        onPickPosition={() => setTool("position")}
        onClearRoute={() => setDestination(undefined)}
        route={route.data}
        routeLoading={route.isFetching}
        steps={steps}
        onShare={() => setDialog("share")}
        channel={channel}
        posts={posts}
        onPost={(text) =>
          setPosts((current) => [...current, { id: crypto.randomUUID(), channel, author: "you", text, time: clock() }])
        }
      />
      <ShareDialog
        open={dialog === "share"}
        onClose={() => setDialog(undefined)}
        buildingId={buildingId}
        request={request}
        positionName={position ? spaceName(document, position.spaceId) : undefined}
        destinationName={destination ? spaceName(document, destination) : undefined}
        onShared={() => log("Sent a route to a phone.")}
      />
      <SettingsDialog
        open={dialog === "settings"}
        onClose={() => setDialog(undefined)}
        movedCount={new Set(moves.map((move) => move.assetId)).size}
        onResetMoves={() => setMoves([])}
      />
    </div>
  );
}

function clock() {
  return new Date().toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });
}
