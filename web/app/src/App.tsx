import { lazy, Suspense } from 'react';
import { Desk } from './desk/Desk';
import { Home } from './home/Home';
import { GoTour } from './phone/GoTour';
import { linkHandler, match, useLocation } from './router';

const Guide = lazy(() => import('./phone/Guide').then(module => ({ default: module.Guide })));

function Placeholder({ title, text }: { title: string; text: string }) {
  return <main className="desk-message"><div className="surface notice"><h1>{title}</h1><p>{text}</p><a className="primary-button" href="/" onClick={linkHandler('/')}>Choose a building</a></div></main>;
}

export default function App() {
  const { path, query } = useLocation();
  const route = match(path);
  if (route.name === 'home') return <Home/>;
  if (route.name === 'desk') return <Desk/>;
  if (route.name === 'go') return route.tourId === 'demo' || query.get('prototype') === '1' ? <Suspense fallback={null}><Guide/></Suspense> : <GoTour tourId={route.tourId}/>;
  if (route.name === 'admin') return <Placeholder title="Admin view" text="Closing and reopening parts of the building arrives with the admin milestone."/>;
  if (route.name === 'marker') return <Placeholder title="Position code" text={`Marker ${route.markerId} is recognised. Opening it inside an active tour arrives with the phone journey.`}/>;
  return <Placeholder title="This page does not exist" text="Check the link, or start from the building list."/>;
}
