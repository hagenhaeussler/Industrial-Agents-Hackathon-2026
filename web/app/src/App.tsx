import { LoaderCircle } from 'lucide-react';
import { lazy, Suspense } from 'react';
import { linkHandler, match, useLocation } from './router';

// one chunk per screen: the phone downloads only the journey
const Home = lazy(() => import('./home/Home').then(module => ({ default: module.Home })));
const Desk = lazy(() => import('./desk/Desk').then(module => ({ default: module.Desk })));
const Journey = lazy(() => import('./phone/Journey').then(module => ({ default: module.Journey })));
const MarkerPage = lazy(() => import('./phone/MarkerPage').then(module => ({ default: module.MarkerPage })));
const Admin = lazy(() => import('./admin/Admin').then(module => ({ default: module.Admin })));
const Guide = lazy(() => import('./phone/Guide').then(module => ({ default: module.Guide })));
const Colab = lazy(() => import('./colab/Colab').then(module => ({ default: module.Colab })));

function Placeholder({ title, text }: { title: string; text: string }) {
  return <main className="desk-message"><div className="surface notice"><h1>{title}</h1><p>{text}</p><a className="primary-button" href="/" onClick={linkHandler('/')}>Choose a building</a></div></main>;
}

function Screen() {
  const { path, query } = useLocation();
  const route = match(path);
  if (route.name === 'home') return <Home/>;
  if (route.name === 'desk') return <Desk/>;
  if (route.name === 'go') return route.tourId === 'demo' || query.get('prototype') === '1' ? <Guide/> : <Journey key={route.tourId} tourId={route.tourId}/>;
  if (route.name === 'admin') return <Admin/>;
  if (route.name === 'colab') return <Colab/>;
  if (route.name === 'marker') return <MarkerPage markerId={route.markerId}/>;
  return <Placeholder title="This page does not exist" text="Check the link, or start from the building list."/>;
}

export default function App() {
  return <Suspense fallback={<main className="desk-message"><p className="loading"><LoaderCircle className="spin" size={20}/>Loading…</p></main>}><Screen/></Suspense>;
}
