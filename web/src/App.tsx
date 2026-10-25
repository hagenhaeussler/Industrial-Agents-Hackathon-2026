import { lazy, Suspense } from "react";
import { Home } from "./home/Home";
import { PhoneGuide } from "./phone/PhoneGuide";
import { useLocation } from "./router";
import { WorkspaceArrival } from "./arrival/WorkspaceArrival";

// The desktop workspace loads three.js; phones opening a QR link should not download it.
const Workspace = lazy(() => import("./admin/Workspace").then((module) => ({ default: module.Workspace })));

export function App() {
  const { page, query } = useLocation();
  if (page.name === "guide") return <PhoneGuide key={page.buildingId} buildingId={page.buildingId} query={query} />;
  if (page.name === "admin") {
    return (
      <>
        <Suspense fallback={null}>
          <Workspace key={page.buildingId} buildingId={page.buildingId} query={query} />
        </Suspense>
        <WorkspaceArrival key={page.buildingId} buildingId={page.buildingId} />
      </>
    );
  }
  if (page.name === "home") return <Home />;
  return <p className="grid h-svh place-items-center text-sm text-muted">This page does not exist.</p>;
}
