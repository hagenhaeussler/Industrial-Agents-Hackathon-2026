import { lazy, Suspense } from "react";
import { Home } from "./home/Home";
import { PhoneGuide } from "./phone/PhoneGuide";
import { useLocation } from "./router";

// The desktop workspace loads three.js; phones opening a QR link should not download it.
const Workspace = lazy(() => import("./admin/Workspace").then((module) => ({ default: module.Workspace })));
const CampusExplorer = lazy(() => import("./explore/CampusExplorer").then((module) => ({ default: module.CampusExplorer })));

export function App() {
  const { page, query } = useLocation();
  if (page.name === "guide") return <PhoneGuide key={page.buildingId} buildingId={page.buildingId} query={query} />;
  if (page.name === "admin") {
    return (
      <Suspense fallback={null}>
        <Workspace key={page.buildingId} buildingId={page.buildingId} query={query} />
      </Suspense>
    );
  }
  if (page.name === "library") return <Home />;
  if (page.name === "home") return <Suspense fallback={null}><CampusExplorer /></Suspense>;
  return <p className="grid h-svh place-items-center text-sm text-muted">This page does not exist.</p>;
}
